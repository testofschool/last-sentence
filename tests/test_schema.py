import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from contracts import sentence_replay, validate_plan, validate_write
from run_matrix import LIGHTNING, SUPER, ULTRA, cost_plan, measured_import, synthetic_matrix

ROOT = Path(__file__).resolve().parents[1]


def plan():
    return {"stations_left": 3, "remaining_s": 300, "budget_chars": 1262, "ops": [{"scene": "4", "op": "compress", "reason": "Less time"}], "log": "3 stations left"}


def test_plan_schema():
    assert validate_plan(plan())["stations_left"] == 3
    for key, value in (("remaining_s", float("nan")), ("stations_left", True), ("budget_chars", -1), ("ops", [{"scene": 4, "op": "invent", "reason": "x"}])):
        body = dict(plan(), **{key: value})
        with pytest.raises(ValueError):
            validate_plan(body)


def test_writer_schema_and_final_station():
    assert validate_write({"model": SUPER, "sentences": ["You arrive at 강남."]}, station="강남")
    assert validate_write({"model": ULTRA, "sentences": ["이야기의 끝은 강남."]}, lang="ko", station="강남")
    with pytest.raises(ValueError):
        validate_write({"model": SUPER, "sentences": ["a" * 91]})
    with pytest.raises(ValueError):
        validate_write({"model": ULTRA, "sentences": ["가" * 41]}, lang="ko")
    with pytest.raises(ValueError):
        validate_write({"model": SUPER, "sentences": ["You arrive at 선릉."]}, station="강남")


@pytest.mark.parametrize("arrival,updates", [
    (560, [(125, 450), (259, 300), (411, 150)]),
    (590, [(150, 450), (303, 300), (441, 150)]),
    (555, [(132, 450), (265, 300), (402, 150)]),
])
def test_three_golden_mocked_writer_runs_land_within_30(arrival, updates):
    result = sentence_replay(arrival, 600, [12] * 35, updates)
    assert abs(result["landing_error_s"]) <= 30
    # Changing the withheld outcome must change the score, never the schedule.
    changed = sentence_replay(arrival + 200, 600, [12] * 35, updates)
    assert changed["story_end_s"] == result["story_end_s"]
    assert changed["landing_error_s"] == result["landing_error_s"] - 200


def test_scheduler_admits_overruns_instead_of_guaranteeing_success():
    result = sentence_replay(200, 600, [12] * 35, [(100, 80)])
    assert result["landing_error_s"] == 220


def test_scheduler_cannot_read_an_update_after_completion():
    result = sentence_replay(180, 200, [12] * 5, [(500, 0)])
    assert result["story_end_s"] == 200
    assert result["updates_used"] == []


def test_synthetic_matrix_contains_nine_distinct_rows_and_zero_model_calls():
    matrix = synthetic_matrix(json.loads((ROOT / "web/replay/manifest.json").read_text()))
    assert len(matrix["rows"]) == 9
    assert matrix["measured_inference_runs"] == 0
    assert sum(r["conductor_calls"] + r["writer_calls"] for r in matrix["rows"]) == 0


def test_conservative_cost_plan_refuses_over_cap():
    prices = {LIGHTNING: (.06, .24), SUPER: (.30, .90), ULTRA: (1, 3)}
    assert cost_plan(prices, 30)["allowed"] is False
    assert cost_plan(prices, 17)["allowed"] is False
    assert cost_plan(prices, 17, max_completions=2048)["allowed"] is True
    assert cost_plan(prices, 5)["allowed"] is True
    assert cost_plan(prices, 5)["max_total_completions"] == 295
    assert cost_plan(prices, 17)["max_conductor_calls"] == (17 + 2) * 12 * 3


def test_measured_import_rejects_estimated_speech_and_missing_trace(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text("")
    data = {"trace_sha256": hashlib.sha256(b"").hexdigest(), "speech_clock": "character-estimate", "rows": []}
    with pytest.raises(ValueError, match="actual browser"):
        measured_import(data, trace)


def measurement_data(tmp_path):
    record = dict(ts="2026-10-30T10:00:01+09:00",recptnDt="2026-10-30T10:00:00+09:00",trainSttus="1",trainNo="42",statnNm="강남",line="2호선",source="seoul-sample")
    trace = tmp_path / "trace.jsonl"
    trace.write_text(json.dumps(record) + "\n")
    receipt = {"model": SUPER, "usage": {"prompt_tokens": 100, "completion_tokens": 50}, "cost_usd": .000075, "latency_ms": 400,
               "pricing":{"input_price_per_million_tokens":.3,"output_price_per_million_tokens":.9}}
    row = {"id":"real-1", "trainNo":"42", "line":"2호선", "exit_station":"강남", "policy":"fixed_clip", "arrival_at":record["recptnDt"], "speech_end_at":"2026-10-30T10:00:08+09:00", "receipts":[receipt]}
    data = {"trace_sha256":hashlib.sha256(trace.read_bytes()).hexdigest(), "speech_clock":"browser-speech-end-event", "rows":[row]}
    return data, trace


def test_measured_import_requires_complete_usage_and_observed_arrival(tmp_path):
    data, trace = measurement_data(tmp_path)
    result = measured_import(data, trace)
    assert result["rows"][0]["landing_error_s"] == 8
    assert result["actual_api_cost_usd"] == .000075
    assert result["coverage"]["comparison_basis"] == "unpaired-only"
    data["rows"][0]["receipts"][0].pop("usage")
    with pytest.raises(ValueError, match="usage"):
        measured_import(data, trace)


@pytest.mark.parametrize("mutation,error", [
    ("line", "recorded station-arrival"), ("model", "known real model"), ("cost", "does not match token usage"),
    ("pricing", "per-call pricing required"),
])
def test_measured_import_rejects_mislabeled_line_unknown_model_and_bad_cost(tmp_path, mutation, error):
    data, trace = measurement_data(tmp_path)
    row = data["rows"][0]
    receipt = row["receipts"][0]
    if mutation == "line":
        row["line"] = "5호선"
    elif mutation == "model":
        receipt["model"] = "unknown-model"
    elif mutation == "cost":
        receipt["cost_usd"] = 0
    else:
        receipt.pop("pricing")
    with pytest.raises(ValueError, match=error):
        measured_import(data, trace)


def test_measured_import_reports_fully_paired_coverage_only_with_all_policies(tmp_path):
    data, trace = measurement_data(tmp_path)
    original = data["rows"][0]
    for policy in ("single_fit", "sentence_replan"):
        data["rows"].append(dict(original, policy=policy))
    result = measured_import(data, trace)
    assert result["coverage"]["comparison_basis"] == "fully-paired"
    assert result["coverage"]["complete_paired_journeys"] == 1


def test_nested_api_receipts_are_flattened_and_aggregate_cost_checked(tmp_path):
    data, trace = measurement_data(tmp_path)
    call = data["rows"][0]["receipts"][0]
    data["rows"][0]["receipts"] = [{"cost_usd":call["cost_usd"], "calls":[call]}]
    assert measured_import(data, trace)["rows"][0]["writer_calls"] == 1
    data["rows"][0]["receipts"][0]["cost_usd"] = 0
    with pytest.raises(ValueError, match="aggregate cost"):
        measured_import(data, trace)
