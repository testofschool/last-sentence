#!/usr/bin/env python3
"""Build one provenance-bound ETA artifact from a single trace snapshot."""
import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from eta_model import fit, evaluate, timestamp

ROOT = Path(__file__).resolve().parents[1]

def prepare(path, line=None, topology_path=None):
    raw = Path(path).read_bytes()
    rows = []
    for source_line in raw.decode("utf-8").splitlines():
        if not source_line.strip():
            continue
        row = json.loads(source_line)
        if not isinstance(row, dict):
            raise ValueError("trace row must be an object")
        timestamp(row.get("ts"))
        if line is None or row.get('line') == line:
            rows.append(row)
    model, evaluation = fit(rows), evaluate(rows)
    meta_path = Path(path).with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    result = {"schema":"last-sentence/eta-bundle-v1", "trace_sha256":hashlib.sha256(raw).hexdigest(),
            "prepared_at":dt.datetime.now(dt.timezone.utc).isoformat(), "recording_complete":bool(meta.get("complete")),
            "model":model,"evaluation":evaluation,"notice":"Experimental estimate from station-arrival proxy observations. Held-out windows overlap; a passed median-error gate is not a confidence interval or a guarantee of ±30-second narration."}
    if line is not None:
        result['line'] = line
    if line in ('5호선', '7호선'):
        topology_raw = Path(topology_path or ROOT/'web/replay/topology.json').read_bytes()
        topology = json.loads(topology_raw)
        if topology.get('schema') != 'last-sentence/topology-v1' or line not in topology.get('lines', {}):
            raise ValueError('the requested line has no authoritative topology snapshot')
        result['topology_sha256'] = hashlib.sha256(topology_raw).hexdigest()
        result['topology'] = {'schema':topology['schema'], 'line':line, **topology['lines'][line], 'sources':topology.get('sources', [])}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path, nargs="?", default=ROOT/"web/replay/trace_2026-10-30.jsonl")
    p.add_argument("--out", type=Path)
    p.add_argument("--line", choices=['2호선','5호선','7호선'])
    p.add_argument("--topology", type=Path, default=ROOT/'web/replay/topology.json')
    args=p.parse_args()
    if args.out is None:
        suffix='' if args.line in (None,'2호선') else '_'+args.line.replace('호선','')
        args.out=ROOT/'evidence'/f'eta_bundle{suffix}.json'
    result=prepare(args.trace, args.line, args.topology)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    shared = {"trace_sha256":result["trace_sha256"],"prepared_at":result["prepared_at"]}
    suffix='' if args.line in (None,'2호선') else '_'+args.line.replace('호선','')
    for field, name in (("model",f"eta_model{suffix}.json"),("evaluation",f"eta_evaluation{suffix}.json")):
        (args.out.parent/name).write_text(json.dumps({**result[field],**shared},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"path":str(args.out),"n":result["evaluation"]["n"],"gate":result["evaluation"]["gate_lte_15_percent"]}))

if __name__=="__main__":
    main()
