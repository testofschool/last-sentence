#!/usr/bin/env python3
"""Combine observed trace snapshots without filling gaps or inventing trains."""
import argparse
import hashlib
import json
from pathlib import Path

from eta_model import timestamp


def combine(paths, output):
    rows, recordings = [], []
    for filename in paths:
        path = Path(filename)
        raw = path.read_bytes()
        parsed = []
        truncated = bool(raw and not raw.endswith(b"\n"))
        lines = raw.splitlines()
        if truncated:
            lines = lines[:-1]
        for number, line in enumerate(lines,1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row,dict):
                raise ValueError(f"trace {path} line {number} is not an object")
            timestamp(row.get("ts"))
            if row.get("source") not in ("seoul-sample","seoul-api"):
                raise ValueError("combined recordings accept observed Seoul rows only")
            parsed.append(row)
        meta_path = path.with_suffix(".meta.json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        line_names = sorted(set(row.get("line") for row in parsed if row.get("line")))
        recordings.append({"path":str(path),"sha256":hashlib.sha256(raw).hexdigest(),"lines":line_names,
            "recording_complete":bool(meta.get("complete")) and not truncated,"metadata":meta,
            "included_records":len(parsed),"truncated_last_line_excluded":truncated})
        rows.extend(parsed)
    rows.sort(key=lambda row:(timestamp(row["ts"]),row.get("line",""),str(row.get("trainNo",""))))
    output = Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text("".join(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n" for row in rows))
    polls = set((row.get("line"),row["ts"]) for row in rows)
    meta = {"schema":"last-sentence/trace-v1","source":"seoul-sample" if all(row["source"]=="seoul-sample" for row in rows) else "seoul-api",
        "line":"combined","lines":sorted(set(row.get("line") for row in rows if row.get("line"))),
        "started_at":rows[0]["ts"] if rows else None,"last_poll_at":rows[-1]["ts"] if rows else None,
        "interval_s":20,"polls":len(polls),"observations":sum(not row.get("gap",False) for row in rows),
        "gaps":sum(bool(row.get("gap")) for row in rows),"complete":bool(recordings) and all(r["recording_complete"] for r in recordings),
        "arrival_event":"station-arrival-proxy","recordings":recordings,
        "notice":"Concatenation of actual per-line recording snapshots, sorted by poll timestamp. No gap filling, interpolation or synthetic observations."}
    output.with_suffix(".meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n")
    return meta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("traces",type=Path,nargs="+")
    p.add_argument("--out",type=Path,default=Path("web/replay/trace_2026-10-30_all_lines.jsonl"))
    args=p.parse_args()
    meta=combine(args.traces,args.out)
    print(json.dumps({k:meta[k] for k in ("lines","observations","gaps","complete")},ensure_ascii=False))


if __name__=="__main__":
    main()
