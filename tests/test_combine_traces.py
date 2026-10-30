import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from combine_traces import combine


def test_combination_preserves_observations_gaps_and_per_line_completeness(tmp_path):
    first=tmp_path/"line2.jsonl";second=tmp_path/"line5.jsonl"
    a={"ts":"2026-10-30T10:00:00+09:00","line":"2호선","trainNo":"1","source":"seoul-sample"}
    b={"ts":"2026-10-30T10:01:00+09:00","line":"5호선","source":"seoul-sample","gap":True,"error":"HTTP-503"}
    first.write_text(json.dumps(a)+"\n");second.write_text(json.dumps(b)+"\n")
    first.with_suffix('.meta.json').write_text(json.dumps({"complete":True}))
    second.with_suffix('.meta.json').write_text(json.dumps({"complete":False}))
    original=(first.read_bytes(),second.read_bytes())
    output=tmp_path/"combined.jsonl";meta=combine([second,first],output)
    assert [json.loads(line) for line in output.read_text().splitlines()] == [a,b]
    assert meta["observations"]==1 and meta["gaps"]==1
    assert meta["complete"] is False
    assert [r["recording_complete"] for r in meta["recordings"]] == [False,True]
    assert (first.read_bytes(),second.read_bytes())==original


def test_combination_refuses_synthetic_rows(tmp_path):
    source=tmp_path/"synthetic.jsonl"
    source.write_text(json.dumps({"ts":"2026-10-30T10:00:00+09:00","line":"5호선","source":"synthetic-fixture"})+"\n")
    with pytest.raises(ValueError,match="observed Seoul"):
        combine([source],tmp_path/"out.jsonl")
