#!/usr/bin/env python3
"""Describe a trace snapshot without inferring API delay or door-open timing."""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import statistics

from eta_model import KST, ROUTES, arrivals, timestamp


def distribution(values):
    values = sorted(values)
    if not values:
        return {"n": 0, "p50": None, "p95": None, "min": None, "max": None}
    return {"n": len(values), "p50": statistics.median(values),
            "p95": values[math.ceil(len(values) * .95) - 1], "min": values[0], "max": values[-1]}


def iso(seconds):
    return dt.datetime.fromtimestamp(seconds, KST).isoformat(timespec="seconds") if seconds is not None else None


def analyze(trace_path):
    trace_path = Path(trace_path)
    payload = trace_path.read_bytes()  # The hash and analysis cover the same snapshot.
    rows = []
    malformed = non_object = nonblank = 0
    for line in payload.decode("utf-8").splitlines():
        if not line.strip():
            continue
        nonblank += 1
        try:
            row = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(row, dict):
            non_object += 1
            continue
        rows.append(row)

    sources, statuses = Counter(), Counter()
    polls = {}
    gaps = 0
    times, ages = [], []
    invalid_poll = missing_provider = invalid_provider = future_ages = 0
    out_of_order = 0
    last_seen_poll = None
    identities = set()
    identity_incomplete = 0
    chain_input = []
    for row in rows:
        sources[str(row.get("source", "missing"))] += 1
        is_gap = bool(row.get("gap"))
        gaps += int(is_gap)
        if not is_gap:
            statuses[str(row.get("trainSttus", "missing"))] += 1
        try:
            polled = timestamp(row.get("ts"))
        except ValueError:
            invalid_poll += 1
            polled = None
        if polled is not None:
            times.append(polled)
            if last_seen_poll is not None and polled < last_seen_poll:
                out_of_order += 1
            last_seen_poll = polled
            poll_key = (str(row.get("line", "missing")), polled)
            polls.setdefault(poll_key, set()).add("gap" if is_gap else "observation")
        if is_gap:
            if polled is not None:
                chain_input.append(row)
            continue
        provided = row.get("recptnDt")
        if provided is None or provided == "":
            missing_provider += 1
            observed = None
        else:
            try:
                observed = timestamp(provided)
            except ValueError:
                invalid_provider += 1
                observed = None
        if observed is not None and polled is not None:
            age = polled - observed
            ages.append(age)
            future_ages += int(age < 0)
        if observed is not None and all(row.get(k) is not None for k in ("line", "updnLine", "trainNo")):
            date = dt.datetime.fromtimestamp(observed, KST).date().isoformat()
            identities.add("|".join((str(row["line"]), str(row["updnLine"]), date, str(row["trainNo"]))))
        else:
            identity_incomplete += 1
        # Keep malformed rows out of the stricter continuity extractor; counts
        # above still describe them. No missing station or timestamp is filled.
        if (polled is not None and observed is not None and isinstance(row.get("line"), str)
                and row["line"] in ROUTES and isinstance(row.get("statnNm"), str)
                and isinstance(row.get("source"), str)):
            chain_input.append(row)

    chains, rejected = arrivals(chain_input)
    segments, durations = Counter(), []
    for chain in chains:
        for a, b in zip(chain, chain[1:]):
            segments["|".join((a["line"], a["station"], b["station"]))] += 1
            durations.append(b["t"] - a["t"])
    metadata_path = trace_path.with_suffix(".meta.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else None
    metadata_fields = ("schema", "source", "line", "started_at", "last_poll_at", "finished_at",
                       "planned_minutes", "interval_s", "polls", "observations", "gaps", "complete", "interrupted")
    sampling = {key: metadata[key] for key in metadata_fields if metadata and key in metadata}
    sampling["partial"] = not bool(metadata and metadata.get("complete"))
    sampling["metadata_present"] = metadata is not None
    sampling["metadata_poll_count_matches_snapshot"] = (metadata.get("polls") == len(polls)) if metadata else None
    first, last = min(times) if times else None, max(times) if times else None
    return {"schema": "last-sentence/trace-quality-v1", "trace_path": str(trace_path),
            "trace_sha256": hashlib.sha256(payload).hexdigest(), "snapshot_bytes": len(payload),
            "nonblank_lines": nonblank, "parsed_object_records": len(rows), "invalid_json_lines": malformed,
            "non_object_lines": non_object, "observation_records": len(rows) - gaps, "gap_records": gaps,
            "record_source_counts": dict(sorted(sources.items())), "train_status_counts": dict(sorted(statuses.items())),
            "distinct_polls_from_line_and_ts": len(polls),
            "poll_status_counts": {"observation": sum(s == {"observation"} for s in polls.values()),
                                   "gap": sum(s == {"gap"} for s in polls.values()),
                                   "mixed": sum(len(s) > 1 for s in polls.values())},
            "invalid_poll_timestamp_count": invalid_poll, "out_of_order_record_timestamps": out_of_order,
            "first_poll_at": iso(first), "last_poll_at": iso(last),
            "observed_poll_span_s": last - first if times else None,
            "distinct_train_identities": len(identities), "train_identities": sorted(identities),
            "records_without_complete_train_identity": identity_incomplete,
            "receipt_timestamp_age_s": distribution(ages), "future_receipt_timestamp_count": future_ages,
            "missing_receipt_timestamp_count": missing_provider, "invalid_receipt_timestamp_count": invalid_provider,
            "receipt_timestamp_age_definition": "polled ts minus provider recptnDt. Age of the receipt timestamp only; not a measurement of transport delay, station-arrival error, or door-open offset. Negative values are retained and counted without attributing a cause.",
            "quantile_definition": "p50=sample median; p95=nearest rank ceil(0.95*n). No interpolation or extrapolation.",
            "contiguous_arrival_chains": len(chains), "chain_lengths_station_events": sorted(len(chain) for chain in chains),
            "adjacent_segment_observations": sum(segments.values()), "distinct_directed_segments": len(segments),
            "directed_segments_with_two_or_more_observations": sum(n >= 2 for n in segments.values()),
            "segment_observation_counts": dict(sorted(segments.items())),
            "arrival_proxy_segment_duration_s": distribution(durations), "continuity_rejections": rejected,
            "sampling": sampling,
            "limitations": "Descriptive counts for one trace snapshot. Repeated polls are not independent journeys. No inference about unobserved lines, trains, operating periods, model performance, or door-open accuracy."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--out", type=Path, default=Path("evidence/trace_quality.json"))
    args = parser.parse_args()
    result = analyze(args.trace)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(args.out), "records": result["parsed_object_records"],
                      "polls": result["distinct_polls_from_line_and_ts"], "partial": result["sampling"]["partial"]}))


if __name__ == "__main__":
    main()
