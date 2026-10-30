#!/usr/bin/env python3
"""Derive record-backed replay clocks from contiguous arrival observations.

These clocks expose the already-recorded future for a demonstration. They are
not ETA forecasts, model runs, observed door events, or accuracy measurements.
"""
import argparse
import hashlib
import json
from pathlib import Path

from eta_model import arrivals, load_trace


def build(trace_path, max_journeys=5, max_stations=5):
    if max_journeys < 1 or max_stations < 2:
        raise ValueError("max_journeys must be positive and max_stations at least two")
    trace_path = Path(trace_path)
    chains, rejected = arrivals(load_trace(trace_path))
    metadata_path = trace_path.with_suffix(".meta.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    journeys = []
    # Select one longest contiguous chain per train identity, then display only
    # its first observed window. Raw traces and ETA evaluation stay unchanged.
    ranked = sorted(chains, key=lambda c: (-len(c), c[0]["t"], c[0]["identity"]))
    selected = []
    identities = set()
    for chain in ranked:
        if chain[0]["identity"] in identities:
            continue
        selected.append(chain)
        identities.add(chain[0]["identity"])
        if len(selected) >= max_journeys:
            break
    for i, full_chain in enumerate(selected, 1):
        chain = full_chain[:max_stations]
        identity = chain[0]["identity"]
        train_no = identity.rsplit("|", 1)[-1]
        duration = chain[-1]["t"] - chain[0]["t"]
        journeys.append({"id": f"recorded-{train_no}-{i}", "line": chain[0]["line"], "trainNo": train_no,
                         "source": chain[0]["source"],
                         "arrival_event": "station-arrival-proxy", "eta_s": duration,
                         "clock_kind": "known-recorded-timeline-not-forecast", "forecast_s": None,
                         "stations": [{"name": event["station"], "offset_s": event["t"] - chain[0]["t"]} for event in chain],
                         "recorded_start_epoch_s": chain[0]["t"], "recorded_end_epoch_s": chain[-1]["t"],
                         "partial_route": True, "train_identity": identity,
                         "total_observed_station_count": len(full_chain), "replay_window_station_count": len(chain),
                         "window_limited": len(chain) < len(full_chain)})
    return {"schema": "last-sentence/replay-v1", "provenance": "recorded-observations",
            "notice": "Recorded Seoul station-arrival observations with a known replay clock. Story scheduling against that clock is a demonstration, not a model/ETA accuracy result or a door-open measurement.",
            "trace_path": str(trace_path), "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            "replay_window_max_stations": max_stations,
            "window_selection": "First observed window of the longest contiguous chain per train identity; partial observed route, not a complete journey.",
            "partial": not metadata.get("complete", False), "recording_complete": metadata.get("complete", False),
            "polls": metadata.get("polls"), "observations": metadata.get("observations"), "gaps": metadata.get("gaps"),
            "timing_uncertainty": {"provider_timestamp": "recptnDt for trainSttus=1", "poll_interval_s": metadata.get("interval_s"),
                                   "provider_lag_s": "unmeasured", "door_open_offset_s": "unmeasured",
                                   "continuity": "Adjacent known station pairs only; no interpolated or skipped stations; 10–600 seconds per observed segment."},
            "rejected": rejected, "journeys": journeys}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("--out", type=Path, default=Path("web/replay/recorded-manifest.json"))
    p.add_argument("--max-journeys", type=int, default=5)
    p.add_argument("--max-stations", type=int, default=5)
    args = p.parse_args()
    result = build(args.trace, args.max_journeys, args.max_stations)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(args.out), "journeys": len(result["journeys"]), "partial": result["partial"]}))


if __name__ == "__main__":
    main()
