"""Small strict contracts also used by deterministic replay tests."""
import math


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
