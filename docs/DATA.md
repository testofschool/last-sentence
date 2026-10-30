# Trace and timing evidence

`web/replay/trace_2026-10-30.jsonl` contains sample API observations from Seoul, not authored train positions. One successful poll produces up to five train records. Failed polls produce explicit gap rows. `recptnDt` and `trainSttus=1` provide a station-arrival proxy; neither field measures when doors open.

Source: Seoul Metropolitan Government/TOPIS, [real-time train position API specification](https://data.seoul.go.kr/dataList/openApiView.do?infId=OA-12601&srvType=A). The position schema describes `recptnDt` as final receipt time, `trainSttus` 0/1/2/3 as entering/arrived/departed/previous-station departed, and direction 0/1 as up or inner/down or outer. A provider receipt timestamp is retained as a proxy; it is not a physical arrival timestamp. The [dataset metadata](https://data.seoul.go.kr/dataList/datasetView.do?infId=OA-12601&serviceKind=1&srvType=A) identifies Seoul as the source and indicates attribution reuse terms. MIT applies to this project's code; source data retains its own terms and attribution.

The companion `.meta.json` records planned duration, poll count, observation count, gaps, and whether recording completed. A partial recording is useful for a demonstration and remains labeled partial.

```sh
python3 scripts/record_trace.py --line 2호선 --minutes 40 --interval 20 --key SAMPLE --out web/replay/new-trace.jsonl
python3 scripts/eta_model.py build web/replay/new-trace.jsonl
python3 scripts/eta_model.py evaluate web/replay/new-trace.jsonl --out evidence/eta_evaluation.json
python3 scripts/build_replay.py web/replay/new-trace.jsonl
```

The recorder accepts real credentials through `--key-file PATH`, never as literal command-line values. After four consecutive sample errors, it can use the protected `~/.seoul_rt_key` fallback. Keys and endpoint URLs containing keys are not written to trace files.

The ETA builder uses consecutive arrivals at adjacent known stations only. It rejects stale observations, non-arrival statuses, missing fields, authored fixtures, station skips, and intervals outside 10–600 seconds. Recorded gaps, source changes, and direction reversals break continuity. Distinct train identities are never stitched into one journey. Segment medians require at least two observations. Unseen segments use an explicitly reported line median when available. There is no invented default ETA for an empty trace.

Validation withholds the complete train identity (line, direction, service date, train number). Three to ten segment predictions use only the other train identities. The report includes the actual number of scored windows. No eligible windows means **insufficient recorded data**, with a null error and null pass/fail value. It does not pass the registered ≤15% error gate by omission.

`recorded-manifest.json` selects one longest contiguous observed station chain per train identity, with at least two arrivals. Displayed windows use its first five observed station events by default (`build_replay.py --max-stations 5`). Each window records the selected chain's full station count, displayed station count, and whether the window was limited. The raw recording and ETA evaluation retain all observations. Its `eta_s` is the already-known duration of that replay clock, **not an ETA forecast**. Story scheduling against that clock demonstrates the interaction; it does not measure prediction or model accuracy. The selected routes are partial observed journeys, not an advertised coverage list for the whole subway system.

`manifest.json` is a separate set of three authored timing fixtures. It is used by deterministic controller tests and the explicitly labeled synthetic comparison. It must not be presented as a recording or inference output.

The model pricing snapshot in `evidence/model-prices.json` is a compact, tracked extract of the public catalog checked on 2026-10-30. It makes cost planning reproducible in a fresh clone. It does not establish account access, credits, or billing charges. `run_matrix.py` plans conservatively, simulates fixtures, or audits separately recorded browser measurements; default modes do not spend API credits.

Measured imports bind each arrival to its line, train number, station, provider timestamp, and the trace hash. Only the three configured Nemotron model IDs are accepted. API receipt `calls[]` are flattened; each call requires prompt/completion usage, latency, and `pricing.input_price_per_million_tokens` / `pricing.output_price_per_million_tokens`. The importer recomputes cost from those rates and usage and checks aggregate costs. These are arithmetic/provenance checks, not authentication of a provider bill or validation of the model's story content.

Coverage is reported as fully paired, mixed, or unpaired. A paired comparison requires all three policies for the same frozen journey ID and the same train, line, exit station and observed arrival. A table containing unpaired journeys is explicitly descriptive, not a controlled same-journey comparison.

## Guarded model-backed timing simulation

The optional `--mode model-simulation` runner consumes actual contiguous recorded windows of 3–10 segments, fits ETA excluding the whole target train identity, and calls the protected Worker Conductor/Writer APIs. It estimates speech from generated Unicode character counts at a fixed cps, advances its virtual clock by measured HTTP latency, and applies revisions at sentence boundaries. This is **model-backed timing simulation**, not browser TTS or door-open accuracy. Other train identities from the complete offline trace may supply training data from later clock times; it is not forward-in-time online validation.

Execution requires all of: explicit `--execute`, `--ack-cost 3` acknowledging the configured $3 ceiling, an owner-protected mode-600 Worker session-token file, a price snapshot checked within one hour, and an authorized Worker with enough remaining completion and dollar reservations. The Worker must enforce a budget no higher than the requested runner cap. The runner checks capacity before each dispatch, reserves worst-case tokens/calls, limits Writer requests to four per story, and aborts when usage, prices, costs or remaining capacity cannot be validated. It never retries paid failures automatically. A fresh output path prevents accidental repeated spending.

```sh
python3 scripts/run_matrix.py --mode model-simulation --journeys 5 \
  --trace web/replay/trace_2026-10-30.jsonl --catalog evidence/preflight/prices.json \
  --worker-url https://YOUR-WORKER.example --session-key-file ~/.last_sentence_session \
  --execute --ack-cost 3 --out evidence/model-simulation-run.json
```

Refresh the public price snapshot first with `python3 -I scripts/preflight.py`; this performs public read-only checks, not inference. The example was not executed during the keyless build. Tests use injected mock HTTP responses only. The default full-30 plan is refused. Five windows × three policies plus an EN/KO pair fit the default conservative reservation plan. Only lines actually present in eligible recordings are included; the current line-2 recording supplies no line-5/7 measurements. Every dispatched attempt and failed response is retained; missing usage makes actual cost **unknown**, never zero. Tavily is not called by this timing runner; stories use the exit station only. Arithmetic receipt checks do not authenticate provider billing or validate semantic story quality.
