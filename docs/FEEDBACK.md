# Feedback draft · observed October 30, 2026 KST

This is a local draft, not a feedback submission. Actual authenticated inference has not run.

| Question | Observation |
| --- | --- |
| Key to first Nemotron reply | UNMEASURED; no Nebius key was present |
| Public model discovery | HTTP 200; 30 model entries; all 5 preregistered Nemotron IDs present |
| Public inference reachability | `/v1/models` returned HTTP 401 without a key; no authentication success is implied |
| Price endpoint | All four preregistered input/output prices matched the public catalog; useful for planning a cost bound |
| `reasoning_effort` accepted by Lightning/Super/Ultra | UNMEASURED; documented enum verified, runtime acceptance not tested |
| Lightning tool calls | UNMEASURED; tool loop and fallback paths tested with mocked responses only |
| Rate-limit headers | UNMEASURED; no authenticated completion response |
| Korean Ultra vs Super, same scene | UNRUN; no model-generated sample text is presented |
| Sentence-length obedience | UNMEASURED; application validates caps but cannot infer a model's compliance rate from mock responses |
| Tavily usefulness | UNMEASURED; no Tavily key or runtime search |

One concrete documentation concern: the model catalog identifies inference IDs, prices and model-card links, while supported languages live in the cards. This prototype records those sources separately so a documented language list is not confused with measured generation quality.

A complete feedback version should include the measured interval from observed key readiness to the first verified reply, returned headers with credentials removed, the identical Korean prompt and three-line Super/Ultra replies, per-attempt schema failures and sentence-length counts, token usage and per-model latency. The separate EN/Super–KO/Ultra trace pair belongs in the results table. Retain errors and retries in the denominator.

Intended next use: keep a fast planning model separate from the story-writing model so each decision and its token cost can be inspected. Whether that separation improves timing or cost still needs the same-trace comparison.


## Controlled Korean Super–Ultra collector · PREPARED, NOT RUN

`scripts/collect_feedback.py` prepares a separate, same-Korean-scene comparison: Super and Ultra each receive the exact same scene and three-line contract. This is distinct from T4's English-Super / Korean-Ultra trace pair. Each completion is bounded to 16,384 input tokens, 180 output tokens, three nonempty lines, 40 Unicode characters per line, and 120 total characters. A successful collector row means the request, identity receipts and mechanical text constraints passed; Korean quality still requires human review.

The public-catalog planning artifact is [feedback-plan.json](../evidence/feedback-plan.json). It made **zero inference calls**. At its recorded prices, the conservative two-completion bound is **$0.0220012**. A plan expires after five minutes; create a fresh plan immediately before any authorized execution. The collector never retries a completion automatically and never overwrites an existing output. Choose unused filenames for each new attempt.

Prepare the separate Worker session token in `.local/worker-session` with mode `600`; it must be the configured `LIVE_ACCESS_TOKEN`, **not** a Nebius, Seoul, or Tavily vendor key. The collector refuses known vendor-key paths, symlinks, and vendor-key hard links without reading their bytes. Replace the Worker URL below with your own protected endpoint.

```sh
mkdir -p .local
chmod 600 .local/worker-session
python3 -I scripts/collect_feedback.py \
  --worker-url https://YOUR-LAST-SENTENCE-WORKER.workers.dev \
  --output .local/feedback-plan-1.json
```

Optional: only when key readiness is actually observed, explicitly create a new local marker. This checks that `~/.nebius_key` is a nonempty regular file; it never opens the key, reads its bytes, or infers creation time from file timestamps.

```sh
python3 -I scripts/collect_feedback.py \
  --mark-key-ready .local/feedback-ready-1.json
```

The following is a future execution command, **not a test performed in this build**. It requires explicit cost acknowledgement, the protected session token, matching fresh prices, the Worker receipt-v2/pricing/comparison capabilities, at least two remaining completion slots, and enough of the shared application reservation budget of at most $3. The local cap may not exceed $0.05; `$0.03` covers the current saved bound. The Worker freshly checks each acknowledged price before dispatch. A price/identity/usage failure or unknown request outcome stops further completions.

```sh
python3 -I scripts/collect_feedback.py \
  --execute \
  --plan .local/feedback-plan-1.json \
  --worker-url https://YOUR-LAST-SENTENCE-WORKER.workers.dev \
  --session-token-file .local/worker-session \
  --ack-cost-cap-usd 0.03 \
  --key-ready-marker .local/feedback-ready-1.json \
  --max-runtime-s 180 \
  --output .local/feedback-run-1.json
```

Omit `--key-ready-marker` if no genuine marker exists. Readiness-to-reply time then stays **UNMEASURED**. Even with a marker, the metric covers local file-presence observation to the first provider-identity-verified Worker reply; it does not measure signup, key creation, or prove which local key file the Worker used. Mock transports always remain labeled mocks and never establish an onboarding interval.

The collector retains successful three-line samples, per-completion requested/reported IDs and exact-match status, usage, usage-based price estimates, requested-rate estimates separately when identity is unverified, validation counts/failures, rate-limit headers, latency, errors and unknown costs. Unverified output is discarded rather than attributed to a model. Reported prices and usage are cost estimates, not billing receipts. No controlled Super/Ultra sample, actual runtime acceptance, Korean-quality judgement, or onboarding measurement has been added to the observations above.

For future sentence-length rates, include every attempt in the attempt/cost tally but use only rows with `validation_countable: true` in the sentence denominator. Successful text is independently recounted. Rejected summaries are counted only after their fixed protocol, counter arithmetic and verdict are validated; missing or inconsistent summaries are explicitly excluded rather than assigned a fabricated zero. Their raw receipts, errors and costs remain available.
