"""Guarded model-backed timing simulation over held-out recorded train windows.

No browser/audio measurement occurs here. Calls are possible only through an
explicitly enabled, protected Worker after local and server budget checks.
"""
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from contracts import RECEIPT_SCHEMA, validate_model_identity, validate_plan, validate_write, validate_writer_validation
from eta_model import arrivals, budget, fit, load_trace, predict, timestamp
from scene_ops import partition, editable_inputs, prepare as prepare_scene_op, apply as apply_scene_patch
from rate_pacing import MinutePacer, PacingError
from run_matrix import LIGHTNING, SUPER, ULTRA, POLICIES, MAX_INPUT_TOKENS, cost_plan, policy_coverage, prices_from_catalog


class SimulationError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Session credentials belong only to the configured Worker origin.
        return None


def fetch_current_prices():
    """Public read-only revalidation, with system CA verification through curl."""
    url='https://tokenfactory.nebius.com/api/public/models_info'
    try:
        result=subprocess.run(['curl','--max-time','20','-fsS',url],capture_output=True,timeout=25)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise SimulationError('public model-price revalidation failed before dispatch: '+type(exc).__name__) from exc
    if result.returncode!=0:
        raise SimulationError('public model-price revalidation failed before dispatch')
    try:
        catalog=json.loads(result.stdout)
        rates={}
        for model in (LIGHTNING,SUPER,ULTRA):
            entry=next(flavor for item in catalog for flavor in item.get('flavors',[]) if flavor.get('model_id')==model)
            pair=tuple(entry[key] for key in ('input_price_per_million_tokens','output_price_per_million_tokens'))
            if any(not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<0 for value in pair):
                raise ValueError('invalid rate')
            rates[model]=pair
    except (ValueError,TypeError,KeyError,StopIteration) as exc:
        raise SimulationError('public model-price revalidation lacks verified required models/rates') from exc
    return rates,{'source_url':url,'catalog_sha256':hashlib.sha256(result.stdout).hexdigest()}


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
    by_line = {}
    for identity, windows in grouped.items():
        by_line.setdefault(windows[0]["line"],{})[identity]=windows
    targets = {line:10 for line in ("2호선","5호선","7호선")} if count==30 else None
    if targets:
        availability = {line:sum(len(w) for w in by_line.get(line,{}).values()) for line in targets}
        if any(availability[line]<target for line,target in targets.items()):
            raise SimulationError("full matrix requires 10 eligible recorded windows per line (2/5/7); availability="+json.dumps(availability,ensure_ascii=False))
    selected, counts = [], {}
    cursors = {line:0 for line in by_line}
    # Balance lines first, then rotate train identities before reusing windows.
    while len(selected)<count and any(any(windows for windows in trains.values()) for trains in by_line.values()):
        progress = False
        for line in sorted(by_line):
            if len(selected)>=count or (targets and counts.get(line,0)>=targets[line]):
                continue
            identities = sorted(by_line[line])
            for _ in identities:
                index=cursors[line]%len(identities);cursors[line]+=1
                identity=identities[index]
                if by_line[line][identity]:
                    selected.append(by_line[line][identity].pop(0));counts[line]=counts.get(line,0)+1
                    progress=True
                    break
        if not progress:
            break
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
    try:
        validate_model_identity(response, (LIGHTNING, SUPER, ULTRA), expected_model)
    except ValueError as exc:
        raise SimulationError(str(exc)) from exc
    total = 0.0
    for call in calls:
        try:
            validate_model_identity(call, (LIGHTNING, SUPER, ULTRA), expected_model)
        except ValueError as exc:
            raise SimulationError(str(exc)) from exc
        usage, pricing = call.get("usage"), call.get("pricing")
        if not isinstance(usage, dict) or not isinstance(pricing, dict):
            raise SimulationError("missing usage or per-call pricing; actual cost unknown")
        if pricing.get('fresh_for_dispatch') is not True or pricing.get('acknowledged') is not True:
            raise SimulationError('receipt lacks fresh acknowledged-price enforcement')
        if any(not isinstance(usage.get(k), int) or isinstance(usage[k], bool) or usage[k] < 0 for k in ("prompt_tokens", "completion_tokens")):
            raise SimulationError("invalid completion usage; actual cost unknown")
        limit = 400 if expected_model == LIGHTNING else 1200
        if usage["prompt_tokens"] > MAX_INPUT_TOKENS or usage["completion_tokens"] > limit:
            raise SimulationError("completion exceeded the reserved token envelope")
        rates = [pricing.get(k) for k in ("input_price_per_million_tokens", "output_price_per_million_tokens")]
        values = rates + [call.get("cost_usd"), call.get("latency_ms")]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
            raise SimulationError("invalid cost, latency, or per-call pricing")
        expected = (usage["prompt_tokens"] * rates[0] + usage["completion_tokens"] * rates[1]) / 1_000_000
        if not math.isclose(expected, call["cost_usd"], rel_tol=1e-9, abs_tol=1e-12):
            raise SimulationError("receipt cost does not match usage and per-call pricing")
        estimate = call.get("requested_rate_cost_estimate_usd")
        if (not isinstance(estimate, (int, float)) or isinstance(estimate, bool)
                or not math.isfinite(estimate) or estimate < 0 or not math.isclose(estimate, expected, rel_tol=1e-9, abs_tol=1e-12)):
            raise SimulationError("requested-rate cost estimate does not match verified usage/pricing")
        total += expected
    aggregate = response.get("cost_usd")
    if not isinstance(aggregate, (int, float)) or isinstance(aggregate, bool) or not math.isclose(aggregate, total, rel_tol=1e-9, abs_tol=1e-12):
        raise SimulationError("aggregate cost does not match completion receipts")
    aggregate_estimate = response.get("requested_rate_cost_estimate_usd")
    if (not isinstance(aggregate_estimate, (int, float)) or isinstance(aggregate_estimate, bool)
            or not math.isfinite(aggregate_estimate) or aggregate_estimate < 0 or not math.isclose(aggregate_estimate, total, rel_tol=1e-9, abs_tol=1e-12)):
        raise SimulationError("aggregate requested-rate estimate does not match completion receipts")
    return calls, total


class Session:
    def __init__(self, transport, token, prices, plan, output, cap=3.0, max_seconds=7200, test_transport=False,
                 clock=time.monotonic,sleep=time.sleep,wall_clock=time.time,price_checked_at=None,price_refresher=fetch_current_prices):
        self.transport, self._token, self.prices, self.plan = transport, token, prices, plan
        self.output, self.cap = Path(output), cap
        self.clock,self.wall_clock=clock,wall_clock
        self.deadline = self.clock() + max_seconds
        self.pacer=MinutePacer(clock,sleep)
        self.price_checked_at=wall_clock() if price_checked_at is None else price_checked_at
        self.price_refresher=price_refresher
        self.reserved = self.actual = 0.0
        self.reserved_calls = 0
        self.unknown_cost = False
        self.document = {"schema":"last-sentence/matrix-v1", "mode":"model-backed-timing-simulation",
            "evidence_kind":"model-backed-timing-simulation", "status":"running", "cost_plan":plan,
            "rows":[], "language_pair":[], "attempts":[], "failures":[], "measured_tts_runs":0,
            "max_execution_seconds":max_seconds,
            "pacing":{"rpm":45,"tpm":300000,"reservation":"worst-case completion groups and input+output token envelope",
                      "wait_s":0,"excluded_from_simulated_speech_clock":True,
                      "assumption":"No competing account traffic; provider limits may differ. Dispatched failures are never retried automatically."},
            "price_revalidations":[],
            "execution_transport":"injected-test-transport" if test_transport else "protected-worker-http",
            "notice":"Model-generated text on recorded receipt-time arrival traces. Speech duration is simulated from fixed Unicode characters/second plus measured HTTP latency. Offline 45RPM/300000TPM pacing and public-price audit waits count in real runtime but are excluded from the simulated speech clock; this assumes no competing account traffic. No browser TTS, door-open, or real-world narration accuracy is measured."}

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
        temporary.write_text(json.dumps(self.redact(self.document), ensure_ascii=True, indent=2) + "\n")
        temporary.replace(self.output)

    def http(self, path, payload=None):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise SimulationError("simulation execution deadline exhausted")
        route_timeout=90 if path=='/api/plan' else 45 if path=='/api/write' else 25
        return self.transport(path, payload, min(route_timeout, remaining))

    def revalidate_prices(self):
        if self.wall_clock()-self.price_checked_at<=3600:
            return
        if self.deadline-self.clock()<25:
            raise SimulationError('not enough remaining runtime for public-price revalidation; no dispatch')
        rates,metadata=self.price_refresher()
        event={**metadata,'checked_at_epoch_s':self.wall_clock(),'rates_unchanged':rates==self.prices,
               'excluded_from_simulated_speech_clock':True}
        self.document['price_revalidations'].append(event)
        self.save()
        if rates!=self.prices:
            raise SimulationError('public catalog rates changed; acknowledged bound retained, no further dispatch')
        self.price_checked_at=self.wall_clock()

    def status(self, minimum_calls, minimum_usd):
        code, result, elapsed = self.http("/api/status")
        limits = result.get("limits", {})
        if code != 200 or result.get("inference_enabled") is not True:
            raise SimulationError("protected Worker is not inference-ready")
        if result.get('receipt_schema') != RECEIPT_SCHEMA:
            raise SimulationError('Worker does not advertise the required receipt-v2 schema')
        if result.get("max_input_token_bound") != self.plan["max_input_tokens_per_completion"]:
            raise SimulationError("Worker input-token envelope does not match the acknowledged cost plan")
        if result.get('expected_pricing_supported') is not True:
            raise SimulationError('Worker does not advertise predispatch acknowledged-price enforcement')
        if result.get('receipt_provenance_supported') is not True or result.get('writer_validation_supported') is not True:
            raise SimulationError('Worker does not advertise verified model provenance and Writer validation receipts')
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
        payload={**payload,'expected_pricing':{'model':model,'input_price_per_million_tokens':input_rate,'output_price_per_million_tokens':output_rate}}
        output_tokens = 400 if model == LIGHTNING else 1200
        upper = maximum * (MAX_INPUT_TOKENS * input_rate + output_tokens * output_rate) / 1_000_000
        if self.reserved + upper > self.cap or self.reserved_calls + maximum > self.plan["configured_completion_cap"]:
            raise SimulationError("local predispatch budget/call reservation refused")
        if len(json.dumps(payload, ensure_ascii=False).encode()) > 24000:
            raise SimulationError("request exceeds the protected Worker input limit")
        try:
            pacing_wait=self.pacer.reserve(maximum,maximum*(MAX_INPUT_TOKENS+output_tokens),self.deadline)
        except PacingError as exc:
            raise SimulationError(str(exc)) from exc
        self.document['pacing']['wait_s']+=pacing_wait
        self.revalidate_prices()
        status_elapsed = self.status(maximum, upper)
        self.reserved += upper
        self.reserved_calls += maximum
        attempt = {"path":path, "input":payload, "state":"dispatched", "reserved_usd":upper,
                   "maximum_completions":maximum,'offline_pacing_wait_s':pacing_wait,
                   'pacing_excluded_from_simulated_speech_clock':True}
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
            if path == '/api/write':
                for call in calls:
                    try:
                        validate_writer_validation(call.get('writer_validation'), expected_language=payload['lang'],
                            expected_budget=payload['budget_chars'], expected_ending=payload['is_last_scene'],
                            sentences=result.get('sentences') if code == 200 and not result.get('error') else None,
                            require_passed=code == 200 and not result.get('error'), expected_station=payload['exit_station'])
                    except ValueError as exc:
                        raise SimulationError(str(exc)) from exc
            if code != 200 or result.get("error"):
                raise SimulationError("Worker request failed; attempt and receipts retained")
            return result, (status_elapsed + elapsed) / 1000
        except Exception as exc:
            attempt["state"] = "failed"
            attempt["failure"] = type(exc).__name__ + ": " + str(exc) if isinstance(exc, SimulationError) else type(exc).__name__
            raise SimulationError(attempt["failure"]) from exc
        finally:
            self.save()


def schedule(sentences, start, cps, scene_id="remaining", kind="body"):
    result = []
    for sentence in sentences:
        end = start + len(sentence) / cps
        result.append({"start":start,"end":end,"text":sentence,"scene_id":scene_id,"kind":kind})
        start = end
    return result


def scene_schedule(scenes,start,cps):
    result=[]
    for scene in scenes:
        frames=schedule(scene["sentences"],start,cps,scene["id"],scene["kind"])
        result.extend(frames)
        if frames:start=frames[-1]["end"]
    return result


def sentence_boundary(timeline,at):
    if at<=timeline[0]["start"]:return timeline[0]["start"]
    return next((frame["end"] for frame in timeline if frame["end"]>=at),timeline[-1]["end"])


def reschedule_scene_patch(timeline,scenes,boundary,cps):
    history=[frame for frame in timeline if frame["end"]<=boundary+1e-9]
    read_count=len(history)
    future=scene_schedule(scenes,0,cps)[read_count:]
    start=boundary
    for frame in future:
        frame["start"]=start;frame["end"]=start+len(frame["text"])/cps;start=frame["end"]
    return history+future


def simulate_story(session, window, policy, lang="en", cps=4.51):
    events = window["events"]
    origin = events[0]["t"]
    route = [event["station"] for event in events]
    model = ULTRA if lang == "ko" else SUPER
    elapsed = 0.0
    timeline = [];scenes=[]
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

    def writer(count, at, is_last_scene=True, prompt=None):
        nonlocal writer_calls
        if count < (len(route[-1]) if is_last_scene else 1):
            raise SimulationError("remaining character budget cannot fit the station alert")
        if writer_calls >= (4 if policy=="sentence_replan" else 2 if policy=="single_fit" else 1):
            raise SimulationError("Writer attempt allowance exhausted")
        body = {"lang":lang,"exit_station":route[-1],"budget_chars":count,"is_last_scene":True,
                "scene":prompt or f"Continue a complete quiet Seoul train mystery. Use close to the {count}-character allowance, one sentence per line. Finish with the exit alert. Offline timing simulation; no source fact is supplied."}
        body["is_last_scene"]=is_last_scene
        writer_calls += 1  # Attempts consume the allowance, including failures.
        response, delay = session.request("/api/write", body, model, 1)
        receipts.append(response)
        try:
            validate_write(response, lang, route[-1] if is_last_scene else None)
        except ValueError as exc:
            raise SimulationError("Writer contract rejected: " + str(exc)) from exc
        if sum(len(text) for text in response["sentences"])>count:
            raise SimulationError("Writer exceeded affected scene character budget")
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
    sentences, elapsed = writer(min(4000,budget(max(0,initial_forecast-elapsed),cps)), elapsed)
    scenes=partition(sentences)
    timeline = scene_schedule(scenes,elapsed,cps)
    midpoint = max(1, (len(route)-1)//2)
    for index in range(1, len(events)-1):
        if policy == "fixed_clip":
            break
        event_time = events[index]["t"] - origin
        elapsed = max(elapsed, event_time)
        if timeline[-1]["end"] <= elapsed:
            decisions.append({"station":route[index],"action":"story-already-ended"})
            break
        if timeline[-1]["start"] <= elapsed:
            decisions.append({"station":route[index],"action":"exit-cue-already-started-no-more-model-rounds"})
            break
        should_write = policy == "single_fit" and index == midpoint
        r = remaining(index, elapsed)
        forecast_clock = elapsed
        if policy == "sentence_replan":
            read_count=sum(frame["start"]<=elapsed for frame in timeline)
            response, delay = session.request("/api/plan", {"current_station":route[index],"exit_station":route[-1],
                "stations_left":len(route)-1-index,"remaining_s":r,"elapsed_story_s":min(7200,elapsed),
                "eta_source":"operator-estimate","remaining_scenes":editable_inputs(scenes,read_count),
                "offline_provenance":"whole-train-held-out recorded receipt-time ETA"}, LIGHTNING, 3)
            receipts.append(response)
            try:
                validate_plan(response.get("plan"))
            except ValueError as exc:
                raise SimulationError("Conductor contract rejected: " + str(exc)) from exc
            conductor_requests += 1
            elapsed += delay
            seen=set()
            for op in response["plan"]["ops"]:
                if timeline[-1]["end"]<=elapsed:break
                if op["scene"] in seen:
                    decisions.append({"station":route[index],"scene":op["scene"],"action":"duplicate-op-skipped"});continue
                read_count=sum(frame["start"]<=elapsed for frame in timeline)
                global_budget=min(4000,budget(max(0,r-(elapsed-forecast_clock)),cps))
                descriptor=prepare_scene_op(scenes,read_count,op,global_budget)
                if not descriptor["allowed"]:
                    decisions.append({"station":route[index],"scene":op["scene"],"op":op["op"],"action":"skipped","reason":descriptor["reason"]});continue
                if op["op"]!="drop" and writer_calls>=4:
                    decisions.append({"station":route[index],"scene":op["scene"],"op":op["op"],"action":"skipped","reason":"four Writer attempts already used"});continue
                seen.add(op["scene"])
                patch=dict(descriptor)
                if op["op"]!="drop":
                    if descriptor["kind"]=="exit" and descriptor["budget_chars"]<len(route[-1]):
                        decisions.append({"scene":op["scene"],"action":"skipped","reason":"scene budget cannot fit the station alert"});continue
                    existing=" ".join(descriptor.get("existing",[]))[:250]
                    prompt=(f"{op['op']} only named scene {op['scene']}. Keep its role in the quiet train mystery. "
                            f"Existing scene: {existing}. "+("Finish with one exit alert." if descriptor["kind"]=="exit" else "Write a body scene, no exit alert."))[:500]
                    replacement,elapsed=writer(descriptor["budget_chars"],elapsed,descriptor["kind"]=="exit",prompt)
                    if descriptor["kind"]=="exit" and len(replacement)!=1:
                        raise SimulationError("exit scene replacement must contain exactly one sentence; receipt and attempt retained")
                    patch["sentences"]=replacement
                if timeline[-1]["end"]<=elapsed:
                    decisions.append({"scene":op["scene"],"action":"skipped","reason":"story completed before patch arrived"});break
                boundary=sentence_boundary(timeline,elapsed)
                boundary_read=sum(frame["end"]<=boundary+1e-9 for frame in timeline)
                installation_budget=min(4000,budget(max(0,r-(boundary-forecast_clock)),cps))
                next_scenes,reason=apply_scene_patch(scenes,boundary_read,patch,installation_budget)
                if reason:
                    decisions.append({"station":route[index],"scene":op["scene"],"op":op["op"],"action":"skipped","reason":reason});continue
                scenes=next_scenes
                timeline=reschedule_scene_patch(timeline,scenes,boundary,cps)
                elapsed=boundary
                decisions.append({"station":route[index],"scene":op["scene"],"op":op["op"],"action":"applied","writer_request":op["op"]!="drop","untouched_scenes_retained":True})
            continue
        if not should_write:
            continue
        if timeline[-1]["end"] <= elapsed:
            decisions.append({"station":route[index],"action":"plan-arrived-after-story-completion"})
            break
        sentences, ready = writer(min(4000,budget(max(0,r-(elapsed-forecast_clock)),cps)),elapsed)
        elapsed = ready
        if timeline[-1]["end"] <= ready:
            decisions.append({"station":route[index],"action":"rewrite-arrived-after-story-completion"})
            break
        boundary = next(s["end"] for s in timeline if s["end"] >= ready)
        if boundary >= timeline[-1]["end"]:
            decisions.append({"station":route[index],"action":"final-alert-already-speaking"})
            break
        history=[s for s in timeline if s["end"]<=boundary]
        scenes=[{"id":"spoken-prefix","kind":"body","sentences":[frame["text"] for frame in history]}]+partition(sentences)
        timeline = history+scene_schedule(partition(sentences),boundary,cps)
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
        "forecast_log":forecast_log,"controller_decisions":decisions,"receipts":receipts,"simulated_sentences":timeline,
        "final_scene_state":scenes,"scene_contract":"named scene-1/scene-2/exit; only wholly unstarted scenes editable; drop local, affected-scene insert/compress; four Writer attempts including initial"}


def execute(trace, catalog, output, worker_url, key_file, journeys=30, cap=3.0, max_completions=300,
            execute_flag=False, ack_cost=None, segments=4, cps=4.51, transport=None,max_runtime_s=7200,
            clock=time.monotonic,sleep=time.sleep,wall_clock=time.time,price_refresher=fetch_current_prices):
    if (not execute_flag or not isinstance(ack_cost, (int, float)) or isinstance(ack_cost, bool)
            or not math.isfinite(ack_cost) or ack_cost < cap):
        raise SimulationError("execution requires --execute and --ack-cost acknowledging the full configured cap")
    if not isinstance(cps, (int, float)) or not math.isfinite(cps) or cps <= 0:
        raise SimulationError("speech rate must be finite and positive")
    if not isinstance(max_runtime_s,(int,float)) or isinstance(max_runtime_s,bool) or not math.isfinite(max_runtime_s) or not 0<max_runtime_s<=7200:
        raise SimulationError('max_runtime_s must be positive and no greater than 7200')
    prices = prices_from_catalog(catalog)
    plan = cost_plan(prices, journeys, cap, max_completions=max_completions)
    if not plan["allowed"]:
        raise SimulationError("precomputed matrix exceeds dollar or completion cap; no requests sent")
    snapshot = json.loads(Path(catalog).read_text())
    captured = (snapshot.get("retrieved_at") or snapshot.get("fetched_at")) if isinstance(snapshot, dict) else None
    if not captured or not -60 <= wall_clock() - timestamp(captured) <= 3600:
        raise SimulationError("a pricing snapshot checked within one hour is required")
    key_file = Path(key_file).expanduser()
    if not key_file.is_file() or key_file.stat().st_mode & 0o077:
        raise SimulationError("Worker session-token file must exist with mode 600")
    token = key_file.read_text().strip()
    if not token:
        raise SimulationError("Worker session-token file is empty")
    if Path(output).exists():
        raise SimulationError("output already exists; choose a fresh run path to avoid accidental repeat spending")
    if journeys==30:
        metadata_path=Path(trace).with_suffix('.meta.json')
        metadata=json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        if metadata.get('complete') is not True:
            raise SimulationError("full matrix requires completed per-line recordings; no inference requests sent")
    rows = load_trace(trace)
    windows = select_windows(rows, journeys, segments)
    client = transport if transport is not None else WorkerHttp(worker_url, token)
    session = Session(client, token, prices, plan, output, cap,max_runtime_s,test_transport=transport is not None,
        clock=clock,sleep=sleep,wall_clock=wall_clock,price_checked_at=timestamp(captured),price_refresher=price_refresher)
    session.document.update(trace_sha256=hashlib.sha256(Path(trace).read_bytes()).hexdigest(),
        line_coverage=sorted(set(w["line"] for w in windows)), distinct_train_identities=len(set(w["identity"] for w in windows)),
        windows_per_line={line:sum(window["line"]==line for window in windows) for line in sorted(set(w["line"] for w in windows))},
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
