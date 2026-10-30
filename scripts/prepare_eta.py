#!/usr/bin/env python3
"""Build one provenance-bound ETA artifact from a single trace snapshot."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

from eta_model import fit, evaluate, timestamp

ROOT = Path(__file__).resolve().parents[1]

def prepare(path):
    raw = Path(path).read_bytes()
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("trace row must be an object")
        timestamp(row.get("ts"))
        rows.append(row)
    model, evaluation = fit(rows), evaluate(rows)
    meta_path = Path(path).with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    return {"schema":"last-sentence/eta-bundle-v1", "trace_sha256":hashlib.sha256(raw).hexdigest(),
            "prepared_at":dt.datetime.now(dt.timezone.utc).isoformat(), "recording_complete":bool(meta.get("complete")),
            "model":model,"evaluation":evaluation,"notice":"Experimental estimate from station-arrival proxy observations. Held-out windows overlap; a passed median-error gate is not a confidence interval or a guarantee of ±30-second narration."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path, nargs="?", default=ROOT/"web/replay/trace_2026-10-30.jsonl")
    p.add_argument("--out", type=Path, default=ROOT/"evidence/eta_bundle.json")
    args=p.parse_args()
    result=prepare(args.trace)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    shared = {"trace_sha256":result["trace_sha256"],"prepared_at":result["prepared_at"]}
    for field, name in (("model","eta_model.json"),("evaluation","eta_evaluation.json")):
        (args.out.parent/name).write_text(json.dumps({**result[field],**shared},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"path":str(args.out),"n":result["evaluation"]["n"],"gate":result["evaluation"]["gate_lte_15_percent"]}))

if __name__=="__main__":
    main()
