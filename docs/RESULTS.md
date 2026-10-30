# Results

**Synthetic timing simulation.**

Three authored journey fixtures, not 30 observed journeys. No model, Tavily, or browser speech measurements. Does not establish real-world accuracy.

Measured inference runs: **0**. Rows in this table: **9**. Actual API cost represented: **$0.000000**.

Paired coverage: **3 of 3 journeys** have all three policies. Unpaired journeys: **0**. Comparison basis: **fully-paired**.

All policy groups below cover the same journey fixtures or frozen observed journeys.

The full 30-journey × 3-policy evaluation and EN/KO model pair are **UNRUN**.

| Policy | n | ≤30 s | ≤10 s | Median absolute error | Cost/story | p50 call latency |
|---|---:|---:|---:|---:|---:|---:|
| fixed_clip | 3 | 33.3% | 33.3% | 40.0 s | $0.000000 | UNMEASURED |
| single_fit | 3 | 100.0% | 66.7% | 10.0 s | $0.000000 | UNMEASURED |
| sentence_replan | 3 | 100.0% | 100.0% | 1.0 s | $0.000000 | UNMEASURED |

Positive error means the story ended after the arrival proxy; negative means before it.

![Landing error by policy](landing-error.svg)

## Interpretation

The fixture controller uses a boarding forecast of 600 seconds and a historical segment forecast of 150 seconds. Only station events already observed at a sentence boundary can revise the forecast. The final arrival timestamp is withheld from scheduling and used only to score the result. Mocked speech lasts 12 seconds per sentence. These assumptions do not establish Nemotron, TTS, live-train, or door-open accuracy.

A numerical comparison with the earlier handoff's simulation is unavailable: its uncertainty model and data were not reproduced here.

## Observed ETA proxy validation

This section describes recorded station-arrival ETA validation. It is separate from the story-policy comparison above and does not measure Nemotron story generation, browser speech timing, or model-backed story landing accuracy.

| Recorded ETA measure | Value |
|---|---:|
| Eligible held-out forecast windows | 338 |
| Train identities represented by arrival chains | 9 |
| Median relative error | 4.9552% |
| Registered median error ≤15% gate | PASS |

Method: `leave-one-train-identity-out`. Status: `measured`. Forecast windows can overlap and reuse stations within a train identity; the window count is not a count of independent journeys or independent samples. The complete held-out train identity is excluded from fitting. No result here establishes performance on unobserved routes or operating periods.

Receipt timestamp age: **p50 50 s / p95 97 s** across **600 repeated polling records**. This is polled `ts` minus provider `recptnDt`: timestamp age, **not network lag, transport delay, or door-open offset**. Repeated polls are not independent journeys.

Trace snapshot: 600 observation records, 120 distinct polls, 0 gap records. Recording marked partial: `False`.

ETA and trace-quality artifacts reference the same trace snapshot, also matching the current local trace.

| Snapshot | SHA-256 |
|---|---|
| ETA artifact | `081db5eeb3a0273d0447869a693397b65e45e05f0fe60c528e772100891703e5` |
| Trace-quality artifact | `081db5eeb3a0273d0447869a693397b65e45e05f0fe60c528e772100891703e5` |
| Current local trace | `081db5eeb3a0273d0447869a693397b65e45e05f0fe60c528e772100891703e5` |

## Five largest absolute errors

Rows retained verbatim from this matrix, including failures:

```json
[
  {
    "id": "line7-fixture",
    "line": "7호선",
    "policy": "fixed_clip",
    "landing_error_s": 45,
    "evidence_kind": "synthetic-timing-simulation",
    "conductor_calls": 0,
    "writer_calls": 0,
    "simulated_forecast_updates": 0,
    "tokens": 0,
    "cost_usd": 0,
    "p50_latency_ms": null,
    "p95_latency_ms": null,
    "tool_calls_supported": null,
    "tavily_ok": null,
    "arrival_event": "station-arrival-proxy",
    "speech_clock": "mocked-12-second-sentences"
  },
  {
    "id": "line2-fixture",
    "line": "2호선",
    "policy": "fixed_clip",
    "landing_error_s": 40,
    "evidence_kind": "synthetic-timing-simulation",
    "conductor_calls": 0,
    "writer_calls": 0,
    "simulated_forecast_updates": 0,
    "tokens": 0,
    "cost_usd": 0,
    "p50_latency_ms": null,
    "p95_latency_ms": null,
    "tool_calls_supported": null,
    "tavily_ok": null,
    "arrival_event": "station-arrival-proxy",
    "speech_clock": "mocked-12-second-sentences"
  },
  {
    "id": "line5-fixture",
    "line": "5호선",
    "policy": "single_fit",
    "landing_error_s": 13.0,
    "evidence_kind": "synthetic-timing-simulation",
    "conductor_calls": 0,
    "writer_calls": 0,
    "simulated_forecast_updates": 1,
    "tokens": 0,
    "cost_usd": 0,
    "p50_latency_ms": null,
    "p95_latency_ms": null,
    "tool_calls_supported": null,
    "tavily_ok": null,
    "arrival_event": "station-arrival-proxy",
    "speech_clock": "mocked-12-second-sentences"
  },
  {
    "id": "line5-fixture",
    "line": "5호선",
    "policy": "fixed_clip",
    "landing_error_s": 10,
    "evidence_kind": "synthetic-timing-simulation",
    "conductor_calls": 0,
    "writer_calls": 0,
    "simulated_forecast_updates": 0,
    "tokens": 0,
    "cost_usd": 0,
    "p50_latency_ms": null,
    "p95_latency_ms": null,
    "tool_calls_supported": null,
    "tavily_ok": null,
    "arrival_event": "station-arrival-proxy",
    "speech_clock": "mocked-12-second-sentences"
  },
  {
    "id": "line7-fixture",
    "line": "7호선",
    "policy": "single_fit",
    "landing_error_s": 10.0,
    "evidence_kind": "synthetic-timing-simulation",
    "conductor_calls": 0,
    "writer_calls": 0,
    "simulated_forecast_updates": 1,
    "tokens": 0,
    "cost_usd": 0,
    "p50_latency_ms": null,
    "p95_latency_ms": null,
    "tool_calls_supported": null,
    "tavily_ok": null,
    "arrival_event": "station-arrival-proxy",
    "speech_clock": "mocked-12-second-sentences"
  }
]
```

## Reproduce

```sh
python3 scripts/run_matrix.py --mode plan --journeys 5 --out evidence/cost-plan-default-cap.json
python3 scripts/run_matrix.py --mode simulation --out evidence/simulation-matrix.json
python3 scripts/make_results.py evidence/simulation-matrix.json
```

Planning uses the saved live model catalog and includes all Conductor fallback attempts. Both the dollar ceiling and the default 300 lifetime completion ceiling are checked; 5 journeys × 3 policies plus 2 language runs have a conservative 295-completion bound. A 17-journey plan requires an explicitly configured Worker ceiling of at least 811 completions and the same $3 guard. The guarded runner inspects authorized Worker status for remaining capacity before beginning and before every inference dispatch. A denied plan exits with code 2 and makes no requests. Default modes make no inference requests. `--mode model-simulation` requires `--execute`, `--ack-cost 3`, a protected session-token file, a price snapshot checked within one hour, and an inference-ready Worker. For actual timing results, instrument browser speech-end events and import them with `run_matrix.py --mode measured --measurements FILE --trace RECORDED.jsonl`. The importer requires matching trace SHA-256, actual arrival records, complete usage/cost/latency receipts, and a total cost no higher than $3.00. Character-count speech estimates are rejected as measured audio.

Model-backed timing simulation example (requires separately authorized execution and configured credentials):

```sh
python3 scripts/run_matrix.py --mode model-simulation --journeys 5 \
  --trace web/replay/trace_2026-10-30.jsonl --catalog evidence/preflight/prices.json \
  --worker-url https://YOUR-WORKER.example --session-key-file ~/.last_sentence_session \
  --execute --ack-cost 3 --out evidence/model-simulation-run.json
```

Refresh the public price snapshot first with `python3 -I scripts/preflight.py`. This command was not executed in the keyless build. It writes real call receipts alongside simulated timing; the output is never accepted as measured browser/audio landing performance.
