"""Small strict contracts also used by deterministic replay tests."""
import math

RECEIPT_SCHEMA = "last-sentence/receipt-v2"


def validate_model_identity(receipt, allowed_models, expected_model=None):
    """Verify the requested and provider-reported identifiers independently."""
    if not isinstance(receipt, dict) or receipt.get("model") not in allowed_models:
        raise ValueError("known real model receipts required")
    if receipt.get("receipt_schema") != RECEIPT_SCHEMA:
        raise ValueError("unsupported receipt schema; actual cost unknown")
    requested = receipt.get("requested_model")
    if requested not in allowed_models:
        raise ValueError("known requested model identity required; actual cost unknown")
    if expected_model is not None and requested != expected_model:
        raise ValueError("unexpected requested model identity; actual cost unknown")
    if (receipt["model"] != requested or receipt.get("provider_reported_model") != requested
            or receipt.get("identity_match") is not True):
        raise ValueError("exact requested/provider model identity required; actual cost unknown")
    return requested


WRITER_VALIDATION_FIELDS = (
    "status", "counting_basis", "purpose", "language", "text_response", "sentence_count",
    "sentences_within_cap", "sentences_over_cap", "max_sentence_chars", "total_chars",
    "sentence_cap", "max_sentence_count", "required_sentence_count", "budget_chars",
    "scene_budget_ok", "sentence_count_ok", "sentence_lengths_ok", "ending_required",
    "ending_station_ok", "passed", "failures",
)


def validate_writer_validation(value, expected_language=None, expected_budget=None,
                               expected_ending=None, sentences=None, require_passed=False, expected_station=None):
    """Validate scalar inspection evidence, including rejected/nontext responses.

    Failed inspections retain a denominator when text was actually inspected.
    Provider failures have null counters rather than invented zero sentences.
    Only normal story calls belong in the policy/language timing comparison.
    """
    def bad():
        raise ValueError("missing or inconsistent Writer validation counters")

    if not isinstance(value, dict) or any(key not in value for key in WRITER_VALIDATION_FIELDS):
        bad()
    if (value["counting_basis"] != "trimmed-nonempty-lines/unicode-code-points"
            or value["purpose"] != "story" or value["language"] not in ("en", "ko")
            or (expected_language is not None and value["language"] != expected_language)
            or value["sentence_cap"] != (40 if value["language"] == "ko" else 90)
            or value["max_sentence_count"] != 100 or value["required_sentence_count"] is not None
            or not isinstance(value["budget_chars"], int) or isinstance(value["budget_chars"], bool)
            or not 1 <= value["budget_chars"] <= 4000
            or (expected_budget is not None and value["budget_chars"] != expected_budget)
            or not isinstance(value["ending_required"], bool)
            or (expected_ending is not None and value["ending_required"] != expected_ending)):
        bad()
    counters = ("sentence_count", "sentences_within_cap", "sentences_over_cap", "max_sentence_chars", "total_chars")
    checks = ("scene_budget_ok", "sentence_count_ok", "sentence_lengths_ok", "ending_station_ok")
    failures = value["failures"]
    if not isinstance(failures, list) or not all(isinstance(item, str) for item in failures) or len(failures) != len(set(failures)):
        bad()
    if value["text_response"] is not True:
        expected_status, expected_failure = (("not_inspected", "completion_not_inspected")
                                             if value["text_response"] is None else ("rejected", "non_text"))
        if (value["text_response"] is not None and value["text_response"] is not False
                or value["status"] != expected_status or failures != [expected_failure]
                or value["passed"] is not False or any(value[key] is not None for key in counters + checks)):
            bad()
    else:
        if any(not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] < 0 for key in counters):
            bad()
        count, within, over, maximum, total = (value[key] for key in counters)
        cap = value["sentence_cap"]
        if (within + over != count or total < maximum
                or (count == 0 and (maximum != 0 or total != 0))
                or (count > 0 and (maximum < 1 or total < count))
                or (over == 0 and maximum > cap) or (over > 0 and maximum <= cap)
                or total < over * (cap + 1) + within):
            bad()
        expected_checks = {"scene_budget_ok": total <= value["budget_chars"],
                           "sentence_count_ok": 0 < count <= 100,
                           "sentence_lengths_ok": over == 0}
        if any(value[key] is not expected for key, expected in expected_checks.items()):
            bad()
        if ((value["ending_required"] and not isinstance(value["ending_station_ok"], bool))
                or (not value["ending_required"] and value["ending_station_ok"] is not None)):
            bad()
        expected_failures = set()
        if count == 0: expected_failures.add("empty")
        if count > 100: expected_failures.add("too_many_sentences")
        if over: expected_failures.add("sentence_cap")
        if not expected_checks["scene_budget_ok"]: expected_failures.add("scene_budget")
        if value["ending_required"] and not value["ending_station_ok"]: expected_failures.add("station_ending")
        passed = not expected_failures
        if (set(failures) != expected_failures or value["passed"] is not passed
                or value["status"] != ("valid" if passed else "rejected")):
            bad()
        if sentences is not None:
            if not isinstance(sentences, list) or any(not isinstance(s, str) or not s for s in sentences):
                bad()
            lengths = [len(sentence) for sentence in sentences]
            observed = (len(lengths), sum(n <= cap for n in lengths), sum(n > cap for n in lengths),
                        max(lengths, default=0), sum(lengths))
            if observed != (count, within, over, maximum, total):
                bad()
            if (value["ending_required"] and expected_station is not None
                    and value["ending_station_ok"] is not bool(sentences and sentences[-1].endswith(expected_station))):
                bad()
    if require_passed and value["passed"] is not True:
        raise ValueError("Writer output did not pass its recorded validation")
    return {key: value[key] for key in WRITER_VALIDATION_FIELDS}


def finite_number(value, minimum=0):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= minimum


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError("plan must be an object")
    if not isinstance(plan.get("stations_left"), int) or isinstance(plan["stations_left"], bool) or plan["stations_left"] < 0:
        raise ValueError("invalid stations_left")
    if not finite_number(plan.get("remaining_s")):
        raise ValueError("invalid remaining_s")
    if not isinstance(plan.get("budget_chars"), int) or isinstance(plan["budget_chars"], bool) or plan["budget_chars"] < 0:
        raise ValueError("invalid budget_chars")
    if not isinstance(plan.get("log"), str) or len(plan["log"]) > 500:
        raise ValueError("invalid log")
    if not isinstance(plan.get("ops"), list):
        raise ValueError("invalid ops")
    for op in plan["ops"]:
        if not isinstance(op, dict) or op.get("op") not in ("insert", "drop", "compress"):
            raise ValueError("invalid scene operation")
        if not isinstance(op.get("reason"), str) or not isinstance(op.get("scene"), (str, int)) or isinstance(op.get("scene"), bool):
            raise ValueError("invalid scene operation fields")
    return plan


def validate_write(body, lang="en", station=None):
    if not isinstance(body, dict) or not isinstance(body.get("model"), str):
        raise ValueError("model missing")
    sentences = body.get("sentences")
    cap = 40 if lang == "ko" else 90
    if not isinstance(sentences, list) or not sentences or any(not isinstance(s, str) or not s.strip() or len(s) > cap for s in sentences):
        raise ValueError("invalid or overlong sentence")
    if station and not sentences[-1].rstrip(".!。 ").endswith(station):
        raise ValueError("last sentence does not end with station")
    return body


def sentence_replay(arrival_s, forecast_s, sentence_durations, updates):
    """Clock scheduler for a fixed mocked Writer, with forecast updates.

    Sentences are indivisible. At sentence boundaries consume the latest ETA
    update that was actually available then; wait to begin the final sentence.
    arrival_s is used only for scoring after scheduling, never by the policy.
    """
    if not sentence_durations or any(not finite_number(x, 0.001) for x in sentence_durations):
        raise ValueError("positive sentence durations required")
    if not finite_number(arrival_s) or not finite_number(forecast_s):
        raise ValueError("invalid time")
    clock = 0.0
    target = forecast_s
    pending = sorted(updates, key=lambda item: item[0])
    used = []
    for index, duration in enumerate(sentence_durations):
        while pending and pending[0][0] <= clock:
            at, remaining = pending.pop(0)
            if not finite_number(at) or not finite_number(remaining):
                raise ValueError("invalid update")
            target = at + remaining
            used.append(at)
        if index == len(sentence_durations) - 1:
            # Updates during a wait are available before the final utterance.
            while pending and pending[0][0] <= max(clock, target - duration):
                at, remaining = pending.pop(0)
                if not finite_number(at) or not finite_number(remaining):
                    raise ValueError("invalid update")
                target = at + remaining
                used.append(at)
            clock = max(clock, target - duration)
        clock += duration
    return {"landing_error_s": clock - arrival_s, "story_end_s": clock, "updates_used": used,
            "evidence_kind": "deterministic-mocked-writer-simulation"}
