#!/usr/bin/env python3
"""ETA from observed adjacent station arrivals; no data means no estimate.

Provider arrival timestamps are not door-open timestamps. Whole train identities
are excluded from the leave-one-train-out fit. Gaps and station skips never
become invented segment observations.
"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import statistics

from topology import DATA as TOPOLOGY, canonical_station, directed_sign, resolve_route

KST = dt.timezone(dt.timedelta(hours=9))
LINE2 = "시청 을지로입구 을지로3가 을지로4가 동대문역사문화공원 신당 상왕십리 왕십리 한양대 뚝섬 성수 건대입구 구의 강변 잠실나루 잠실 잠실새내 종합운동장 삼성 선릉 역삼 강남 교대 서초 방배 사당 낙성대 서울대입구 봉천 신림 신대방 구로디지털단지 대림 신도림 문래 영등포구청 당산 합정 홍대입구 신촌 이대 아현 충정로".split()
ROUTES = {"2호선": LINE2, **{line:list(info["stations"]) for line, info in TOPOLOGY["lines"].items()}}


def timestamp(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise ValueError("non-finite timestamp")
        return float(value)
    if not isinstance(value, str):
        raise ValueError("timestamp missing")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.timestamp()


def budget(remaining_s, speech_rate_cps=4.51, margin_s=20):
    for value in (remaining_s, speech_rate_cps, margin_s):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("budget inputs must be finite numbers")
    if speech_rate_cps <= 0 or margin_s < 0:
        raise ValueError("rate must be positive and margin nonnegative")
    return max(0, math.floor((remaining_s - margin_s) * speech_rate_cps))


def load_trace(path):
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("expected an object")
                timestamp(row.get("ts"))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid trace line {number}: {type(exc).__name__}") from exc
            rows.append(row)
    return rows


def adjacent(line, a, b):
    if line != "2호선":
        return directed_sign(line, a, b) is not None
    route = ROUTES.get(line, [])
    if a not in route or b not in route:
        return False
    distance = abs(route.index(a) - route.index(b))
    return distance == 1 or (line == "2호선" and distance == len(route) - 1)


def arrivals(rows):
    groups = {}
    gap_events = []
    rejected = {"gaps": 0, "non_arrival": 0, "missing_fields": 0, "stale": 0, "synthetic": 0,
                "continuity_gaps": 0, "source_breaks": 0, "direction_breaks": 0}
    for row in rows:
        if row.get("gap"):
            rejected["gaps"] += 1
            try:
                gap_events.append((row.get("line"), timestamp(row.get("ts"))))
            except ValueError:
                pass
            continue
        if row.get("source") not in ("seoul-api", "seoul-sample"):
            rejected["synthetic"] += 1
            continue
        if str(row.get("trainSttus")) != "1":
            rejected["non_arrival"] += 1
            continue
        if not all(row.get(k) is not None for k in ("line", "trainNo", "statnNm", "updnLine", "recptnDt")):
            rejected["missing_fields"] += 1
            continue
        try:
            observed = timestamp(row["recptnDt"])
            polled = timestamp(row["ts"])
        except ValueError:
            rejected["missing_fields"] += 1
            continue
        if abs(polled - observed) > 300:
            rejected["stale"] += 1
            continue
        date = dt.datetime.fromtimestamp(observed, KST).date().isoformat()
        identity = "|".join((str(row["line"]), str(row["updnLine"]), date, str(row["trainNo"])))
        groups.setdefault(identity, []).append({"station": canonical_station(row["line"], row["statnNm"]), "t": observed, "polled_t": polled,
                                               "line": row["line"], "identity": identity, "source": row["source"]})
    chains = []
    for identity, events in sorted(groups.items()):
        events.sort(key=lambda e: (e["t"], e["polled_t"], e["station"]))
        chain = []
        travel_direction = None
        for event in events:
            if chain:
                previous = chain[-1]
                source_break = event["source"] != previous["source"]
                gap_break = any((line is None or line == event["line"]) and
                                (previous["polled_t"] < at <= event["polled_t"] or previous["t"] < at <= event["t"])
                                for line, at in gap_events)
                if source_break or gap_break:
                    rejected["source_breaks"] += int(source_break)
                    rejected["continuity_gaps"] += int(gap_break)
                    if len(chain) >= 2:
                        chains.append(chain)
                    chain = []
                    travel_direction = None
            if chain and event["station"] == chain[-1]["station"]:
                continue
            if chain:
                seconds = event["t"] - chain[-1]["t"]
                if not adjacent(event["line"], chain[-1]["station"], event["station"]) or not 10 <= seconds <= 600:
                    if len(chain) >= 2:
                        chains.append(chain)
                    chain = []
                    travel_direction = None
                else:
                    if event["line"] == "2호선":
                        route = ROUTES[event["line"]]
                        difference = route.index(event["station"]) - route.index(chain[-1]["station"])
                        direction = 1 if difference % len(route) == 1 else -1
                    else:
                        direction = directed_sign(event["line"], chain[-1]["station"], event["station"])
                    if travel_direction is not None and direction != travel_direction:
                        rejected["direction_breaks"] += 1
                        if len(chain) >= 2:
                            chains.append(chain)
                        chain = []
                        travel_direction = None
                    else:
                        travel_direction = direction
            chain.append(event)
        if len(chain) >= 2:
            chains.append(chain)
    return chains, rejected


def fit(rows, exclude_train=None):
    chains, rejected = arrivals(rows)
    samples, line_samples = {}, {}
    for chain in chains:
        if chain[0]["identity"] == exclude_train:
            continue
        for a, b in zip(chain, chain[1:]):
            value = b["t"] - a["t"]
            key = "|".join((a["line"], a["station"], b["station"]))
            samples.setdefault(key, []).append({"seconds": value, "train": a["identity"]})
            line_samples.setdefault(a["line"], []).append(value)
    segments = {}
    for key, values in samples.items():
        if len(values) >= 2:
            seconds = [v["seconds"] for v in values]
            segments[key] = {"median_s": statistics.median(seconds), "sd_s": statistics.pstdev(seconds),
                             "n": len(values), "trains": len(set(v["train"] for v in values))}
    line_medians = {line: statistics.median(values) for line, values in line_samples.items() if len(values) >= 2}
    return {"schema": "last-sentence/eta-v1", "source": "recorded-station-arrival-proxy",
            "segments": segments, "line_medians_s": line_medians,
            "segment_observations": sum(map(len, samples.values())), "usable_segments": len(segments), "rejected": rejected}


def predict(model, line, stations, elapsed_s=0):
    stations = [canonical_station(line, name, True) for name in stations]
    if len(stations) < 2:
        raise ValueError("at least two ordered stations required")
    if not math.isfinite(elapsed_s) or elapsed_s < 0:
        raise ValueError("elapsed_s must be finite and nonnegative")
    total = 0
    fallback = []
    if line != "2호선":
        signs = {directed_sign(line, a, b) for a,b in zip(stations, stations[1:])}
        if None not in signs and len(signs) > 1:
            raise ValueError("route changes operating direction or crosses line-5 branches; supply one continuous train path")
    for a, b in zip(stations, stations[1:]):
        if not adjacent(line, a, b):
            raise ValueError("route contains unobserved topology or a station skip")
        key = "|".join((line, a, b))
        segment = model["segments"].get(key)
        if segment:
            total += segment["median_s"]
        elif line in model["line_medians_s"]:
            total += model["line_medians_s"][line]
            fallback.append([a, b])
        else:
            raise ValueError("insufficient recorded observations; ETA unavailable")
    return {"remaining_s": max(0, total - elapsed_s), "fallback_segments": fallback,
            "arrival_event": "station-arrival-proxy", "source": model["source"]}


def evaluate(rows):
    chains, rejected = arrivals(rows)
    errors = []
    excluded_predictions = 0
    identities = sorted(set(chain[0]["identity"] for chain in chains))
    for identity in identities:
        model = fit(rows, exclude_train=identity)
        for chain in chains:
            if chain[0]["identity"] != identity:
                continue
            for length in range(3, min(10, len(chain) - 1) + 1):
                for i in range(len(chain) - length):
                    window = chain[i:i + length + 1]
                    actual = window[-1]["t"] - window[0]["t"]
                    try:
                        prediction = predict(model, window[0]["line"], [e["station"] for e in window])["remaining_s"]
                    except ValueError:
                        excluded_predictions += 1
                        continue
                    errors.append(abs(prediction - actual) / actual)
    median = statistics.median(errors) if errors else None
    return {"method": "leave-one-train-identity-out", "station_horizons": [3, 10], "n": len(errors),
            "train_identities": len(identities), "median_relative_error": median,
            "gate_lte_15_percent": None if median is None else median <= 0.15,
            "status": "measured" if errors else "insufficient-recorded-data", "excluded_predictions": excluded_predictions,
            "arrival_event": "station-arrival-proxy", "rejected": rejected}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("trace", type=Path)
    b.add_argument("--out", type=Path, default=Path("evidence/eta_model.json"))
    e = sub.add_parser("evaluate")
    e.add_argument("trace", type=Path)
    e.add_argument("--out", type=Path)
    q = sub.add_parser("predict")
    q.add_argument("--model", type=Path, default=Path("evidence/eta_model.json"))
    q.add_argument("--line", default="2호선")
    q.add_argument("--stations", help="Comma-separated ordered station path; preserves the original explicit-path interface.")
    q.add_argument("--from", dest="from_station")
    q.add_argument("--to", dest="to_station")
    q.add_argument("--direction", choices=["0", "1"])
    q.add_argument("--terminus")
    q.add_argument("--at", help="Explicit forecast-anchor timestamp; never interpreted as an observed arrival.")
    q.add_argument("--elapsed-s", type=float, default=0)
    args = p.parse_args()
    if args.command == "build":
        result = fit(load_trace(args.trace))
    elif args.command == "evaluate":
        result = evaluate(load_trace(args.trace))
    else:
        try:
            if args.stations:
                if args.from_station or args.to_station:
                    p.error("use either --stations or --from/--to")
                if args.direction is not None or args.terminus is not None:
                    p.error("--direction/--terminus apply to --from/--to; --stations already specifies the complete path")
                route = args.stations.split(",")
            elif args.from_station and args.to_station:
                route = resolve_route(args.line, args.from_station, args.to_station, args.direction, args.terminus, LINE2)
            else:
                p.error("predict requires --stations or both --from and --to")
            model = json.loads(args.model.read_text())
            if len(route) == 1 and route[0] in ROUTES.get(args.line, []):
                result = {"remaining_s":0,"fallback_segments":[],"arrival_event":"station-arrival-proxy","source":model["source"]}
            else:
                result = predict(model, args.line, route, args.elapsed_s)
            result["route"] = route
            if args.at:
                anchor = timestamp(args.at)
                result["forecast_anchor_at"] = dt.datetime.fromtimestamp(anchor, KST).isoformat()
                result["estimated_arrival_at"] = dt.datetime.fromtimestamp(anchor + result["remaining_s"], KST).isoformat()
                result["clock_kind"] = "explicit-forecast-anchor-not-observed-arrival"
        except (ValueError, KeyError) as exc:
            p.error(str(exc))
    if getattr(args, "out", None):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
