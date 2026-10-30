"""Guarded model-backed timing simulation over held-out recorded train windows.

No browser/audio measurement occurs here. Calls are possible only through an
explicitly enabled, protected Worker after local and server budget checks.
"""
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request

from contracts import validate_plan, validate_write
from eta_model import arrivals, budget, fit, load_trace, predict, timestamp
from run_matrix import LIGHTNING, SUPER, ULTRA, POLICIES, cost_plan, policy_coverage, prices_from_catalog


class SimulationError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Session credentials belong only to the configured Worker origin.
        return None


def select_windows(rows, count, segments=4):
    if not 3 <= segments <= 10:
        raise SimulationError("window_segments must be between 3 and 10")
    chains, _ = arrivals(rows)
    grouped = {}
    for chain in chains:
        length = min(segments, len(chain) - 1)
        if length < 3:
            continue
        for start in range(len(chain) - length):
            window = chain[start:start + length + 1]
            identity = chain[0]["identity"]
            model = fit(rows, exclude_train=identity)
            route = [event["station"] for event in window]
            try:
                forecast = predict(model, window[0]["line"], route)
            except ValueError:
                continue
            grouped.setdefault(identity, []).append({"id": f"{identity}|{window[0]['t']:.0f}|{window[-1]['t']:.0f}",
                "identity": identity, "line": window[0]["line"], "trainNo": identity.rsplit("|", 1)[-1],
                "events": window, "model": model, "initial_forecast_s": forecast["remaining_s"]})
    selected = []
    # Round-robin train identities before reusing overlapping windows.
    while len(selected) < count and any(grouped.values()):
        for identity in sorted(grouped):
            if grouped[identity] and len(selected) < count:
                selected.append(grouped[identity].pop(0))
    if len(selected) < count:
        raise SimulationError(f"insufficient eligible recorded windows: requested {count}, available {len(selected)}")
    return selected


class WorkerHttp:
    def __init__(self, base_url, token):
        parsed = urllib.parse.urlsplit(base_url)
        local = parsed.hostname in ("127.0.0.1", "localhost", "::1")
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.scheme != "https" and not (parsed.scheme == "http" and local)):
            raise SimulationError("Worker URL must use HTTPS (or loopback HTTP), without credentials/query/fragment")
        self.base = base_url.rstrip("/")
        self._token = token
        self.opener = urllib.request.build_opener(NoRedirect)

    def __call__(self, path, payload, timeout):
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        request = urllib.request.Request(self.base + path, data=body,
            headers={"Authorization": "Bearer " + self._token, "Content-Type": "application/json"},
            method="POST" if body is not None else "GET")
        started = time.monotonic()
        try:
            response = self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise SimulationError("Worker response exceeded the size limit")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise SimulationError("Worker returned an invalid response object")
            return response.status, parsed, (time.monotonic() - started) * 1000


def validate_calls(response, expected_model, maximum):
    calls = response.get("calls")
    if not isinstance(calls, list) or not 1 <= len(calls) <= maximum:
        raise SimulationError("missing or excessive completion receipts")
    total = 0.0
    for call in calls:
        if not isinstance(call, dict) or call.get("model") != expected_model:
            raise SimulationError("unexpected model in completion receipts")
        usage, pricing = call.get("usage"), call.get("pricing")
        if not isinstance(usage, dict) or not isinstance(pricing, dict):
            raise SimulationError("missing usage or per-call pricing; actual cost unknown")
        if any(not isinstance(usage.get(k), int) or isinstance(usage[k], bool) or usage[k] < 0 for k in ("prompt_tokens", "completion_tokens")):
            raise SimulationError("invalid completion usage; actual cost unknown")
        limit = 400 if expected_model == LIGHTNING else 1200
        if usage["prompt_tokens"] > 32768 or usage["completion_tokens"] > limit:
            raise SimulationError("completion exceeded the reserved token envelope")
        rates = [pricing.get(k) for k in ("input_price_per_million_tokens", "output_price_per_million_tokens")]
        values = rates + [call.get("cost_usd"), call.get("latency_ms")]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
            raise SimulationError("invalid cost, latency, or per-call pricing")
        expected = (usage["prompt_tokens"] * rates[0] + usage["completion_tokens"] * rates[1]) / 1_000_000
        if not math.isclose(expected, call["cost_usd"], rel_tol=1e-9, abs_tol=1e-12):
            raise SimulationError("receipt cost does not match usage and per-call pricing")
        total += expected
    aggregate = response.get("cost_usd")
    if not isinstance(aggregate, (int, float)) or isinstance(aggregate, bool) or not math.isclose(aggregate, total, rel_tol=1e-9, abs_tol=1e-12):
        raise SimulationError("aggregate cost does not match completion receipts")
    return calls, total


class Session:
    def __init__(self, transport, token, prices, plan, output, cap=3.0, max_seconds=600, test_transport=False):
        self.transport, self._token, self.prices, self.plan = transport, token, prices, plan
        self.output, self.cap = Path(output), cap
        self.deadline = time.monotonic() + max_seconds
        self.reserved = self.actual = 0.0
        self.reserved_calls = 0
        self.unknown_cost = False
        self.document = {"schema":"last-sentence/matrix-v1", "mode":"model-backed-timing-simulation",
            "evidence_kind":"model-backed-timing-simulation", "status":"running", "cost_plan":plan,
            "rows":[], "language_pair":[], "attempts":[], "failures":[], "measured_tts_runs":0,
            "max_execution_seconds":max_seconds,
            "execution_transport":"injected-test-transport" if test_transport else "protected-worker-http",
            "notice":"Model-generated text on recorded receipt-time arrival traces. Speech duration is simulated from fixed Unicode characters/second plus measured HTTP latency. No browser TTS, door-open, or real-world narration accuracy is measured."}

    def redact(self, value):
        if isinstance(value, str):
            return value.replace(self._token, "[redacted]")
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, dict):
            return {k:self.redact(v) for k,v in value.items()}
        return value

    def save(self):
        receipt_groups = [attempt.get("response", {}).get("calls") for attempt in self.document["attempts"]]
        self.document.update(actual_api_cost_usd=None if self.unknown_cost else self.actual,
            known_usage_cost_usd=self.actual, reserved_upper_bound_usd=self.reserved,
            reserved_completion_bound=self.reserved_calls, coverage=policy_coverage(self.document["rows"]),
            completed_simulation_runs=len(self.document["rows"]) + len(self.document["language_pair"]),
            inference_dispatch_attempts=len(self.document["attempts"]),
            model_completion_attempts=sum(len(group) for group in receipt_groups if isinstance(group, list)),
            completion_attempt_count_known=all(isinstance(group, list) for group in receipt_groups))
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output.with_suffix(self.output.suffix + ".tmp")
        temporary.write_text(json.dumps(self.redact(self.document), ensure_ascii=False, indent=2) + "\n")
        temporary.replace(self.output)

    def http(self, path, payload=None):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise SimulationError("simulation execution deadline exhausted")
        return self.transport(path, payload, min(30, remaining))

    def status(self, minimum_calls, minimum_usd):
        code, result, elapsed = self.http("/api/status")
        limits = result.get("limits", {})
        if code != 200 or result.get("inference_enabled") is not True:
            raise SimulationError("protected Worker is not inference-ready")
        available = limits.get("reservation_budget_usd")
        reserved = limits.get("reserved_usd")
        remaining = limits.get("completion_calls_remaining")
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in (available, reserved, remaining)):
            raise SimulationError("authorized Worker budget state is unavailable")
        if not 0 <= reserved <= available <= self.cap or available - reserved + 1e-12 < minimum_usd or remaining < minimum_calls:
            raise SimulationError("Worker budget or remaining completion capacity is insufficient")
        return elapsed

    def request(self, path, payload, model, maximum):
        input_rate, output_rate = self.prices[model]
        output_tokens = 400 if model == LIGHTNING else 1200
        upper = maximum * (32768 * input_rate + output_tokens * output_rate) / 1_000_000
        if self.reserved + upper > self.cap or self.reserved_calls + maximum > self.plan["configured_completion_cap"]:
            raise SimulationError("local predispatch budget/call reservation refused")
        if len(json.dumps(payload, ensure_ascii=False).encode()) > 24000:
            raise SimulationError("request exceeds the protected Worker input limit")
        status_elapsed = self.status(maximum, upper)
        self.reserved += upper
        self.reserved_calls += maximum
        attempt = {"path":path, "input":payload, "state":"dispatched", "reserved_usd":upper,
                   "maximum_completions":maximum}
        self.document["attempts"].append(attempt)
        # Preserve a pending attempt if the process is interrupted after dispatch.
        self.unknown_cost = True
        self.save()
        try:
            code, result, elapsed = self.http(path, payload)
            attempt.update(http_status=code, response=result, http_elapsed_ms=elapsed, status_elapsed_ms=status_elapsed)
            calls, cost = validate_calls(result, model, maximum)
            self.actual += cost
            self.unknown_cost = False
            attempt["state"] = "recorded" if code == 200 else "failed-with-receipts"
            if self.actual > self.cap:
                raise SimulationError("actual receipt costs exceeded the local cap; abort")
            if cost > upper + 1e-12 or any((call["pricing"]["input_price_per_million_tokens"], call["pricing"]["output_price_per_million_tokens"]) != self.prices[model] for call in calls):
                raise SimulationError("Worker pricing differs from the acknowledged snapshot; abort before further dispatch")
            if code != 200 or result.get("error"):
                raise SimulationError("Worker request failed; attempt and receipts retained")
            return result, (status_elapsed + elapsed) / 1000
        except Exception as exc:
            attempt["state"] = "failed"
            attempt["failure"] = type(exc).__name__ + ": " + str(exc) if isinstance(exc, SimulationError) else type(exc).__name__
            raise SimulationError(attempt["failure"]) from exc
        finally:
            self.save()


def schedule(sentences, start, cps):
    result = []
    for sentence in sentences:
        end = start + len(sentence) / cps
        result.append({"start":start,"end":end,"text":sentence})
        start = end
    return result


def simulate_story(session, window, policy, lang="en", cps=4.51):
    events = window["events"]
    origin = events[0]["t"]
    route = [event["station"] for event in events]
    model = ULTRA if lang == "ko" else SUPER
    elapsed = 0.0
    timeline = []
    receipts, forecast_log, decisions = [], [], []
    writer_calls = conductor_requests = 0
    initial_forecast = predict(window["model"], window["line"], route)["remaining_s"]

    def remaining(index, at):
        forecast = predict(window["model"], window["line"], route[index:])["remaining_s"]
        value = max(0, forecast - max(0, at - (events[index]["t"] - origin)))
        forecast_log.append({"station":route[index],"observed_at_s":events[index]["t"]-origin,
                             "controller_clock_s":at,"remaining_s":value,"eta_source":"operator-estimate",
                             "offline_provenance":"whole-train-held-out receipt-time ETA; not a server-verified live anchor"})
        return value

    def writer(remaining_s, at):
        nonlocal writer_calls
        count = min(4000, budget(remaining_s, cps))
        if count < len(route[-1]):
            raise SimulationError("remaining character budget cannot fit the station alert")
        body = {"lang":lang,"exit_station":route[-1],"budget_chars":count,"is_last_scene":True,
                "scene":f"Continue a complete quiet Seoul train mystery. Use close to the {count}-character allowance, one sentence per line. Finish with the exit alert. Offline timing simulation; no source fact is supplied."}
        response, delay = session.request("/api/write", body, model, 1)
        receipts.append(response)
        try:
            validate_write(response, lang, route[-1])
        except ValueError as exc:
            raise SimulationError("Writer contract rejected: " + str(exc)) from exc
        writer_calls += 1
        return response["sentences"], at + delay

    if policy == "sentence_replan":
        r = remaining(0, elapsed)
        response, delay = session.request("/api/plan", {"current_station":route[0],"exit_station":route[-1],
            "stations_left":len(route)-1,"remaining_s":r,"elapsed_story_s":0,"eta_source":"operator-estimate",
            "remaining_scenes":[],"offline_provenance":"whole-train-held-out recorded receipt-time ETA"}, LIGHTNING, 3)
        receipts.append(response)
        try:
            validate_plan(response.get("plan"))
        except ValueError as exc:
            raise SimulationError("Conductor contract rejected: " + str(exc)) from exc
        conductor_requests += 1
        elapsed += delay
    sentences, elapsed = writer(max(0, initial_forecast - elapsed), elapsed)
    timeline = schedule(sentences, elapsed, cps)
    midpoint = max(1, (len(route)-1)//2)
    for index in range(1, len(events)-1):
        if policy == "fixed_clip":
            break
        event_time = events[index]["t"] - origin
        elapsed = max(elapsed, event_time)
        if timeline[-1]["end"] <= elapsed:
            decisions.append({"station":route[index],"action":"story-already-ended"})
            break
        should_write = policy == "single_fit" and index == midpoint
        r = remaining(index, elapsed)
        forecast_clock = elapsed
        if policy == "sentence_replan":
            response, delay = session.request("/api/plan", {"current_station":route[index],"exit_station":route[-1],
                "stations_left":len(route)-1-index,"remaining_s":r,"elapsed_story_s":min(7200,elapsed),
                "eta_source":"operator-estimate","remaining_scenes":[{"id":"remaining","chars":sum(len(s['text']) for s in timeline if s['end']>elapsed)}],
                "offline_provenance":"whole-train-held-out recorded receipt-time ETA"}, LIGHTNING, 3)
            receipts.append(response)
            try:
                validate_plan(response.get("plan"))
            except ValueError as exc:
                raise SimulationError("Conductor contract rejected: " + str(exc)) from exc
            conductor_requests += 1
            elapsed += delay
            should_write = bool(response["plan"]["ops"]) and writer_calls < 4
            decisions.append({"station":route[index],"ops":response["plan"]["ops"],"rewrite_permitted":should_write})
        if not should_write:
            continue
        if timeline[-1]["end"] <= elapsed:
            decisions.append({"station":route[index],"action":"plan-arrived-after-story-completion"})
            break
        sentences, ready = writer(max(0, r - (elapsed - forecast_clock)), elapsed)
        elapsed = ready
        if timeline[-1]["end"] <= ready:
            decisions.append({"station":route[index],"action":"rewrite-arrived-after-story-completion"})
            break
        boundary = next(s["end"] for s in timeline if s["end"] >= ready)
        if boundary >= timeline[-1]["end"]:
            decisions.append({"station":route[index],"action":"final-alert-already-speaking"})
            break
        timeline = [s for s in timeline if s["end"] <= boundary] + schedule(sentences, boundary, cps)
    # Held-out final timestamp is read only here, for scoring after control.
    actual_arrival = events[-1]["t"] - origin
    calls = [call for response in receipts for call in response["calls"]]
    latencies = sorted(call["latency_ms"] for call in calls)
    return {"id":window["id"],"line":window["line"],"trainNo":window["trainNo"],"policy":policy,"lang":lang,
        "exit_station":route[-1],"evidence_kind":"model-backed-timing-simulation","landing_error_s":timeline[-1]["end"]-actual_arrival,
        "story_end_s":timeline[-1]["end"],"arrival_proxy_s":actual_arrival,"initial_forecast_s":initial_forecast,
        "speech_clock":"fixed-unicode-character-rate-plus-measured-http-latency","speech_rate_cps":cps,
        "conductor_calls":sum(call["model"]==LIGHTNING for call in calls),"conductor_requests":conductor_requests,
        "writer_calls":writer_calls,"tokens":sum(call["usage"]["prompt_tokens"]+call["usage"]["completion_tokens"] for call in calls),
        "cost_usd":sum(call["cost_usd"] for call in calls),"p50_latency_ms":statistics.median(latencies),
        "p95_latency_ms":latencies[math.ceil(len(latencies)*.95)-1],"tool_calls_supported":all(response.get("tool_calls_supported") is True for response in receipts if "plan" in response) if conductor_requests else None,
        "tavily_ok":None,"fact_mode":"station-only-no-search-requested","arrival_event":"station-arrival-proxy",
        "forecast_log":forecast_log,"controller_decisions":decisions,"receipts":receipts,"simulated_sentences":timeline}


def execute(trace, catalog, output, worker_url, key_file, journeys=30, cap=3.0, max_completions=300,
            execute_flag=False, ack_cost=None, segments=4, cps=4.51, transport=None):
    if (not execute_flag or not isinstance(ack_cost, (int, float)) or isinstance(ack_cost, bool)
            or not math.isfinite(ack_cost) or ack_cost < cap):
        raise SimulationError("execution requires --execute and --ack-cost acknowledging the full configured cap")
    if not isinstance(cps, (int, float)) or not math.isfinite(cps) or cps <= 0:
        raise SimulationError("speech rate must be finite and positive")
    prices = prices_from_catalog(catalog)
    plan = cost_plan(prices, journeys, cap, max_completions=max_completions)
    if not plan["allowed"]:
        raise SimulationError("precomputed matrix exceeds dollar or completion cap; no requests sent")
    snapshot = json.loads(Path(catalog).read_text())
    captured = (snapshot.get("retrieved_at") or snapshot.get("fetched_at")) if isinstance(snapshot, dict) else None
    if not captured or not -60 <= time.time() - timestamp(captured) <= 3600:
        raise SimulationError("a pricing snapshot checked within one hour is required")
    key_file = Path(key_file).expanduser()
    if not key_file.is_file() or key_file.stat().st_mode & 0o077:
        raise SimulationError("Worker session-token file must exist with mode 600")
    token = key_file.read_text().strip()
    if not token:
        raise SimulationError("Worker session-token file is empty")
    if Path(output).exists():
        raise SimulationError("output already exists; choose a fresh run path to avoid accidental repeat spending")
    rows = load_trace(trace)
    windows = select_windows(rows, journeys, segments)
    client = transport if transport is not None else WorkerHttp(worker_url, token)
    session = Session(client, token, prices, plan, output, cap, test_transport=transport is not None)
    session.document.update(trace_sha256=hashlib.sha256(Path(trace).read_bytes()).hexdigest(),
        line_coverage=sorted(set(w["line"] for w in windows)), distinct_train_identities=len(set(w["identity"] for w in windows)),
        selection_notice="Only eligible recorded lines are included. No line-5/7 results exist unless those traces are supplied. Windows may overlap; repeated windows are not independent journeys.",
        eta_training="Other train identities from this offline trace; whole target train identity excluded. This is not forward-in-time online validation.")
    session.save()
    try:
        session.status(plan["max_total_completions"], plan["worst_case_usd"])
        for window in windows:
            for policy in POLICIES:
                session.document["rows"].append(simulate_story(session, window, policy, "en", cps))
                session.save()
        for language in ("en", "ko"):
            session.document["language_pair"].append(simulate_story(session, windows[0], "sentence_replan", language, cps))
            session.save()
        session.document["status"] = "complete"
    except Exception as exc:
        session.document["status"] = "aborted"
        session.document["failures"].append({"type":type(exc).__name__,"reason":str(exc) if isinstance(exc, SimulationError) else type(exc).__name__})
    finally:
        session.save()
    return session.redact(session.document)
