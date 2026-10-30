"""Retained real-input reports must not reproduce an unrelated fixture run."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_results import render


def matrix(mode):
    return {
        "mode": mode,
        "notice": "Synthetic renderer test fixture; no provider request was made.",
        "rows": [],
        "trace_sha256": "f" * 64,
        "trace_path": "retained-recorded-trace.jsonl",
        "execution_transport": "injected-test-transport",
        "actual_api_cost_usd": None,
    }


@pytest.mark.parametrize("mode", ["model-backed-timing-simulation", "recorded-browser-measurements"])
def test_cli_real_report_reproduces_its_retained_input_without_inference(tmp_path, mode):
    source = tmp_path / "recorded runs" / "run's matrix.json"
    source.parent.mkdir()
    source.write_text(json.dumps(matrix(mode)), encoding="utf-8")
    output = tmp_path / "results output.md"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/make_results.py"), str(source), "--out", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    text = output.read_text()
    reproduction = text.split("## Reproduce", 1)[1]
    command = reproduction.split("```sh\n", 1)[1].split("```", 1)[0].strip()
    assert shlex.split(command) == [
        "python3", "scripts/make_results.py", str(source), "--out", str(output)
    ]
    assert "--execute" not in command
    assert "evidence/simulation-matrix.json" not in reproduction
    assert hashlib.sha256(source.read_bytes()).hexdigest() in reproduction
    assert "f" * 64 in reproduction
    assert "retained-recorded-trace.jsonl" in reproduction
    assert "injected-test-transport" in reproduction
    assert "fresh output filename" in reproduction
    assert "no inference requests" in reproduction
    assert "Usage/catalog cost estimate represented (all retained attempts): **UNKNOWN" in text
    assert "invoice/account billing is unverified" in text
    assert "Actual API cost represented" not in text
    assert "## Scheduled evaluation coverage" not in text


def test_synthetic_report_preserves_fixture_reproduction_commands(tmp_path):
    output = tmp_path / "RESULTS.md"
    render(matrix("synthetic-timing-simulation"), output)
    text = output.read_text()
    reproduction = text.split("## Reproduce", 1)[1]
    assert "Actual API cost represented" in text
    assert "python3 scripts/run_matrix.py --mode simulation --out evidence/simulation-matrix.json" in reproduction
    assert "python3 scripts/make_results.py evidence/simulation-matrix.json" in reproduction


def test_in_memory_real_report_does_not_invent_a_retained_matrix_path(tmp_path):
    output = tmp_path / "RESULTS.md"
    data=matrix("model-backed-timing-simulation")
    data.pop('actual_api_cost_usd')
    render(data, output)
    text=output.read_text()
    reproduction = text.split("## Reproduce", 1)[1]
    assert "source path was not supplied" in reproduction
    assert "evidence/simulation-matrix.json" not in reproduction
    assert "Usage/catalog cost estimate represented (all retained attempts): **UNKNOWN" in text


def test_report_exposes_all_scheduled_slots_and_scored_only_zero_percent_rate(tmp_path):
    data = matrix('model-backed-timing-simulation')
    def counts(planned, scored, rejected):
        return {'scheduled':planned,'attempted':planned,'scored':scored,'failed':rejected,
                'rejected_model_output':rejected,'aborted':0,'unstarted':0}
    data['evaluation_coverage']={
        'total':counts(17,12,5),
        'policies':{policy:counts(5,4,1) for policy in ('fixed_clip','single_fit','sentence_replan')},
        'language_pair':{**counts(2,0,2),'languages':{'en':counts(1,0,1),'ko':counts(1,0,1)}}}
    data['rows']=[{'id':f'journey-{i}','policy':policy,'landing_error_s':45+i*10,
                   'cost_usd':.001,'p50_latency_ms':10,'p95_latency_ms':20}
                  for policy in ('fixed_clip','single_fit','sentence_replan') for i in range(4)]
    data['actual_api_cost_usd']=.014  # Includes .002 of failed-attempt cost beyond .012 scored costs.
    output=tmp_path/'RESULTS.md'
    render(data,output)
    text=output.read_text()
    assert text.index('## Scheduled evaluation coverage') < text.index('| Policy | n |')
    assert '| Total | 17 | 17 | 12 | 5 | 5 | 0 | 0 |' in text
    assert '| sentence_replan | 5 | 5 | 4 | 1 | 1 | 0 | 0 |' in text
    assert '| EN/KO pair | 2 | 2 | 0 | 2 | 2 | 0 | 0 |' in text
    assert '| KO pair | 1 | 1 | 0 | 1 | 1 | 0 | 0 |' in text
    assert '| sentence_replan | 4 | 0.0% | 0.0% |' in text
    assert 'completed, scored rows only' in text and 'no fabricated landing error' in text
    assert 'Usage/catalog cost estimate represented (all retained attempts): **$0.014000**' in text
    assert 'Policy cost/story below uses scored rows only.' in text
