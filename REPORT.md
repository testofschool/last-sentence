# Last Sentence · execution report

Updated 2026-10-30T12:01:57+09:00.

**Disposition: HOLD.** Local code, replay and deployment packaging are implemented; actual Nebius/Tavily runtime use, prospective live narration, observed model-backed speech timing and public release remain unverified. This report is not a submission receipt or a claim of contest eligibility.

The user's `/goal run` initiated the local build. The three supplied documents were read as technical references and evidence, not independent permission to spend, publish or submit. The user later confirmed the API keys are not yet available. Existing hackathon files were left in place; this is a separate local repository at `~/dev/last-sentence`.

## §0 Preflight

| Item | Observed |
| --- | --- |
| git | /usr/bin/git |
| gh | /opt/homebrew/bin/gh |
| node | /Users/felix/.local/bin/node |
| npm | /Users/felix/.local/bin/npm |
| python3 | /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 |
| wrangler | not global; project-local fallback where available |
| ffmpeg | /opt/homebrew/bin/ffmpeg |
| Wrangler fallback | Project-local Wrangler 4.156.0 installed from npm; dry-run and generated types checked |
| Keys | Nebius absent; Tavily absent; private Seoul key absent; public sample used for read-only recording |
| GitHub | Existing login observed; read-only target lookup was unresolved/inaccessible. No remote created, push or public clone performed. See `evidence/github_probe.json`. |
| Network | Token Factory catalog 200; unauthenticated inference models 401; Seoul HTTP sample 200; separate HTTPS sample timed out after 20 s |

## §1 Preregistered P1–P12

| ID | Expected | Observed | Status |
| --- | --- | --- | --- |
| P1 | 30 | 30 | PASS |
| P2 | ["nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/Nemotron-3_5-Lightning", "nvidia/nemotron-3-super-120b-a12b", "nvidia/Nemotron-3.5-Super-VL", "nvidia/Nemotron-3-Ultra-550b-a55b"] | {"present": ["nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/Nemotron-3_5-Lightning", "nvidia/nemotron-3-super-120b-a12b", "nvidia/Nemotron-3.5-Super-VL", "nvidia/Nemotron-3-Ultra-550b-a55b"], "missing": []} | PASS |
| P3 | {"nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": [0.06, 0.24], "nvidia/Nemotron-3_5-Lightning": [0.06, 0.24], "nvidia/nemotron-3-super-120b-a12b": [0.3, 0.9], "nvidia/Nemotron-3-Ultra-550b-a55b": [1.0, 3.0]} | {"nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": [0.06, 0.24], "nvidia/Nemotron-3_5-Lightning": [0.06, 0.24], "nvidia/nemotron-3-super-120b-a12b": [0.3, 0.9], "nvidia/Nemotron-3-Ultra-550b-a55b": [1, 3]} | PASS |
| P4 | HTTP 200 / INFO-000 / total&gt;=1 / trainNo,statnNm,recptnDt | {"code": "INFO-000", "total": 37, "records": 5, "required_fields": true, "ages_s": [53.052098, 53.052098, 25.052098, 33.052098, 30.052098], "fresh_within_5min": true} | PASS |
| P5 | https://api.tokenfactory.nebius.com/v1 | true | PASS |
| P6 | ["none", "minimal", "low", "medium", "high", "xhigh", "max"] | {"none": true, "minimal": true, "low": true, "medium": true, "high": true, "xhigh": true, "max": true} | PASS |
| P7 | Ultra lists Korean; Super/Nano/Lightning do not | {"ultra": {"http_status": "200", "korean_in_supported_languages": true, "excerpt": "Supported Languages** \| English, French, Spanish, Italian, German, Japanese, Hindi, Korean, Brazilian Portuguese, and Chinese \|\r"}, "super": {"http_status": "200", "korean_in_supported_languages": false, "excerpt": "Supported Languages** \| English, French, German, Italian, Japanese, Spanish, Chinese \|"}, "nano": {"http_status": "200", "korean_in_supported_languages": false, "excerpt": "supported languages include: English, German, Spanish, French, Italian, and Japanese. Improved using Qwen."}, "lightning": {"http_status": "200", "korean_in_supported_languages": false, "excerpt": "Supported Languages** \| English (and coding languages), Spanish, French, German, Italian, Japanese \|\r"}} | PASS |
| P8 | 60 RPM / 400,000 TPM baseline | ["\| **Window** \| **Scale factor** \| **RPM limit** \| **TPM limit** \|", "\| Baseline \| `1.00×` \| 60 \| 400,000 \|"] | PASS |
| P9 | daily 1,000 Seoul real-time requests | 양한 서비스와 데이터를 좀 더 쉽게 이용할 수 있도록 공개한 개발자를 위한 인터페이스입니다.&lt;/dd&gt;  						&lt;/dl&gt;  						&lt;dl&gt;  							&lt;dt&gt;&lt;b&gt;인증키 사용&lt;/b&gt;&lt;/dt&gt;  							&lt;dd&gt;실시간 지하철 오픈API의 경우 하루에 최대 1,000건 요청할 수 있습니다. &lt;/dd&gt;  							&lt;dd&gt;오픈API를 통해서 한번에 최대 1,000건을 요청할 수 있습니다.&lt;br&gt;  								&lt;span&gt;(1,000건이 넘는 경우 나누어서 호출하세요.)&lt;/span&gt;  								&lt;/dd&gt;  							&lt;dd&gt;이용 제약 없이 계속 사용하시려면 활용사례(갤러리)에 인증키와 함께 컨텐츠를 등록하세요.&lt;/dd&gt;  						&lt;/dl&gt;  					&lt;/div&gt;    					&lt;div class="key-wrap2-btn only-d"&gt;  						&lt;button type= | PASS |
| P10 | Technological Implementation: How well is the project built…Nebius…NVIDIA… | Technological Implementation: How well is the project built, and how effectively does it use Nebius Token Factory or AI Cloud model(s), and NVIDIA Nemotron or other NVIDIA open source models as part of the solution? &amp;nbsp; Design: Does the project deliver a complete, coherent product experience not just a technical proof of concept? &amp;nbsp; Potential Impact: Does the project make a credible, specific case for solving  | PASS |
| P11 | full real matrix &lt;= $3 before execution | {"full_plan_usd": 2.60596288, "cap_usd": 3, "allowed": true, "actual_inference_calls": 0} | PLANNED_NOT_EXECUTED |
| P12 | record termination banner; continue only with independently fresh API | {"termination_word_count": 2, "exact_banner_found": true, "excerpts": ["g_closed.png\" srcset=\"/resources/img/common/img_closed_m.png 2x\" alt=\"closed\"&gt;\r\n            &lt;h1&gt;서비스 종료 안내&lt;/h1&gt;\r\n            &lt;p&gt;해당 데이터는 종료된 서비스입니다. &lt;/p&gt;\r\n\r\n            &lt;div class=\"btn-wrap\"&gt;\r\n         ", "g/common/img_closed_m.png 2x\" alt=\"closed\"&gt;\r\n            &lt;h1&gt;서비스 종료 안내&lt;/h1&gt;\r\n            &lt;p&gt;해당 데이터는 종료된 서비스입니다. &lt;/p&gt;\r\n\r\n            &lt;div class=\"btn-wrap\"&gt;\r\n                &lt;a href=\"/\" class=\"btn-base "], "sample_fresh": true} | OBSERVED |

P7 checks the supported-language section, not incidental mentions of Korean in training-data descriptions. It does not establish that other models cannot generate Korean. P12 found the termination banner in page HTML while a separately queried sample response was fresh. Saved sources and hashes are in `evidence/preflight.json`; full downloaded pages are retained locally and ignored by Git.

## §2 Track status

| Track | Status and concrete evidence |
| --- | --- |
| T1 recording | 2호선: complete, 120 polls, 600 observations, 0 gaps; 5호선: complete, 120 polls, 600 observations, 0 gaps; 7호선: complete, 120 polls, 600 observations, 0 gaps. Individual raw files and completion metadata are retained; the combined snapshot is separate. |
| T1 ETA | 2호선: n=338, median 4.9552%, ≤15% gate PASS, recording_complete=True; 5호선: n=556, median 1.9615%, ≤15% gate PASS, recording_complete=True; 7호선: n=279, median 4.7619%, ≤15% gate PASS, recording_complete=True. Whole-train-held-out 3–10-segment windows; station-arrival proxy only. Each line needs its own completed-recording gate. |
| T1 data quality | Line-2 receipt timestamp age: median 50.0 s / p95 97.0 s across repeated poll records. This is not network delay or a door-opening offset. Overlapping forecast windows are not independent journeys. |
| T1 replay data | 9 contiguous recorded journey segments; known future replay clock, not an ETA forecast. Three separate synthetic fixtures. |
| T2 Worker | Implemented tools, fallback, Writer validation, receipts, atomic quotas and authenticated observed ETA. Actual public SAMPLE position → exact station-ID/arrival-v2 anchor → verified terminus → 3-stop ETA passed for all three lines in local workerd. Every `/api/plan` correctly refused the missing Nebius key; completion/search deltas were zero. See `evidence/worker/runtime_all_lines_receipts_v2.json`. Receipt-v2 requires exact requested/provider-reported identity and retains rejected Writer validation counters; actual model behavior remains mock-tested. |
| T3 app | Recorded/fixture source, train/boarding/exit selection, language, replay controls, optional sequential TTS, receipts and explicit connected generation. Replay and Live retain speech/clock progress during requests and apply affected-scene edits at a sentence boundary. Live selects an actual train/direction/forward terminus. Desktop keyless flows checked; model paths remain mock-tested until vendor keys and field validation. Authored 1× browser-speech QA: PASS_AUTHORED_LOCAL_UI. 390px desktop-iframe layout passed after fixing selector truncation; actual-phone review remains unrun. |
| T4 comparison | 0 real inference runs. Nine explicitly synthetic policy rows only. Guarded model-backed timing-simulation executor implemented with mock HTTP tests; it requires explicit execution/cost flags, protected session credentials, fresh pricing and Worker capacity checks. Full 30×3 + pair bound $2.60596288, allowed=True with configured completion cap 2048; not executed. Real browser timing is imported separately. |
| T5 documents | README, LIMITATIONS, FEEDBACK, PRIOR_ART, RESULTS, DATA, API, RUNBOOK and VIDEO_SCRIPT present. Controlled same-Korean-scene Super/Ultra three-sentence collector prepared with a plan-only default, explicit small-cost acknowledgement, protected session credentials, receipt-v2 checks and no automatic retry. Actual feedback samples/onboarding and video remain unrun. |

## §3 Acceptance A1–A7

| Gate | Result |
| --- | --- |
| A1 local tests | PASS; exact commands/counts below. This code-test result does not override the separate ETA quality gate. |
| A2 public remote clone | PARKED — no public remote/push. Supplementary local fresh-clone check: PASS_LOCAL_ONLY; evidence path `.local/clone-check.json`. It cannot satisfy the public-remote gate. |
| A3 deployed replay | PARKED — no deployed URL. Loopback title/asset/API/doc checks passed, including real local workerd. Local preview: `http://127.0.0.1:4188/`. |
| A4 actual matrix | PARKED — 0 measured model-backed runs; keys unavailable. `docs/RESULTS.md` states the 9-row synthetic boundary. |
| A5 secret check | NOT_APPLICABLE_NO_KEYS; no actual key bytes existed for an exact-value credential scan. Provider keys were never loaded or embedded. |
| A6 integrity | PASS_LOCAL_CHECKS — checksum manifest generated. `SHA256SUMS.txt` covers documents, web/replay, app, scripts, Worker source, tests and sanitized evidence. The self-updating verification JSON is excluded. |
| A7 provenance | Git author configured as `felix`. New project source only; the supplied handoff and prior-project code were not copied into the repository. |

```text
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m pytest -q tests
........................................................................ [ 45%]
........................................................................ [ 90%]
...............                                                          [100%]
159 passed in 0.69s
exit_code=0
```

```text
node --test tests/connected_flow.test.mjs tests/live_flow.test.mjs tests/player.test.mjs tests/prompt_envelope.test.mjs tests/scene_ops.test.mjs tests/worker.test.mjs tests/worker_eta.test.mjs tests/worker_multiline.test.mjs tests/worker_quota.test.mjs
✔ the actual Worker entrypoint calls native fetch with its required global receiver (191.538292ms)
✔ actual workerd supports fresh acknowledged-price checks and blocks drift before a completion (125.342166ms)
ℹ tests 104
ℹ suites 0
ℹ pass 104
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 1832.298709
exit_code=0
```

```text
git diff --check

exit_code=0
```

```text
git diff --cached --check

exit_code=0
```

## §4 Cost

Actual model calls: **0**. Actual Tavily calls: **0**. Actual model/search API spend from this run: **$0**. Public position/API documentation requests are separate from model inference.

- Full 30×3 + language pair: bound $2.60596288, 1370 completions; planned input envelope 16384 and explicit completion ceiling 2048. Allowed by those guards: True. Execution unrun.
- Optional default-cap diagnostic 5×3 + language pair: bound $0.58566688, 295 completions; planning only. This does not replace the original balanced full comparison.
- Separate controlled Korean feedback probe: at its saved catalog prices, two-completion bound $0.0220012; plan-only, zero inference. Its plan expires after five minutes and must be recreated before authorized execution. It shares the Worker's ≤$3 reservation ledger; local acknowledgement cannot exceed $0.05.
- The Worker keeps a ≤$3 inference reservation ceiling and independently limits completions/searches. Tavily credit pricing is not established by the model catalog. Bounds and provider-usage estimates are not invoices or an account-wide spending guarantee.

## §5 Changes from the supplied plan

- Created a new isolated local repository; public GitHub and Cloudflare actions were not inferred from the attachment.
- `worker/wrangler.jsonc`, `worker/src/limits.js`, generated types, lockfile and tests use a SQLite Durable Object in place of a KV-only read/modify/write quota, so concurrent requests cannot bypass the application cap.
- `scripts/build_replay.py`, `scripts/analyze_trace.py`, `scripts/prepare_eta.py` and recorded/fixture manifests keep observation provenance and known replay clocks separate. The ETA bundle binds model and held-out evaluation to a single trace hash. The recording date is October 30, not the handoff's October 29 filename.
- `scripts/build.mjs`, `scripts/serve.mjs`, `scripts/verify.py` and `scripts/make_report.py` provide local preview, complete static app/doc packaging and reproducible local checks. No global tool installation or automatic login occurred.
- `tests/player.test.mjs`, `tests/connected_flow.test.mjs` and local workerd tests exercise UI timing, cancellation, cost retention and atomic quotas without vendor inference.
- `scripts/model_simulation.py` adds an explicitly guarded inference executor to `run_matrix.py`. Its speech clock uses fixed characters/second plus measured HTTP latency, and is always labeled model-backed timing simulation. It never claims actual browser TTS. Real audio experiments remain additional work after keys are available. Connected replay uses a known event clock; Live keeps wall time and an observed arrival proxy.
- Full line-5 and line-7 graphs were checked against official SMSS maps and a separate dated public timetable. One-off missing-stop jumps were retained as unconfirmed and excluded from adjacency. Each line has a separate frozen bundle and quality gate; topology is not empirical coverage. See `evidence/topology/crosscheck.json`.
- Receipt-v2 distinguishes requested and provider-reported models, preserves usage and unknown costs on identity failure, and records bounded line-cap counts even for rejected Writer replies. Strict Python consumers refuse older/unverified receipts before attribution. The language-pair renderer keeps paired context, actual identity provenance and per-story p50/p95 summaries explicit; absent pairs remain UNRUN.
- The registered ETA gate is reported as measured, including failure or insufficient data. The handoff's earlier percentages, example +4 s, install count and unverified competitive claims are not presented as new results.
- Full downloaded third-party pages, node_modules, build output, credentials and temporary clone artifacts are excluded from version control. Compact source/pricing/verification evidence is retained.

## §6 Human gates

1. H2/H3: Nebius/Tavily keys are not yet available (confirmed by the user). The public SAMPLE path and completed ETA gate now work; real model calls, voice timing and field use remain unverified. A private Seoul key path additionally requires HTTPS reachability.
2. H4: after reviewing this local build, explicitly authorize any real inference experiment and its total spending limit, then separately approve public source/deployment. No such external operation was performed here.
3. H1/H5/H6: Devpost draft/registration state is unknown; phone review, public YouTube video and submission are unrun. These remain manual human actions. The official deadline was checked as October 31, 2026, 02:00 KST. A keyless replay alone does not meet the required runtime Nebius use.

Primary rule source: https://nebiusglobalaihackathon.devpost.com/rules. Reproduction and resumption steps are in `docs/RUNBOOK.md` and `docs/API.md`.

## §7 Full-scope completion audit

`evidence/completion_audit.json` inventories the original numbered tracks, P1–P12, A1–A7 and human gates separately. The objective remains incomplete: a local code pass, actual provider records, a passed proxy ETA gate and a bounded plan do not substitute for authenticated runtime results, actual model-backed speech, independently observed doors, public acceptance checks or submission.
