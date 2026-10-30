# Trace and timing evidence

`web/replay/trace_2026-10-30.jsonl` (line 2), `trace_2026-10-30_line5.jsonl` and `trace_2026-10-30_line7.jsonl` contain sample API observations from Seoul, not authored train positions. Their combined snapshot is `trace_2026-10-30_all_lines.jsonl`; the original files remain intact. One successful poll produces up to five train records. Failed polls produce explicit gap rows. `recptnDt` and `trainSttus=1` provide a station-arrival proxy; neither field measures when doors open.

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

`evidence/browser_speech.json` records three uninterrupted 1× local browser UI checks with hand-authored sentences: line 2 English, line 5 Korean and line 7 English. Their displayed speech ends were 9.3, 4.1 and 7.0 seconds before the known observation clock. The routes were crosschecked against unique actual raw observation pairs. These development-page checks used no model/search requests; they are excluded from the model-policy matrix and do not establish prospective ETA, final-build device coverage or door-opening accuracy. Screenshots retain the exact UI state at the time of each check.

The line-5 and line-7 graphs in `web/replay/topology.json` come from the official Seoul Metro SMSS map. A separate public Seoul timetable snapshot dated September 30, 2025 corroborates all 55 line-5 edges and 52 line-7 edges after documented alias normalization. Two one-off missing-stop jumps in scheduled rows are retained as unconfirmed candidates and excluded from physical adjacency. These scheduled stops are not used as actual train observations or ETA training data. See `evidence/topology/crosscheck.json` and `timetable-adjacency.json`; full downloaded website assets remain local-only. To reproduce the timetable extract, download the CSV from its linked official dataset and run `python3 scripts/extract_timetable_topology.py PATH.csv`.

The model pricing snapshot in `evidence/model-prices.json` is a compact, tracked extract of the public catalog checked on 2026-10-30. It makes cost planning reproducible in a fresh clone. It does not establish account access, credits, or billing charges. `run_matrix.py` plans conservatively, simulates fixtures, or audits separately recorded browser measurements; default modes do not spend API credits.

Measured imports bind each arrival to its line, train number, station, provider timestamp, and the trace hash. Only the three configured Nemotron model IDs are accepted. API receipt `calls[]` are flattened; each call requires prompt/completion usage, latency, and `pricing.input_price_per_million_tokens` / `pricing.output_price_per_million_tokens`. The importer recomputes cost from those rates and usage and checks aggregate costs. These are arithmetic/provenance checks, not authentication of a provider bill or validation of the model's story content.

Coverage is reported as fully paired, mixed, or unpaired. A paired comparison requires all three policies for the same frozen journey ID and the same train, line, exit station and observed arrival. A table containing unpaired journeys is explicitly descriptive, not a controlled same-journey comparison.

## Historical browser-audio clock mapping

Contemporaneous live speech imports retain the shared wall-clock calculation. A historical replay must instead include an explicit per-row `clock_mapping` and matching `controller_provenance.policy`. The recorded boarding timestamp and raw station name must match an actual `trainSttus=1` observation for the same line, train and direction as the exit, within one contiguous recorded station chain. The wall-clock playback origin and actual `speech_end_at` must include timezones, be in the past and occur in chronological order. Only uninterrupted 1× playback with no pause or seek is accepted. Character-rate simulations remain ineligible.

Format fragment only, **not a measured run**:

```json
{
  "controller_provenance": {"policy": "fixed_clip", "eta_source": "recorded-replay"},
  "clock_mapping": {
    "kind": "historical-replay-1x",
    "source": "recorded-observations",
    "direction": "1",
    "speed": 1,
    "uninterrupted": true,
    "paused": false,
    "seeked": false,
    "recorded_origin_station": "RAW_BOARDING_STATION_NAME",
    "recorded_origin_at": "2026-10-30T10:00:00+09:00",
    "playback_origin_at": "2026-10-30T11:00:00+09:00"
  }
}
```

The importer scores `(speech_end_at − playback_origin_at) − (arrival_at − recorded_origin_at)`, preserving both the mapping and controller provenance. It rejects mismatched/future origins, source/direction mismatches and interrupted or accelerated playback. A historical browser-audio result measures speech against a known replay clock; it does not establish prospective ETA or actual door-open accuracy.

## Guarded model-backed timing simulation

The optional `--mode model-simulation` runner consumes actual contiguous recorded windows of 3–10 segments, fits ETA excluding the whole target train identity, and calls the protected Worker Conductor/Writer APIs. It estimates speech from generated Unicode character counts at a fixed cps, advances its virtual clock by measured HTTP latency, and applies revisions at sentence boundaries. This is **model-backed timing simulation**, not browser TTS or door-open accuracy. Other train identities from the complete offline trace may supply training data from later clock times; it is not forward-in-time online validation.

Execution requires all of: explicit `--execute`, `--ack-cost 3` acknowledging the configured $3 ceiling, an owner-protected mode-600 Worker session-token file, a price snapshot checked within one hour, and an authorized Worker with enough remaining completion and dollar reservations. The Worker must enforce a budget no higher than the requested runner cap. The runner checks capacity before each dispatch, reserves worst-case tokens/calls, limits Writer requests to four per story, and aborts when usage, prices, costs or remaining capacity cannot be validated. It never retries paid failures automatically. A fresh output path prevents accidental repeated spending.

The real experiment runtime defaults to 7,200 seconds and cannot exceed that ceiling (`--max-runtime-s`). A rolling-minute pacer conservatively reserves complete plan/write groups against 45RPM and 300,000 input+output tokens/minute, leaving headroom below the checked 60RPM/400,000TPM baseline. Pacing counts in real runtime but is excluded from the simulated speech clock: an accelerated offline benchmark must not mistake its artificial dispatch spacing for the natural interval between subway stations. This assumes no competing account traffic and does not guarantee provider acceptance. Public prices are revalidated read-only after one hour; unavailable or changed rates stop further dispatch without raising the acknowledged cost bound. Public-price audit waits are also excluded from simulated speech timing; the Worker's own model/catalog HTTP latency remains included. Tests inject clocks and sleeps and make no paid requests.

Each inference request includes `expected_pricing` for its selected model. The runner requires the Worker to advertise that capability; before each completion attempt the Worker fetches a fresh public catalog entry and refuses a mismatch before reserving quota or contacting inference. Per-call receipts must report fresh acknowledged pricing and the exact usage/cost arithmetic. This checks the latest advertised price; public catalog and provider billing are not an atomic transaction. Runner HTTP timeouts match the frontend budgets:90 seconds for a plan,45 for writing,25 for status, each capped by remaining real runtime. Dispatched failures are recorded and never retried automatically.

```sh
python3 scripts/run_matrix.py --mode model-simulation --journeys 30 --max-completions 2048 \
  --trace web/replay/trace_2026-10-30_all_lines.jsonl --catalog evidence/model-prices.json \
  --worker-url https://YOUR-WORKER.example --session-key-file ~/.last_sentence_session \
  --execute --ack-cost 3 --max-runtime-s 7200 --out evidence/model-simulation-run.json
```

Refresh the public price snapshot first with `python3 -I scripts/preflight.py`; this performs public read-only checks, not inference. The example was not executed during the keyless build. Tests use injected mock HTTP responses only. The full-30 plan fits the $3 guard at the checked prices with the explicit 2,048-completion setting; the default 300 setting still refuses it. The intended dataset has 10 eligible windows per recorded line, and inadequate line coverage must stop that full experiment. Every dispatched attempt and failed response is retained; missing usage makes actual cost **unknown**, never zero. Tavily is not called by this timing runner; stories use the exit station only. Arithmetic receipt checks do not authenticate provider billing or validate semantic story quality.
