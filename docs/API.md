# Last Sentence API

The deployed build is a keyless recorded/fixture replay. It performs no model or search calls. The [canonical Worker](https://last-sentence.felix-market-radar.workers.dev) serves the generated `dist/` assets (web plus documents) and same-origin `/api/*` routes. [Cloudflare Pages](https://last-sentence.pages.dev) is a static keyless mirror; [the public repository](https://github.com/testofschool/last-sentence) has an MIT license. Public UI/assets and API status were verified on October 30, 2026 KST. A local `~/.nebius_key` is now present with mode `600`, but two direct POST `/v1/chat/completions` authentication smokes returned HTTP 401, with no provider model identity, usage or actual cost. Two separate read-only GET `/v1/models` diagnostics also returned HTTP 401 and requested no completion. Successful Nemotron completions, matrix evaluation, controlled Korean feedback and Tavily search remain **UNRUN**. The provider credential has not been uploaded to the Worker, and deployed inference remains disabled. Real Nemotron inference is directly authorized up to $3 total; refresh prices and inspect shared reservations before execution. A conservative outside-Worker reserve of 1,974 microUSD ($0.001974) is retained for the two smokes, leaving a planned Worker cap of $2.998026; that reduced cap has not been deployed and is not a verified provider charge.

## Run and configure

```sh
npm ci --prefix worker
npm run dev --prefix worker
```

The `predev` and `precheck` hooks run `scripts/build.mjs` to refresh `dist/`, including document links, before preview or dry-run packaging. `npm run build` at the project root performs the same static assembly.

`worker/wrangler.jsonc` keeps `ENABLE_LIVE=false`. Copy `worker/.dev.vars.example` to ignored `.dev.vars` for local Worker development. Configure server secrets `NEBIUS_API_KEY`, `SEOUL_RT_KEY` (`SAMPLE` opts into the public five-train sample), `TAVILY_API_KEY`, and a strong `LIVE_ACCESS_TOKEN` when authorized. Set `ENABLE_LIVE=true` explicitly. For the deployed Worker, use Wrangler secret storage. A key file being present does not automatically enable inference.

Every live request requires `Authorization: Bearer <LIVE_ACCESS_TOKEN>`. This is an application session credential, never a provider key. Keep it in browser session memory and out of URLs and static assets. Same-origin requests work by default; an optional `ALLOWED_ORIGIN` must exactly match a separately hosted frontend. Cross-origin requests otherwise receive 403. The Node local preview can route `core.js` with an empty environment to retain the same disabled status semantics.

## Contract

Every JSON API response includes `receipt_schema:'last-sentence/receipt-v2'`, `model`, `usage`, `cost_usd`, and `latency_ms`. Completion calls also carry this schema version. `model:null`, `usage:null`, `cost_usd:0` means no inference happened. Attempted completions include a `calls` array with one entry per attempt. The compatibility `model` field is the requested ID; `requested_model` states this explicitly. `provider_reported_model` retains a bounded model identifier reported by the provider, or null; `identity_match` is true only on exact equality with the requested documented ID. Missing or mismatched identity returns HTTP502 `provider_model_missing` or `provider_model_mismatch` before using output or making another completion attempt. Undocumented aliases are refused. Usage, latency and the reservation remain recorded, but `cost_usd` stays null for unverified identity. `requested_rate_cost_estimate_usd` separately retains usage multiplied by the requested model's catalog rates; it is not a verified charge for a different or unidentified model. Invalid identifiers and unrecognized values containing a configured credential are omitted; the three public allowlisted model IDs are safe metadata.

Each call's `pricing` includes `input_price_per_million_tokens`, `output_price_per_million_tokens`, `source_url`, `observed_at`, and `catalog_cache_ttl_s:3600`. With matched identity and returned usage, `cost_usd` is a usage/catalog estimate, not an invoice or independent verification of model weights. Missing usage or failed upstream calls retain null cost. Aggregate responses expose the same identity and requested-rate-estimate fields; strict consumers require each call's matched provenance. A Tavily search has `usage:{search_calls:1}`, with USD cost null because a model-token catalog does not price search credits. Status advertises the same `receipt_schema` plus `receipt_provenance_supported:true` and `writer_validation_supported:true`, so prepared collectors can reject an older Worker before dispatch.

### GET /api/status

Returns `mode:'replay-only'|'live-ready'`, `inference_enabled`, `position_enabled`, `tavily_enabled`, and `auth_required:true`. `eta_models` contains independent quality gates for lines 2, 5 and 7; `eta_model_lines` lists the ready lines. `eta_model_configured` means at least one line is ready, while the backward-compatible `eta_model` remains line 2's result. The frontend must inspect its selected line's entry. An incomplete recording never enables that line. This route does not require authorization or call providers. `limits` reports the configured completion and dollar ceilings. With a valid session credential, it also reads Durable Object reservation usage and remaining completion calls; anonymous requests retain null usage fields. Before an experiment, compare the cost plan's worst-case completion count to the authenticated remaining count. Configured service status does not prove provider credentials are valid.

### GET /api/position?line=2호선

Supports lines 2, 5, 7 only. Returns `mode:'live'`, `positions:[{subwayId,trainNo,statnId,statnNm,updnLine,trainSttus,recptnDt,statnTnm,statnTid,directAt,lstcarAt}]`, `sample_key`, `transport`, `transport_fallback`, and `observed_at`. The terminus name/ID and express/last-train flags are preserved. The provider defines `recptnDt` as final receipt time and `trainSttus=1` as arrival status. This is a receipt-time proxy, never a door sensor. Experimental forecasts are available separately through `/api/eta`.

Disabled configuration, a missing Seoul key, upstream no-data, or the 950-call ceiling returns `mode:'replay-forced'`, `positions:[]`, and a reason. Only disabled mode may be queried without a session token. Success responses cache for 15 seconds before reserving a new provider call. Private API keys are sent only over HTTPS to the configured Seoul origin. The published `sample` key may fall back from a three-second HTTPS attempt to HTTP, explicitly labeled `transport:'http-public-sample'`; each transport attempt reserves its own daily slot. Private keys never use HTTP. A successful canonical station arrival with direction 0/1 is retained as an internal anchor for at most 300 seconds; departure updates do not erase it, and older out-of-order arrivals cannot overwrite a newer anchor.

### GET /api/eta

This read-only route makes no vendor request and needs no provider key. It loads `replay/eta-bundle.json`, `eta-bundle-5.json`, or `eta-bundle-7.json` for the selected line. Each artifact contains a model and evaluation produced from one trace snapshot. Readiness requires a complete recording, a valid trace SHA-256, recorded source, at least 10 leave-one-train-identity-out predictions across at least two train identities, and a measured median relative error at or below 15%. A failed or missing gate returns `eta_available:false` with a reason. Overlapping evaluation windows, receipt timestamps and off-peak recording limit the interpretation of that gate.

`?line=2호선&trainNo=1234&direction=0` reads the latest internally cached verified arrival and returns `reason:'choose_exit'`, the anchor, and `eligible_exits`. Add `&to=을지로4가` to receive `remaining_s`, `stations_left`, the full ordered route, per-segment line-median fallbacks, `anchor_age_s`, `valid_until`, and evaluation provenance. Line 2 direction 0 follows the observed inner-loop order. Lines 5 and 7 use independently confirmed direction maps from adjacent recorded transitions. Their bundles embed the official 56-node line 5 graph (including the 강동 fork) or 53-node line 7 graph, its published edge set, aliases and observed realtime API-ID bindings. SMSS map codes are never substituted for realtime API station IDs.

Verified arrivals require both a canonical station name (or documented alias) and its matching realtime station ID. Line 2 uses a fixed 43-stop main-loop map; the frozen recording corroborates 40 of its name/ID pairs without mismatch, while 봉천, 신림 and 신대방 were not observed. Lines 5 and 7 accept only directly observed API-ID bindings. A known name with a missing, unknown, or conflicting ID does not create an anchor. The `arrival-v2` cache namespace excludes older name-only anchors. Verified forecasts also require the provider's actual train terminus name and matching mapped API ID. The suffix `종착` is normalized only with a matching canonical station ID. Routing follows the directed graph toward that actual terminus: line 5's 하남 and 마천 branches cannot be concatenated or switched. Eligible destinations stop at the forward terminus; a short-turn train is never assumed to complete a circle. Unknown/mismatched termini return `verified_terminus_unavailable`; an unreachable terminus returns `terminus_direction_mismatch`. Initial choices marked `horizon_supported:true` are 3–10 stops away, matching the evaluated horizons. One- and two-stop continuations remain explicitly outside the evaluated horizon. More than 10 stops is unavailable. Each new line remains disabled until its full recording and held-out gate pass.

The calculation sums recorded segment medians, uses the recorded line median only for missing segments, discloses every fallback, then subtracts elapsed wall time since the arrival-status receipt. A missing anchor, an anchor older than 300 seconds, a timestamp more than five seconds ahead of the server clock, or an unsupported direction or route produces no guessed uniform ETA. Up to five seconds of future clock skew is tolerated and its elapsed age is treated as zero. `anchor.epoch_s` is the provider receipt timestamp expressed in UTC seconds. A verified arrival-status anchor already at the target returns `arrived:true`, `remaining_s:0`; this remains an observation proxy rather than physical door opening.

The manual form `?line=2호선&from=시청&to=을지로4가&direction=0&observed_at=2026-10-30T10:19:20%2B09:00` is labeled `eta_source:'operator-estimate'`, `anchor.verified:false`. It cannot masquerade as a verified live observation. Estimates are experimental, with polling interval 20 seconds and provider lag and door offsets unmeasured.

### POST /api/plan

```json
{
  "current_station":"왕십리", "exit_station":"성수",
  "stations_left":3, "remaining_s":300, "elapsed_story_s":60,
  "eta_source":"recorded-model",
  "remaining_scenes":[{"id":"scene-1","chars":1500}]
}
```

`eta_source` is required: `recorded-model`, `recorded-replay`, `operator-estimate`, or `synthetic-fixture`. `recorded-replay` uses a replay's known timeline and is not a held-out ETA prediction. The server does not invent an ETA from raw station names. The frontend must retain this provenance. Remaining time is 0–7200 seconds, station count 0–60, and at most 12 scenes are accepted.

The Conductor uses `nvidia/Nemotron-3_5-Lightning`. There are at most two tool-call attempts and one final JSON completion, each capped at 400 output tokens. The server executes only `eta_to_station`, `budget`, and `scene_ops`; it passes actual tool results back to the model. `tool_calls_supported` reports whether any call was emitted; `required_tools_completed` separately records whether all three tools ran. JSON fallback is labeled explicitly. The server computes the authoritative budget as `floor(max(0, remaining_s−20)×4.51)` and validates scene targets and operations. A model cannot overwrite the ETA or budget.

Each distinct tool executes at most once per plan. At most four scene operations are accepted, with reasons limited to 96 Unicode characters. Tool arguments are limited to 4096 UTF-8 bytes. Assistant text in a tool turn is limited to 256 bytes; a no-tool retry response is limited to 2048 bytes. Unknown argument fields, duplicate tools and oversized replies are rejected explicitly. Validated tool fields are serialized canonically into the history; full ETA provenance remains in the API response while the tool receives the timing, route, fallback and anchor fields needed for its decision. No user or model text is silently truncated to fit a budget.

Live requests supply `train_anchor:{line,trainNo,direction,to}`. The server recomputes the experimental ETA from its verified arrival cache and validated bundle, replaces client station/time/count fields, and returns that actual data through `eta_to_station` and the response's `eta` object. A client-supplied `eta_source:'recorded-model'` without a verified anchor is refused. Explicit replay and operator-estimate inputs remain available for labeled demonstrations.

Returns `plan:{stations_left,remaining_s,budget_chars,eta_source,ops:[{scene,op,reason}],log}`, `tool_calls_supported`, `required_tools_completed`, and `tool_executions`. Scene operations are `insert`, `drop`, or `compress`.

### POST /api/write

```json
{
  "lang":"en", "exit_station":"Seongsu", "budget_chars":180,
  "is_last_scene":true, "scene":"The traveler finds a final clue.",
  "fact":{"text":"A supplied source snippet.","url":"https://example.org/source"}
}
```

Uses `nvidia/nemotron-3-super-120b-a12b` for English, `nvidia/Nemotron-3-Ultra-550b-a55b` for Korean, with `reasoning_effort:'none'`. Scene budgets are 1–4000 Unicode characters. Maximum output tokens are `min(1200,max(60,ceil(budget_chars×1.5)))`. Lines exceeding 90 characters in English or 40 in Korean, total character overflow, or a final line that does not end with the exact exit name are rejected. The returned failure retains the cost of the rejected model call. No truncation is hidden as model compliance.

Returns `sentences`, `sentence_cap`, `char_count`, `fact_grounding`, and receipt fields. Source snippets are untrusted data. Whether the final sentence accurately names a supplied fact is not semantically verified by this validator; `fact_grounding` makes that limit explicit.

Every attempted Writer completion also records `calls[0].writer_validation`, including rejected replies. Its counting basis is `trimmed-nonempty-lines/unicode-code-points`: these are line-based units, not a semantic sentence parser. The bounded summary reports purpose/language, sentence count, within/over-cap counts, maximum and total characters, sentence and scene limits, ending checks, pass/failure flags and reason enums. Uninspected or nontext replies have null observed counts rather than fabricated zeros; observed empty text has zero counts. Completion failures use `status:'not_inspected'`; observed rejected content uses `status:'rejected'`. No rejected text or unbounded per-line arrays are returned. This supports a future obedience-rate denominator while retaining failed attempts; it does not establish language or story quality.

For the original controlled feedback comparison only, `/api/write` accepts this separate authenticated shape:

```json
{
  "purpose":"feedback-korean-compare", "lang":"ko",
  "feedback_model":"nvidia/nemotron-3-super-120b-a12b",
  "sentence_count":3, "budget_chars":120,
  "scene":"The identical Korean scene description for both models.",
  "expected_pricing":{"model":"nvidia/nemotron-3-super-120b-a12b","input_price_per_million_tokens":0.1,"output_price_per_million_tokens":0.3}
}
```

The two numeric rates above illustrate the schema; the collector must use fresh acknowledged catalog rates. `feedback_model` accepts only the exact Super or Ultra ID. No other fields, fact or destination-ending settings are accepted. The same fixed Korean prompt requests exactly three nonempty lines, at most 40 Unicode characters each and 120 total, with `max_tokens:180`. The shared atomic dollar/completion quotas, fresh expected-price guard and exact provider identity checks apply. Validation records `purpose:'feedback-korean-compare'`, `required_sentence_count:3`, `max_sentence_count:3`; a count mismatch includes `exact_sentence_count`. Normal product routing remains Super English/Ultra Korean. Status advertises `feedback_korean_compare_supported:true` and `feedback_probe_limits` for pre-dispatch checks. Preparing this branch does not imply that any comparison was executed.

### GET /api/fact?station=Seongsu

One Tavily basic search, maximum three results, returns a short source snippet and HTTPS URL in `fact:{text,url}`, plus `tavily_ok`. A missing key, search failure, zero results, or the 100-search lifetime ceiling returns `fact:null`, `tavily_ok:false`, and a reason. The story may then use the station name only. A retrieved snippet is source material, not independent verification of the fact.

## Quotas and bounded failures

`UsageLimits` is a SQLite Durable Object. Its coordination atom is this application's shared provider quota, so all requests deliberately use one deterministic object. Synchronous transactional reservations avoid a KV read/modify/write race:

* Seoul: at most 950 uncached upstream attempts per KST day. Failed attempts also consume a slot.
* Inference: the default ceiling is 300 lifetime completions, including all retry/fallback attempts. The full 30-journey × 3-policy experiment plus two language runs reserves at most 1370 completions. Its explicit local profile is `worker/.dev.vars.matrix.example` with capacity 2048 and live calls disabled until separately enabled. The application's hard reservation ceiling is at most $3. At the saved current prices and enforced 16,384 input envelope, the full worst-case plan is $2.60596288. Before each call, reserve estimated worst-case token cost from current catalog prices, serialized prompt UTF-8 bytes plus a 4096-token framing allowance, and maximum output tokens. Reservations are never refunded. Configuration can lower the ceiling but cannot raise it above $3 in this build. The current resumption plan lowers the Worker portion to $2.998026 to retain the two direct smokes' conservative $0.001974 reserve outside this ledger; this change is planned, not deployed. Provider usage and actual cost for the HTTP 401 smokes remain null.
* Tavily: at most 100 lifetime search attempts, including failures.

Before each completion, the server rejects a serialized UTF-8 prompt plus framing allowance above the enforced 16,384 input envelope, including expanded tool-loop context. `/api/status` exposes `max_input_token_bound:16384` and the explicit `prompt_limits`. Each completion receipt records its actual conservative `input_token_bound`. The runner must match this limit to its cost plan. `scripts/measure_prompt_envelope.mjs` stresses maximum legal scene identifiers, operation reasons, retry histories, all three route graphs, EN/KO Writer inputs, four-byte Unicode and JSON escaping. All 24 controlled cases fit; the largest serialized request plus framing was 15,898. These are mocked payload measurements, with zero provider calls. Oversized responses are rejected rather than silently shortened; earlier attempted-call costs remain in their receipts.

Both model endpoints optionally accept `expected_pricing:{model,input_price_per_million_tokens,output_price_per_million_tokens}`. Its model must match the selected Conductor or Writer and both rates must be finite nonnegative numbers. `/api/status` advertises `expected_pricing_supported:true`. For each completion attempt carrying this assertion, the Worker bypasses its one-hour catalog cache and requests the public catalog with [`cache:'no-store'`](https://developers.cloudflare.com/workers/runtime-apis/fetch/). A mismatch returns HTTP409 `pricing_changed` before reserving or dispatching that attempt; earlier attempted-call receipts remain visible. The assertion stays outside the model prompt. Matching receipts mark `pricing.fresh_for_dispatch:true` and `pricing.acknowledged:true`. This checks advertised rates immediately before dispatch; catalog retrieval and provider billing cannot be made atomic by this Worker. Requests omitting the assertion retain the documented one-hour catalog cache.

The cost reservation is a conservative application bound, not a guarantee about provider billing, hidden tokenizer overhead, price changes, or account charges elsewhere. A separately precomputed experiment cap and account credit checks are still required for real evaluation. The model catalog is cached for one hour; no hardcoded handoff price is silently used. Missing pricing, missing quota bindings, malformed provider data, or exhausted inference reservations fail closed.

Request JSON is limited to 24 KB. Upstream JSON is streamed with a bounded size and a 20-second timeout per request. There are no automatic unbounded retries. Provider bodies, API keys, and secret-bearing URLs never appear in error responses.

## Local verification

```sh
node --test tests/worker.test.mjs tests/worker_quota.test.mjs
npm run check --prefix worker
npm run types --prefix worker
```

The unit suite mocks all provider fetches. The integration test uses local workerd/Miniflare to exercise 1000 concurrent SQLite reservations and verifies exactly 950 are accepted; it also checks completion and search ceilings. It skips explicitly if Worker development dependencies have not been installed. `check` is a dry run and does not deploy.

The separate opt-in command `node scripts/check_worker_runtime.mjs --public-sample` starts an owned loopback Worker on port 8792 and makes up to three published-SAMPLE position polls per line, 20 seconds apart (at most 18 HTTPS/HTTP transport attempts). It requires all three frozen bundles and matching built assets, refuses an existing profile/server, and loads empty model/search keys. It records actual per-line readiness, verified ETA or availability reasons, and missing-model-key refusals in `evidence/worker/runtime_all_lines.json`, then stops its own process and removes its unchanged temporary profile. Existing evidence is never overwritten; pass `--out NEW_FILENAME.json` to save another check in `evidence/worker/`. This command is outside the unit suite and makes real public read-only feed requests; it performs no model inference or search.

Implementation references retrieved 2026-10-30: [Workers best practices](https://developers.cloudflare.com/workers/best-practices/workers-best-practices/), [SQLite Durable Object storage](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/), [Seoul train-position field definitions](https://data.seoul.go.kr/dataList/openApiView.do?infId=OA-12601&srvType=A). Wrangler 4.156.0 validates the configuration and generates binding types; current reference type package was `@cloudflare/workers-types@5.20261029.1`.
