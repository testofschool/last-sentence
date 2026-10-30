import io
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import record_trace


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.mark.parametrize("body", [[], {"errorMessage": []}, {"errorMessage": {"code": "INFO-000"}, "realtimePositionList": {}}])
def test_unexpected_provider_schema_is_a_gap(body):
    rows, error = record_trace.poll("2호선", opener=lambda *a, **k: Response(json.dumps(body).encode()))
    assert rows is None
    assert error in ("invalid-schema", "invalid-record-list")


def test_provider_observations_are_not_expanded_to_invented_trains():
    body = {"errorMessage": {"code": "INFO-000"}, "realtimePositionList": [{"trainNo": "42", "statnNm": "강남", "unneeded": "ignore"}]}
    rows, error = record_trace.poll("2호선", opener=lambda *a, **k: Response(json.dumps(body).encode()))
    assert error is None
    assert len(rows) == 1
    assert rows[0]["trainNo"] == "42"
    assert "unneeded" not in rows[0]


def test_poll_failure_is_preserved_in_jsonl_and_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(record_trace, "poll", lambda *a: (None, "HTTP-503"))
    path = tmp_path / "trace.jsonl"
    metadata = record_trace.record(path, "2호선", minutes=1, interval=.01, max_polls=1)
    row = json.loads(path.read_text())
    assert row["gap"] is True
    assert row["error"] == "HTTP-503"
    assert metadata["gaps"] == 1
    assert metadata["observations"] == 0
    assert metadata["complete"] is False


def test_sample_fallback_after_four_consecutive_errors(tmp_path, monkeypatch):
    seen_keys = []
    def fake_poll(line, key):
        seen_keys.append(key)
        return (None, "provider-error") if key == "sample" else ([{"trainNo": "42"}], None)
    monkeypatch.setattr(record_trace, "poll", fake_poll)
    path = tmp_path / "trace.jsonl"
    metadata = record_trace.record(path, "2호선", minutes=1, interval=.001, max_polls=5, fallback_key="private-test-value")
    assert seen_keys == ["sample"] * 4 + ["private-test-value"]
    assert metadata["fallback_used"] is True
    assert "private-test-value" not in path.read_text()
    assert "private-test-value" not in path.with_suffix(".meta.json").read_text()
