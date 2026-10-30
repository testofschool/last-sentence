#!/usr/bin/env python3
"""Summarize consecutive scheduled stops from a downloaded public Seoul CSV.

This is a dated corroborating source, not evidence of current service or a
complete topology. No network calls, train observations or ETA samples are made.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

SOURCE = "https://data.seoul.go.kr/dataList/OA-22522/L/1/datasetView.do"


def canonical(name):
    return name.split("(", 1)[0].split("（", 1)[0].strip()


def seconds(value):
    try:
        h, m, s = map(int, value.split(":"))
        if not (0 <= h <= 30 and 0 <= m < 60 and 0 <= s < 60):
            return None
        return h * 3600 + m * 60 + s
    except (ValueError, TypeError, AttributeError):
        return None


def extract(rows):
    groups = collections.defaultdict(set)
    stations = collections.defaultdict(set)
    totals = collections.Counter()
    for row in rows:
        line = row.get("LINE")
        if line not in {"2", "5", "7"} or row.get("GUBHANG") != "0":
            continue
        station = canonical(row.get("STATION_NM", ""))
        arrival, departure = seconds(row.get("STT")), seconds(row.get("EDT"))
        when = arrival if arrival else departure
        if not station or not when:
            continue
        totals[line] += 1
        stations[line].add((row.get("SI_ID", ""), station))
        identity = (line, row.get("WEEKTAG"), row.get("INOUTTAG"), row.get("TRAIN_NO"),
                    canonical(row.get("ST_STT_NM", "")), canonical(row.get("ED_STT_NM", "")))
        groups[identity].add((when, station))
    pairs = collections.defaultdict(collections.Counter)
    rejected = collections.Counter()
    for identity, events in groups.items():
        for a, b in zip(sorted(events), sorted(events)[1:]):
            # Same-time stations or a service break cannot establish an edge.
            if a[1] == b[1] or not 0 < b[0] - a[0] <= 900:
                rejected[identity[0]] += 1
                continue
            pairs[identity[0]][tuple(sorted((a[1], b[1])))] += 1
    return {line + "호선": {
        "scheduled_rows": totals[line],
        "stations": [{"code": code, "name": name} for code, name in sorted(stations[line])],
        "edges": [{"stations": list(pair), "scheduled_occurrences": count}
                  for pair, count in sorted(pairs[line].items()) if count >= 2],
        "unconfirmed_singleton_pairs": [{"stations": list(pair), "scheduled_occurrences": count}
                  for pair, count in sorted(pairs[line].items()) if count < 2],
        "rejected_gaps_or_duplicates": rejected[line],
    } for line in ("2", "5", "7")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("evidence/topology/timetable-adjacency.json"))
    args = parser.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as stream:
        lines = extract(csv.DictReader(stream))
    result = {"schema": "last-sentence/scheduled-adjacency-v1", "source_url": SOURCE,
              "source_filename": "서울교통공사_도시철도열차운행시각표(250930).csv",
              "source_snapshot_date": "2025-09-30", "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "source_bytes": args.csv.stat().st_size, "source_sha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
              "method": "Consecutive normal-service scheduled stops grouped by line/day/direction/train/origin/terminus; arrival time or origin departure; gaps >900 seconds rejected; pairs need >=2 scheduled occurrences, singleton candidates retained separately.",
              "limits": "Dated scheduled-stop corroboration only. Not current service, complete topology, actual train movement or ETA training observations. Operators may omit stops outside their scope. Names retain this source's date.",
              "lines": lines}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    for line, item in lines.items():
        print(line, "stations", len(item["stations"]), "edges", len(item["edges"]), "rows", item["scheduled_rows"])


if __name__ == "__main__":
    main()
