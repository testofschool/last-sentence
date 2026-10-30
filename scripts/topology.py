"""Official-map route paths for lines 5/7; line 2 keeps its existing ring."""
import json
from pathlib import Path
import re

PATH = Path(__file__).resolve().parents[1] / "web" / "replay" / "topology.json"
DATA = json.loads(PATH.read_text())


def canonical_station(line, name, required=False):
    if line not in DATA["lines"]:
        return name
    stations = DATA["lines"][line]["stations"]
    if isinstance(name, str):
        if name in stations:
            return name
        base = re.sub(r"\(.*?\)", "", name).strip()
        for canonical, info in stations.items():
            if name in info["aliases"] or base in info["aliases"]:
                return canonical
    if required:
        raise ValueError("unknown station in the verified topology")
    return name


def directed_sign(line, a, b):
    a, b = canonical_station(line, a), canonical_station(line, b)
    if not isinstance(a, str) or not isinstance(b, str) or line not in DATA["lines"]:
        return None
    for path in DATA["lines"][line]["paths"]:
        for first, second in zip(path, path[1:]):
            if (a, b) == (first, second):
                return 1
            if (a, b) == (second, first):
                return -1
    return None


def resolve_route(line, origin, destination, direction=None, terminus=None, ring_route=None):
    if direction is not None and str(direction) not in ("0", "1"):
        raise ValueError("direction must be 0 or 1")
    if line == "2호선":
        route = ring_route or []
        if origin not in route or destination not in route:
            raise ValueError("unknown line-2 ring station")
        if terminus is not None and terminus not in route:
            raise ValueError("unknown line-2 ring terminus")
        if origin == destination:
            return [origin]
        if direction is None:
            raise ValueError("ambiguous line-2 ring route: specify --direction 0/1 or --stations")
        step = 1 if str(direction) == "0" else -1
        result = [origin]
        index = route.index(origin)
        for _ in range(len(route) - 1):
            index = (index + step) % len(route)
            result.append(route[index])
            if route[index] == destination:
                break
        if terminus is not None and terminus in result[:-1]:
            raise ValueError("destination lies beyond the supplied terminus")
        return result
    if line not in DATA["lines"]:
        raise ValueError("line has no verified route topology")
    origin, destination = canonical_station(line, origin, True), canonical_station(line, destination, True)
    terminus = canonical_station(line, terminus, True) if terminus is not None else None
    candidates = set()
    for path in DATA["lines"][line]["paths"]:
        if origin not in path or destination not in path:
            continue
        first, last = path.index(origin), path.index(destination)
        step = 1 if last >= first else -1
        if direction is not None and DATA["lines"][line]["direction_steps"][str(direction)] != step:
            continue
        if terminus is not None:
            if terminus not in path or (path.index(terminus) - last) * step < 0:
                continue
        candidates.add(tuple(path[index] for index in range(first, last + step, step)))
    if not candidates:
        raise ValueError("no continuous operating path for this direction/terminus; line-5 branches are not concatenated")
    if len(candidates) != 1:
        raise ValueError("ambiguous route: specify --direction, --terminus or --stations")
    return list(next(iter(candidates)))
