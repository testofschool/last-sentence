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

A complete feedback version should include the measured interval from key readiness to first successful response, returned headers with credentials removed, identical English/Korean prompt text and provider replies, per-attempt schema failures and sentence-length counts, token usage and per-model latency. Retain errors and retries in the denominator.

Intended next use: keep a fast planning model separate from the story-writing model so each decision and its token cost can be inspected. Whether that separation improves timing or cost still needs the same-trace comparison.
