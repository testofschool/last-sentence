#!/usr/bin/env python3
"""Plan costs, run clearly labeled fixture simulations, or audit real receipts.

Default modes never send inference requests. Explicit model-simulation execution
can call a protected Worker after cost and credential gates; its speech timing
remains simulated. Measured rows require actual browser speech-end events.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from contracts import sentence_replay, validate_model_identity, validate_writer_validation
from eta_model import KST, arrivals, canonical_station, load_trace, timestamp

POLICIES = ("fixed_clip", "single_fit", "sentence_replan")
LIGHTNING = "nvidia/Nemotron-3_5-Lightning"
SUPER = "nvidia/nemotron-3-super-120b-a12b"
ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"
MAX_INPUT_TOKENS = 16384


def policy_coverage(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["id"], set()).add(row["policy"])
    paired = sum(policies == set(POLICIES) for policies in grouped.values())
    total = len(grouped)
    return {"journeys": total, "complete_paired_journeys": paired, "unpaired_journeys": total - paired,
            "rows_by_policy": {p: sum(row["policy"] == p for row in rows) for p in POLICIES},
            "comparison_basis": "fully-paired" if total and paired == total else "mixed-paired-and-unpaired" if paired else "unpaired-only",
            "pairing_definition": "All three policies for the same frozen journey id; measured import also verifies train, line, exit/arrival and replay origin/direction when present."}


def prices_from_catalog(path):
    items = json.loads(Path(path).read_text())
    if isinstance(items, dict) and isinstance(items.get("models"), dict) and items.get("fetched_at"):
        converted = {"schema":"last-sentence/model-prices-v1", "prices":{}}
        for model in (LIGHTNING, SUPER, ULTRA):
            pair = items["models"].get(model)
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("preflight snapshot missing a required model price")
            converted["prices"][model] = {"input_price_per_million_tokens":pair[0], "output_price_per_million_tokens":pair[1]}
        items = converted
    if isinstance(items, dict) and items.get("schema") == "last-sentence/model-prices-v1":
        prices = {}
        for model in (LIGHTNING, SUPER, ULTRA):
            entry = items.get("prices", {}).get(model)
            if not entry:
                raise ValueError("price snapshot missing a required model")
            pair = (entry["input_price_per_million_tokens"], entry["output_price_per_million_tokens"])
            if any(not isinstance(x, (float, int)) or not math.isfinite(x) or x < 0 for x in pair):
                raise ValueError("invalid model price")
            prices[model] = pair
        return prices
    prices = {}
    for item in items:
        for flavor in item.get("flavors", []):
            if flavor.get("model_id") in (LIGHTNING, SUPER, ULTRA):
                prices[flavor["model_id"]] = (flavor["input_price_per_million_tokens"], flavor["output_price_per_million_tokens"])
    if len(prices) != 3:
        raise ValueError("catalog missing a required model")
    return prices


def cost_plan(prices, journeys=30, cap=3.0, max_input_tokens=MAX_INPUT_TOKENS, stations=12, max_completions=300):
    """Conservative bounded request plan including all Conductor retries.

    A 16,384 input-token envelope is enforced by the Worker and runner. Three
    completions per plan include two tool attempts and one JSON fallback.
    """
    if journeys < 1 or not 0 < cap <= 3 or max_input_tokens < 1 or stations < 1 or not 1 <= max_completions <= 2048:
        raise ValueError("invalid cost-plan limits")
    conductor_calls = journeys * stations * 3
    writer_calls = journeys * (1 + 2 + 4)  # fixed / midpoint / replanned
    pair_conductor_calls = 2 * stations * 3
    pair_super_calls, pair_ultra_calls = 4, 4
    def cost(model, count, output):
        a, b = prices[model]
        return count * (max_input_tokens * a + output * b) / 1_000_000
    total = (cost(LIGHTNING, conductor_calls + pair_conductor_calls, 400)
             + cost(SUPER, writer_calls + pair_super_calls, 1200)
             + cost(ULTRA, pair_ultra_calls, 1200))
    total_completions = conductor_calls + pair_conductor_calls + writer_calls + 8
    return {"journeys": journeys, "policy_runs": journeys * 3, "language_pair_runs": 2,
            "max_input_tokens_per_completion": max_input_tokens, "max_conductor_output_tokens": 400,
            "max_writer_output_tokens": 1200, "max_conductor_calls": conductor_calls + pair_conductor_calls,
            "max_writer_calls": writer_calls + 8, "worst_case_usd": round(total, 8), "cap_usd": cap,
            "max_total_completions": total_completions, "configured_completion_cap": max_completions,
            "required_worker_live_max_completions": total_completions,
            "allowed_cost": total <= cap, "allowed_completions": total_completions <= max_completions,
            "allowed": total <= cap and total_completions <= max_completions, "pricing_source": "saved-live-catalog",
            "runner_enforcement_required": "Reject requests above the input envelope; reserve worst-case cost before each call. Includes all fallback attempts. No calls made by this script."}


def synthetic_matrix(manifest):
    if manifest.get("provenance") != "synthetic-fixture":
        raise ValueError("fixture mode requires explicit synthetic provenance")
    results = []
    for journey in manifest["journeys"]:
        stations = journey["stations"]
        if len(stations) < 4 or any(a["offset_s"] >= b["offset_s"] for a, b in zip(stations, stations[1:])):
            raise ValueError("fixture station times must be strictly increasing")
        arrival = stations[-1]["offset_s"]
        initial_forecast = journey["eta_s"]
        historical_segment_s = initial_forecast / (len(stations) - 1)
        # Controller sees only already-observed station events. Future event
        # timestamps and final arrival are used solely by the scoring function.
        updates = [(s["offset_s"], historical_segment_s * (len(stations) - 1 - i))
                   for i, s in enumerate(stations[1:-1], 1)]
        midpoint = len(updates) // 2
        for policy in POLICIES:
            if policy == "fixed_clip":
                error = initial_forecast - arrival
                calls = 0
            else:
                selected = [updates[midpoint]] if policy == "single_fit" else updates
                simulated = sentence_replay(arrival, initial_forecast, [12] * 35, selected)
                error = simulated["landing_error_s"]
                calls = len(selected)
            results.append({"id": journey["id"], "line": journey["line"], "policy": policy,
                            "landing_error_s": error, "evidence_kind": "synthetic-timing-simulation",
                            "conductor_calls": 0, "writer_calls": 0, "simulated_forecast_updates": calls,
                            "tokens": 0, "cost_usd": 0, "p50_latency_ms": None, "p95_latency_ms": None,
                            "tool_calls_supported": None, "tavily_ok": None,
                            "arrival_event": "station-arrival-proxy",
                            "speech_clock": "mocked-12-second-sentences"})
    return {"schema": "last-sentence/matrix-v1", "mode": "synthetic-timing-simulation",
            "measured_inference_runs": 0, "rows": results, "actual_api_cost_usd": 0, "coverage": policy_coverage(results),
            "notice": "Three authored journey fixtures, not 30 observed journeys. No model, Tavily, or browser speech measurements. Does not establish real-world accuracy."}


def explicit_wall_time(value,label):
    if not isinstance(value,str):
        raise ValueError(label+' must be an explicit timezone-bearing wall-clock timestamp')
    try:
        parsed=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:
        raise ValueError('invalid '+label) from exc
    if parsed.tzinfo is None:
        raise ValueError(label+' must include its timezone')
    return parsed.timestamp()


def replay_clock_mapping(row,mapping,observed_directional,chains,now):
    if not isinstance(mapping,dict) or mapping.get('kind')!='historical-replay-1x':
        raise ValueError('unsupported historical replay clock mapping')
    if mapping.get('source')!='recorded-observations':
        raise ValueError('replay clock source must be recorded observations')
    controller=row.get('controller_provenance')
    if not isinstance(controller,dict) or controller.get('policy')!=row['policy']:
        raise ValueError('historical replay requires matching controller-policy provenance')
    speed=mapping.get('speed')
    if isinstance(speed,bool) or not isinstance(speed,(int,float)) or speed!=1:
        raise ValueError('historical replay measurements require speed=1')
    if mapping.get('uninterrupted') is not True or mapping.get('paused') is not False or mapping.get('seeked') is not False:
        raise ValueError('historical replay measurement was interrupted, paused or seeked')
    direction=str(mapping.get('direction'))
    if direction not in ('0','1'):
        raise ValueError('replay origin requires the recorded train direction')
    station=mapping.get('recorded_origin_station')
    if not isinstance(station,str) or not station.strip():
        raise ValueError('recorded_origin_station must name a raw observed boarding station')
    origin=timestamp(mapping.get('recorded_origin_at'))
    arrival=timestamp(row['arrival_at'])
    playback=explicit_wall_time(mapping.get('playback_origin_at'),'playback_origin_at')
    speech_end=explicit_wall_time(row['speech_end_at'],'speech_end_at')
    if origin>=arrival or origin>now or arrival>now or playback>now or playback>speech_end or speech_end>now:
        raise ValueError('invalid or future replay/recorded origin or speech-end timestamp')
    origin_key=(row['line'],str(row['trainNo']),direction,station,origin)
    arrival_key=(row['line'],str(row['trainNo']),direction,row['exit_station'],arrival)
    if origin_key not in observed_directional or arrival_key not in observed_directional:
        raise ValueError('replay origin/arrival does not match the same raw train, line, direction and station')
    canonical_origin=canonical_station(row['line'],station,True)
    canonical_exit=canonical_station(row['line'],row['exit_station'],True)
    matched=False
    for chain in chains:
        identity=chain[0]['identity'].split('|')
        if identity[0]!=row['line'] or identity[1]!=direction or identity[-1]!=str(row['trainNo']):
            continue
        first=next((i for i,event in enumerate(chain) if event['station']==canonical_origin and event['t']==origin),None)
        last=next((i for i,event in enumerate(chain) if event['station']==canonical_exit and event['t']==arrival),None)
        if first is not None and last is not None and first<last:
            matched=True;break
    if not matched:
        raise ValueError('replay origin and exit do not form one contiguous recorded train window')
    recorded_interval=arrival-origin
    measured_elapsed=speech_end-playback
    retained={**mapping,'recorded_interval_s':recorded_interval,'measured_speech_elapsed_s':measured_elapsed,
        'mapped_arrival_wall_at':dt.datetime.fromtimestamp(playback+recorded_interval,KST).isoformat(),
        'origin_source_validated':True,'contiguous_window_validated':True,
        'notice':'Actual imported browser speech-end elapsed time against a known historical receipt-time replay interval. Does not establish prospective ETA or door-open accuracy.'}
    return measured_elapsed-recorded_interval,retained,('historical-replay-1x',direction,station,origin)


def measured_import(measurements, trace_path, cap=3.0,now=None):
    """Audit externally recorded speech-end/arrival rows and complete receipts.

    A trace hash binds the arrival evidence. Every final arrival must appear as
    trainSttus=1 in the recorded trace. Never infer it from the planned ETA.
    """
    if not 0 < cap <= 3:
        raise ValueError("cap must be in (0, 3]")
    trace_path = Path(trace_path)
    trace_bytes = trace_path.read_bytes()
    trace_hash = hashlib.sha256(trace_bytes).hexdigest()
    if measurements.get("trace_sha256") != trace_hash:
        raise ValueError("measurement trace hash does not match")
    if measurements.get("speech_clock") != "browser-speech-end-event":
        raise ValueError("measured mode requires actual browser speech-end events")
    now=time.time() if now is None else now
    trace_rows=load_trace(trace_path)
    chains,_=arrivals(trace_rows)
    observed = set();observed_directional=set()
    for row in trace_rows:
        if row.get("source") in ("seoul-api", "seoul-sample") and str(row.get("trainSttus")) == "1" and row.get("recptnDt"):
            observed.add((row.get("line"), str(row["trainNo"]), row["statnNm"], timestamp(row["recptnDt"])))
            if str(row.get('updnLine')) in ('0','1'):
                observed_directional.add((row.get('line'),str(row['trainNo']),str(row['updnLine']),row['statnNm'],timestamp(row['recptnDt'])))
    policy_inputs = measurements.get("rows", [])
    pair_inputs = measurements.get("language_pair", [])
    if not isinstance(policy_inputs, list) or not isinstance(pair_inputs, list) or len(pair_inputs) > 2:
        raise ValueError("rows and the optional EN/KO language pair must be lists; at most two language rows")
    out, language_pair = [], []
    costs = []
    seen = set()
    journey_context = {}
    required = ("id", "trainNo", "line", "exit_station", "policy", "arrival_at", "speech_end_at", "receipts")
    pair_languages, pair_context = set(), None
    for is_language_pair, row in [(False, row) for row in policy_inputs] + [(True, row) for row in pair_inputs]:
        if not isinstance(row, dict) or any(key not in row for key in required) or row["policy"] not in POLICIES:
            raise ValueError("invalid measurement row")
        if not isinstance(row["id"], str) or not row["id"].strip():
            raise ValueError("frozen journey id must be a nonempty string")
        language = row.get("lang")
        if language is not None and language not in ("en", "ko"):
            raise ValueError("invalid measurement language")
        if is_language_pair:
            if language not in ("en", "ko") or language in pair_languages:
                raise ValueError("language pair requires distinct explicit en/ko languages")
            pair_languages.add(language)
        identity = (is_language_pair, row["id"], row["policy"], language if is_language_pair else None)
        if identity in seen:
            raise ValueError("duplicate journey/policy measurement")
        seen.add(identity)
        arrival = timestamp(row["arrival_at"])
        context = (row["line"], str(row["trainNo"]), row["exit_station"], arrival)
        if context not in observed:
            raise ValueError("arrival does not match a recorded station-arrival observation")
        if row.get('clock_mapping') is not None:
            landing_error,mapping,mapping_context=replay_clock_mapping(row,row['clock_mapping'],observed_directional,chains,now)
            evidence_kind='historical-replay-browser-speech-vs-arrival-proxy'
        else:
            landing_error=timestamp(row['speech_end_at'])-arrival
            mapping=None;mapping_context=('shared-live-wall-clock',)
            evidence_kind='recorded-browser-speech-end-vs-arrival-proxy'
        context=context+mapping_context
        if row["id"] in journey_context and journey_context[row["id"]] != context:
            raise ValueError("conflicting context for the same frozen journey id")
        journey_context[row["id"]] = context
        if is_language_pair:
            current_pair_context = (row["id"], row["policy"], context)
            if pair_context is not None and pair_context != current_pair_context:
                raise ValueError("EN/KO pair must share one frozen journey, policy and recorded clock context")
            pair_context = current_pair_context
        receipts = row["receipts"]
        if not isinstance(receipts, list) or not receipts:
            raise ValueError("complete inference receipts required")
        latency, tokens, cost = [], 0, 0.0
        calls = []
        for receipt in receipts:
            if not isinstance(receipt, dict):
                raise ValueError("invalid receipt object")
            if receipt.get("mock") or receipt.get("source") == "synthetic-fixture":
                raise ValueError("known real model receipts required")
            nested = receipt.get("calls")
            if nested is not None:
                if not isinstance(nested, list) or not nested:
                    raise ValueError("empty or invalid nested call receipts")
                validate_model_identity(receipt, (LIGHTNING, SUPER, ULTRA))
                for call in nested:
                    validate_model_identity(call, (LIGHTNING, SUPER, ULTRA), receipt["requested_model"])
                if any(not isinstance(call, dict) or not isinstance(call.get("cost_usd"), (int, float)) or isinstance(call["cost_usd"], bool) or not math.isfinite(call["cost_usd"]) or call["cost_usd"] < 0 for call in nested):
                    raise ValueError("invalid nested call cost")
                nested_cost = math.fsum(call.get("cost_usd", float("nan")) for call in nested)
                if not isinstance(receipt.get("cost_usd"), (int, float)) or isinstance(receipt["cost_usd"], bool) or not math.isclose(receipt["cost_usd"], nested_cost, abs_tol=1e-12):
                    raise ValueError("aggregate cost does not match call receipts")
                calls.extend(nested)
            else:
                calls.append(receipt)
        for receipt in calls:
            validate_model_identity(receipt, (LIGHTNING, SUPER, ULTRA))
            usage = receipt.get("usage")
            if not isinstance(usage, dict) or not all(isinstance(usage.get(k), int) and not isinstance(usage[k], bool) and usage[k] >= 0 for k in ("prompt_tokens", "completion_tokens")):
                raise ValueError("missing or invalid token usage")
            c, ms = receipt.get("cost_usd"), receipt.get("latency_ms")
            if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or x < 0 for x in (c, ms)):
                raise ValueError("missing or invalid cost/latency")
            if receipt.get("model") not in (LIGHTNING, SUPER, ULTRA) or receipt.get("mock") or receipt.get("source") == "synthetic-fixture":
                raise ValueError("known real model receipts required")
            pricing = receipt.get("pricing")
            if not isinstance(pricing, dict):
                raise ValueError("per-call pricing required")
            rates = [pricing.get(key) for key in ("input_price_per_million_tokens", "output_price_per_million_tokens")]
            if any(not isinstance(rate, (int, float)) or isinstance(rate, bool) or not math.isfinite(rate) or rate < 0 for rate in rates):
                raise ValueError("invalid per-call pricing")
            expected_cost = (usage["prompt_tokens"] * rates[0] + usage["completion_tokens"] * rates[1]) / 1_000_000
            if not math.isclose(c, expected_cost, rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError("receipt cost does not match token usage and pricing")
            estimate = receipt.get("requested_rate_cost_estimate_usd")
            if (not isinstance(estimate, (int, float)) or isinstance(estimate, bool) or not math.isfinite(estimate)
                    or estimate < 0 or not math.isclose(estimate, expected_cost, rel_tol=1e-9, abs_tol=1e-12)):
                raise ValueError("requested-rate estimate does not match token usage and pricing")
            cost += c
            tokens += usage["prompt_tokens"] + usage["completion_tokens"]
            latency.append(ms)
        costs.append(cost)
        latency.sort()
        writer_calls = [receipt for receipt in calls if receipt["requested_model"] in (SUPER, ULTRA)]
        validations = [validate_writer_validation(receipt.get("writer_validation"), expected_language=language)
                       for receipt in writer_calls]
        if validations and not any(value["passed"] for value in validations):
            raise ValueError("measured story requires at least one accepted Writer output")
        writer_languages = {validation["language"] for validation in validations}
        if len(writer_languages) > 1:
            raise ValueError("one measured story cannot mix Writer languages")
        if language is None and writer_languages:
            language = next(iter(writer_languages))
        requested_writers = sorted({receipt["requested_model"] for receipt in writer_calls})
        reported_writers = sorted({receipt["provider_reported_model"] for receipt in writer_calls})
        if is_language_pair and requested_writers != ([SUPER] if language == "en" else [ULTRA]):
            raise ValueError("EN/KO language pair requires the verified Super English and Ultra Korean Writers")
        destination = language_pair if is_language_pair else out
        destination.append({"id": row["id"], "line": row["line"], "trainNo": str(row["trainNo"]), "lang":language,
                    "exit_station": row["exit_station"], "arrival_at": row["arrival_at"], "policy": row["policy"],
                    "speech_end_at":row['speech_end_at'],"landing_error_s":landing_error,
                    "measurement_clock":mapping_context[0],"clock_mapping":mapping,
                    "controller_provenance":row.get('controller_provenance'),
                    "evidence_kind":evidence_kind,"cost_usd": cost,
                    "tokens": tokens, "conductor_calls": sum(r["model"] == LIGHTNING for r in calls),
                    "writer_calls": sum(r["model"] in (SUPER, ULTRA) for r in calls),
                    "p50_latency_ms": statistics.median(latency), "p95_latency_ms": latency[math.ceil(len(latency) * .95) - 1],
                    "tool_calls_supported": row.get("tool_calls_supported"), "tavily_ok": row.get("tavily_ok"),
                    "writer_models_requested":requested_writers,"writer_models_reported":reported_writers,
                    "model_identities_verified":True,"writer_validations":validations,
                    "arrival_event": "station-arrival-proxy"})
    if not out and not language_pair:
        raise ValueError("no measured rows")
    total = math.fsum(costs)
    if total > cap:
        raise ValueError("recorded receipts exceed the cost cap; comparison not accepted")
    return {"schema": "last-sentence/matrix-v1", "mode": "recorded-browser-measurements",
            "trace_sha256": trace_hash, "rows": out, "language_pair":language_pair,
            "language_pair_status":"complete" if pair_languages == {"en", "ko"} else "partial" if language_pair else "UNRUN",
            "measured_inference_runs": len(out) + len(language_pair),
            "actual_api_cost_usd": total, "cap_usd": cap, "coverage": policy_coverage(out),
            "measurement_clocks":sorted(set(row['measurement_clock'] for row in out + language_pair)),
            "notice": "Imported browser speech-end measurements against station-arrival receipt-time proxies. Historical replay uses an explicit uninterrupted 1× playback-origin mapping; a known-clock audio replay does not establish prospective ETA or door-open accuracy. Receipts provide arithmetic/provenance checks, not semantic model-output validation or provider billing verification."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("plan", "simulation", "measured", "model-simulation"), default="plan")
    p.add_argument("--manifest", type=Path, default=Path("web/replay/manifest.json"))
    p.add_argument("--catalog", type=Path, default=Path("evidence/model-prices.json"))
    p.add_argument("--journeys", type=int, default=30)
    p.add_argument("--cap-usd", type=float, default=3)
    p.add_argument("--max-completions", type=int, default=300)
    p.add_argument("--measurements", type=Path)
    p.add_argument("--trace", type=Path)
    p.add_argument("--out", type=Path, default=Path("evidence/matrix.json"))
    p.add_argument("--execute", action="store_true", help="Explicitly permit protected Worker inference in model-simulation mode")
    p.add_argument("--ack-cost", type=float, help="Acknowledge the entire configured dollar cap before inference")
    p.add_argument("--worker-url")
    p.add_argument("--session-key-file", type=Path)
    p.add_argument("--window-segments", type=int, default=4)
    p.add_argument("--speech-rate-cps", type=float, default=4.51)
    p.add_argument("--max-runtime-s",type=float,default=7200,help="Real experiment runtime including offline pacing, maximum 7200 seconds")
    args = p.parse_args()
    try:
        if args.mode == "plan":
            result = cost_plan(prices_from_catalog(args.catalog), args.journeys, args.cap_usd, max_completions=args.max_completions)
            result["secrets_present"] = {key: ((Path.home() / ("." + key + "_key")).is_file() and (Path.home() / ("." + key + "_key")).stat().st_size > 0) for key in ("nebius", "tavily", "seoul_rt")}
            result["inference_execution"] = "not performed in plan mode; guarded model-simulation requires explicit execution/cost flags and credentials; measured speech is imported separately"
            result["runtime_gate"] = "The guarded executor inspects authorized Worker status and requires remaining completion capacity >= the planned maximum and available USD >= worst_case_usd; saved planning does not reserve capacity."
        elif args.mode == "simulation":
            result = synthetic_matrix(json.loads(args.manifest.read_text()))
        elif args.mode == "model-simulation":
            from model_simulation import execute
            if not args.trace or not args.worker_url or not args.session_key_file:
                p.error("model-simulation requires --trace, --worker-url and --session-key-file; no requests sent")
            result = execute(args.trace, args.catalog, args.out, args.worker_url, args.session_key_file,
                args.journeys, args.cap_usd, args.max_completions, args.execute, args.ack_cost,
                args.window_segments, args.speech_rate_cps,max_runtime_s=args.max_runtime_s)
        else:
            if not args.measurements or not args.trace:
                p.error("measured mode requires --measurements and --trace; no model calls were made")
            result = measured_import(json.loads(args.measurements.read_text()), args.trace, args.cap_usd)
        if args.mode!='model-simulation':
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.mode == "model-simulation":
            print(json.dumps({key:result.get(key) for key in ("status", "completed_simulation_runs", "inference_dispatch_attempts", "actual_api_cost_usd", "failures")}, ensure_ascii=False, indent=2))
            if result["status"] != "complete":
                raise SystemExit(2)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.mode == "plan" and not result["allowed"]:
            raise SystemExit(2)
    except (ValueError, OSError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
