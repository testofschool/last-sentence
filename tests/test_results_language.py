import copy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from make_results import language_pair_section, render
from run_matrix import SUPER, ULTRA


def pair():
    return [{"id": "same-window", "line": "5호선", "trainNo": "42", "exit_station": "강동", "policy": "sentence_replan",
             "lang": lang, "landing_error_s": error, "cost_usd": cost, "tokens": 120, "p50_latency_ms": 100,
             "p95_latency_ms": 420, "conductor_calls": 3, "writer_calls": 1, "tool_calls_supported": True, "tavily_ok": None,
             "writer_models_requested": [model], "writer_models_reported": [model], "model_identities_verified": True}
            for lang, model, error, cost in [("en", SUPER, -7, .002), ("ko", ULTRA, 11, .008)]]


def test_language_table_keeps_same_journey_models_cost_latency_and_unrun_fact_distinct():
    text = "\n".join(language_pair_section({"language_pair": pair(), "mode": "model-backed-timing-simulation"}))
    assert "same frozen journey" in text and "INCOMPLETE_PAIR" not in text
    assert "| en | Super | -7.0 s | $0.002000 | 120 | 100.0 ms | 420.0 ms |" in text
    assert "| ko | Ultra | 11.0 s | $0.008000 |" in text
    assert "| en | 3 | 1 | true | not recorded |" in text
    assert "browser TTS remains unmeasured" in text


def test_partial_or_different_train_pair_is_never_called_paired():
    rows = pair()
    for values in [rows[:1], [rows[0], dict(rows[1], trainNo="other")]]:
        assert "INCOMPLETE_PAIR" in "\n".join(language_pair_section({"language_pair": values}))


def test_unknown_identity_and_cost_do_not_become_expected_models_or_zero():
    rows = pair();rows[0].update(model_identities_verified=False, cost_usd=None)
    text = "\n".join(language_pair_section({"language_pair": rows}))
    assert "| en | UNVERIFIED | -7.0 s | UNKNOWN |" in text
    assert "| en | Super |" not in text


def test_language_table_also_reads_simulator_call_receipts_and_checks_exact_identity():
    rows = pair()
    for row in rows:
        model = row.pop("writer_models_requested")[0]
        row.pop("writer_models_reported");row.pop("model_identities_verified")
        row["receipts"] = [{"calls": [{"model": model, "requested_model": model,
            "provider_reported_model": model, "identity_match": True}]}]
    text = "\n".join(language_pair_section({"language_pair": rows}))
    assert "| en | Super |" in text and "| ko | Ultra |" in text
    rows[1]["receipts"][0]["calls"][0]["provider_reported_model"] = SUPER
    assert "| ko | UNVERIFIED |" in "\n".join(language_pair_section({"language_pair": rows}))


def test_absent_pair_remains_explicitly_unrun_and_mock_transport_is_labeled():
    assert "UNRUN" in "\n".join(language_pair_section({}))
    text = "\n".join(language_pair_section({"language_pair": pair(), "execution_transport": "injected-test-transport"}))
    assert "mocked, not actual provider measurements" in text


def test_renderer_includes_language_table_and_labels_quantile_aggregation(tmp_path):
    rows = pair();policy_row = copy.deepcopy(rows[0]);policy_row.update(policy="fixed_clip")
    output = tmp_path / "RESULTS.md"
    render({"mode": "model-backed-timing-simulation", "rows": [policy_row], "language_pair": rows,
            "actual_api_cost_usd": .012, "notice": "Injected fixture"}, output)
    text = output.read_text()
    assert "## English / Korean comparison" in text
    assert "Median story call p95" in text and "not pooled call percentiles" in text
    assert output.with_name("landing-error.svg").exists()
