#!/usr/bin/env python3
"""Freeze the actual windows intended for the balanced model timing experiment.

This selects observations and fits held-out ETAs only. No model requests, speech
measurements, or policy success results are produced.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from eta_model import load_trace
from model_simulation import select_windows


def plan(trace,journeys=30,segments=4):
    trace=Path(trace);raw=trace.read_bytes();rows=load_trace(trace)
    if trace.read_bytes()!=raw:
        raise ValueError("trace changed while taking the selection snapshot; retry without inference")
    selected=select_windows(rows,journeys,segments)
    meta_path=trace.with_suffix('.meta.json');meta=json.loads(meta_path.read_text()) if meta_path.exists() else {}
    windows=[]
    for selected_window in selected:
        events=selected_window['events'];origin=events[0]['t']
        windows.append({"id":selected_window['id'],"line":selected_window['line'],"trainNo":selected_window['trainNo'],
            "held_out_train_identity":selected_window['identity'],"stations":[{"name":event['station'],"offset_s":event['t']-origin} for event in events],
            "initial_forecast_s":selected_window['initial_forecast_s'],"held_out_full_identity":True,
            "arrival_event":"station-arrival-proxy","forecast_source":"other-train-identities-in-offline-recording"})
    return {"schema":"last-sentence/recorded-matrix-windows-v1","trace_path":str(trace),"trace_sha256":hashlib.sha256(raw).hexdigest(),
        "recording_complete":bool(meta.get('complete')),"requested_windows":journeys,"selected_windows":len(windows),
        "windows_per_line":dict(sorted(Counter(window['line'] for window in windows).items())),"windows":windows,
        "model_execution_performed":False,"actual_model_requests":0,
        "notice":"Planned selection of actual recorded windows only. May contain overlapping windows from the same train; not independent journeys. No model-backed policy comparison, speech timing, or door-open result is measured."}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace",type=Path,nargs='?',default=Path('web/replay/trace_2026-10-30_all_lines.jsonl'))
    parser.add_argument("--journeys",type=int,default=30)
    parser.add_argument("--window-segments",type=int,default=4)
    parser.add_argument("--out",type=Path,default=Path('evidence/matrix_windows.json'))
    args=parser.parse_args();result=plan(args.trace,args.journeys,args.window_segments)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('selected_windows','windows_per_line','recording_complete')},ensure_ascii=False))


if __name__=='__main__':
    main()
