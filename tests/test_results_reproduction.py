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


def test_synthetic_report_preserves_fixture_reproduction_commands(tmp_path):
    output = tmp_path / "RESULTS.md"
    render(matrix("synthetic-timing-simulation"), output)
    reproduction = output.read_text().split("## Reproduce", 1)[1]
    assert "python3 scripts/run_matrix.py --mode simulation --out evidence/simulation-matrix.json" in reproduction
    assert "python3 scripts/make_results.py evidence/simulation-matrix.json" in reproduction


def test_in_memory_real_report_does_not_invent_a_retained_matrix_path(tmp_path):
    output = tmp_path / "RESULTS.md"
    render(matrix("model-backed-timing-simulation"), output)
    reproduction = output.read_text().split("## Reproduce", 1)[1]
    assert "source path was not supplied" in reproduction
    assert "evidence/simulation-matrix.json" not in reproduction
