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


## §0-v2 Proposal preflight · 2026-10-30T15:59:48.649523+09:00

The current user's request is `/goal run` with three supplied files. The handoff's quoted earlier authorization is documentary content, not independently confirmed user authorization in this chat. This continuation completed local, reversible preparation. It made no paid API call, public push/deployment, message, video or Devpost submission. GitHub/Cloudflare publication and an inference cap require a direct user instruction; inference additionally requires the missing Nebius credential.

- Source repository web snapshot: `9965c12dee396fbf763a21504428a8b859b6fbc0`; repository initially clean with no remote.
- `node`, `npm`, `python3`, `gh`, `ffmpeg`, `pdftotext`, `pdffonts`, `pdftoppm`: 8/8 found. Python Playwright and pypdf import: 2/2. Initial Playwright browser launch failed with `Executable doesn't exist ... chromium_headless_shell-1208 ... chrome-headless-shell`; `python3 -m playwright install chromium` completed, after which captures and PDF generation worked. Existing Python packages were reused.
- `~/.nebius_key`: absent. `~/.tavily_key`: absent; `tavily_ok=false`. No key bytes read, transmitted or printed.
- `gh auth status`: exit 0. Installed Wrangler `whoami`: exit 0; optional k2.read/write scope warning retained in private log. Build: exit 0. Worker deploy dry run: exit 0. No external resource was created.
- Source PDF SHA-256: `90e08072c24f20674e838b3ddaa74fa1f2cc42a1bdb92555d330905db3328e98`. It is a DUMMY-image smoke sample, not a deployed-service capture. Original PDF and ZIP are unchanged.
- Private artifact/evidence root: `/Users/felix/dev/last-sentence-proposal/`. Contact defaults and original package remain there, outside this repository.

### R1–R8 expected versus observed

| ID | Expected | Observed in v2 |
| --- | --- | --- |
| R1 | Python 159, Node 104; total 263 | Re-run: 159 + 104 = 263 passed; 0 failed, Node 0 skipped; both exit 0. |
| R2 | Per-line ETA medians 4.9552%, 1.9615%, 4.7619% | Existing frozen results match; not re-recorded/re-estimated. Proposal rounds the range to 1.96–4.96%, labels station-arrival proxy and overlapping windows. No door/voice result. |
| R3 | Saved Nano/Lightning 0.06/0.24, Super 0.30/0.90, Ultra 1/3 USD per million in/out | Saved pricing only; no fresh pricing verification or inference. Refresh before any authorized execution. |
| R4 | Authenticated Lightning smoke HTTP 200, nonzero usage, matching model | UNRUN: credential absent and no direct spend instruction. No substitute mock receipt. |
| R5 | Reduced bound $0.58566688; full $2.60596288; total cap $3 | Existing plan bounds only; actual calls 0, spend $0. Reduced/full sequential worst-case sum exceeds cap. Default Worker completion allowance 300 fits reduced 295 only before other calls; full 1370 requires explicit configuration and residual-budget check. |
| R6 | 2 A4 pages, zero residue/forbidden/widgets/JS, embedded fonts, intended metadata, at least 3 images | PASS 9/9: 2 pages 595.0×841.9 pt; 0 placeholder braces; 9 forbid tokens checked, 0 hits; 0 widget/JS/encryption/embedded files; 75 embedded font resources; 3 image XObjects; title/author match. Missing-key exact scan is N/A, not a tested secret value. |
| R7 | Supplied sandbox smoke: 2 pages, 3 links, 3 images, 21 fonts | Historical package claim only. New local draft: 0 links, 3 images, 75 fonts; unobserved public URLs removed rather than represented as live. |
| R8 | Desktop 1440×900, mobile 390×844 at DPR 2 | Captured 2880×1800 and 780×1688 PNGs. Source is recorded replay, authored story, ×16, 2호선 신도림→합정. Arrival-state captures are scrolled; mobile viewport naturally crops the adjacent story card. |

## §3-v2 UI and document checks

- UI spec initial gate: 1 FAIL / 1 WARN; source-grounded rationale for the existing eyebrow text was added. Final: 0 FAIL / 1 WARN (G6 availability axis N/A). CSS appendix equals source exactly; 5/5 HTML/CSS/JS/JSON runtime inputs independently verified. No web source changed.
- First viewport at 1440×900: 35 visible objects, 19 RGB-merged UI colours, 2 font families. At 390×844: 22 objects, 11 colours, 2 families. V4 PASS on both for exact strings `Last Sentence` and `Replay`; no `who` string specified. V1–V3 are UNMEASURED against budgets because no budgets were declared; these numbers are diagnostics, not quality ratings.
- Hook gate desktop: H1 FAIL (fill 0.031 versus default 0.25; largest type ratio 0.056667 versus 0.13); H2 FAIL (0 full-frame events); H3 reports largest media ratio 0.00025 and type 51 px; H4 FAIL (10.07 s gap versus 4 s). No environment stall/load/page errors. Existing app remains unchanged; failures are recorded for the designer, not hidden or reclassified as PASS. A source-spec pass does not mean the UI passes the hook test.
- Composition diagnostic: K1 0, K2 0 radii, K3 0, K5 order-run 2; K4/K6 WARN. This parser reads inline HTML styles and does not measure external style.css, so zeroes do not mean the app lacks those properties.
- Actual capture page errors: 0 desktop / 0 mobile; horizontal overflow false for both. Receipts panel shows 0 API CALLS. Required ≥3 real-call receipts is NOT MET; no fake calls were inserted.
- PDF gate full JSON: private `evidence/pdf-gate-initial.json`; complete rendered pages: `out/page-1.png`, `out/page-2.png`. Original PDF pixel-isolation: N/A, because this is a new proposal, not a form edit. Visual/DOM/provenance audit is retained separately.

## §8-v2 Track outcomes and resumption

| Track | Outcome |
| --- | --- |
| T-K real Nemotron | PARKED: H1 absent key; direct spend instruction also missing. Reduced/full/probe/feedback regeneration not executed. Existing RESULTS/FEEDBACK remain truthful. |
| T-P public release | PREPARED, NOT PUBLISHED: H3 authentication passes; awaiting direct public-source/deployment instruction. No remote, public URL, public clone or signed-out public HTTP check. Secret-pattern scan: 147 tracked files plus local patch history, 4 patterns, 0 hits; exact-value scan N/A (keys absent). |
| T-S screenshots | LOCAL CAPTURES COMPLETE with sidecars; desktop/mobile/first viewport/empty receipts. ≥3 real calls prerequisite remains unmet. Captions contain `로컬 미리보기` and `예시값 · 실측 아님`. |
| T-F UI spec | `docs/UI_SPEC.md` complete, pinned to current web source. Hygiene gate 0 FAIL/1 WARN. Existing-page hook gate FAIL remains open for designer review. No design changes claimed. |
| T-D proposal | LOCAL REVIEW DRAFT COMPLETE, 2 pages, structural gate PASS 9/9. Generic designer salutation; supplied contact preserved. No fabricated public links, recipient, inference result or door-opening guarantee. Human visual acceptance and sending remain unperformed. |

Public URLs/HTTP results: none observed; public checks UNRUN. Local preview `http://127.0.0.1:4188/` returned HTTP 200 and title `Last Sentence`; `/api/status` reports `replay-only`, `inference_enabled=false`. This URL works on this machine only.

Actual model/Tavily calls: 0 / 0. Actual model/search spend: $0. PDF SHA-256: `64f5c39017977fc0a9a64aec70fdc52f5b3b1aae8dc2e44cf8975cc9e81da108`.

Release configuration review: merely uploading NEBIUS_API_KEY does not enable inference. The existing Worker requires `ENABLE_LIVE=true`, a strong application `LIVE_ACCESS_TOKEN` and its Durable Object. Provider keys remain server-side. Worker already serves the app/assets same-origin. Separate Pages hosting additionally requires explicit frontend Worker URL and exact `ALLOWED_ORIGIN`; public keyless replay alone does not satisfy runtime contest use. Configure and review these only within approved scope. Do not expose the protected session token in public assets.

Files changed in repository: `docs/UI_SPEC.md` (new), `REPORT.md` (append only), `SHA256SUMS.txt` (regenerated to cover new documentation). Generated ignored `dist/` and Worker dry-run output refreshed. Private proposal files include source package, capture/preparation/finalization scripts, fill + provenance, derived local template, screenshots + sidecars, evidence logs and final PDF/renders. Playwright Chromium cache was installed. No changes in the unrelated hackathon workspace and no application source/behavior edits.

The overall handoff remains incomplete pending external authorization, credentials, observed public acceptance and real-runtime evidence. H5 sending, video and Devpost submission were not requested as actions in this chat and have not been performed.


## §9-v2 Direct authorization and public release continuation

The user directly approved public GitHub + Cloudflare publication and real Nebius inference with a total cap of $3 in this chat. This supersedes the pending-authorization status in the timestamped §0-v2/§8-v2 local-preparation snapshot. Nebius/Tavily key files are still absent at release start; no runtime inference is claimed. Public release is now being executed and verified.


## §10-v2 Observed public release and final proposal · 2026-10-30T16:08:31.383637+09:00

Publication is complete for the current keyless build. This supersedes earlier pending-publication entries, which remain historical snapshots. Actual inference is still blocked only by the missing Nebius credential; the user's direct $3 total inference authorization remains valid.

| Acceptance | Observed evidence |
| --- | --- |
| Public source | https://github.com/testofschool/last-sentence ; public, MIT, default branch main. First tested public commit `a8bea171fb9a1d1f2025bc6778c231ab8345aec8`. |
| Canonical service | https://last-sentence.felix-market-radar.workers.dev ; signed-out curl HTTP 200, title Last Sentence. UI and `/api/*` share the Worker origin. |
| Pages mirror | https://last-sentence.pages.dev ; signed-out HTTP 200, static keyless mirror. API calls use the canonical Worker when explicitly connected. |
| Public status | `/api/status`: HTTP 200, mode `replay-only`, inference_enabled false, receipt-v2; `/api/position?line=2호선`: HTTP 200, mode `replay-forced`. This is the disabled-path JSON contract, not a successful live-position/model claim. |
| Served content | Root HTML, style.css, app.js and docs/UI_SPEC.md matched local source byte-for-byte on Worker and Pages: 8/8 comparisons. Later documentation-only publication is checked separately. |
| Public clone | New unauthenticated HTTPS clone with credential helper/auth-token environment disabled. Local HEAD, public HEAD/main and clone HEAD all matched `a8bea171`; npm ci/build exit 0; Python159 + Node104 passed, 0 failed/skipped, clone clean. No application/test source changed afterward. |
| Public capture set | Actual Worker URLs, 2호선 신도림→합정, recorded replay ×16, authored text, sound off. Desktop1440×900 and mobile390×844 at DPR2; 4 PNGs with 4 sidecars including exact file hashes. Browser errors0 and horizontal overflow false. Empty Receipts panel remains0 calls; ≥3 real-call condition is unmet. |
| UI contract | Source-derived spec unchanged, spec gate0 FAIL/1 WARN. Existing-page hook failures H1/H2/H4 remain open design findings; no UI redesign was performed. |
| Private proposal | 2 A4 pages, 3 public screenshot images, 3 actual links, 75 embedded font resources, gate9/9; all three PDF link destinations HTTP200; complete render/DOM review found0 overflow/footer overlaps. Model calls0, spend$0 and `예시값 · 실측 아님` captions retained. |

The Pages CLI initially delegated `pages project create` to a Worker deployment. The subsequent Pages upload reported `The Pages project "last-sentence" does not exist.` Installed Wrangler source confirmed a direct-project-create opt-out; `pages project create ... --force` created the specified Pages project without replacing any existing site, then ordinary `pages deploy ../dist --project-name last-sentence --branch main` succeeded. Worker configuration was ignored for the static Pages upload, as expected. Both resulting public services were independently probed. Logs are retained privately; no account identifiers or credentials were copied into public evidence.

The default Python HTTPS client failed its local certificate-chain lookup during the first unauthenticated probe. Normal `curl` certificate validation and Playwright HTTPS navigation succeeded; no TLS-verification bypass was used for publication acceptance or captures. The failed Python probe is retained separately and not reported as a server TLS failure.

Final private PDF SHA-256: `50d110c3d2089e989c672298163aa00006c317f77c1e47fe9a0aa61b5c9e3489`. PDF, contact line, fill/provenance, source ZIP, screenshots, page renders and designer review ZIP stay under `/Users/felix/dev/last-sentence-proposal/`; none was added to the public repository. Original supplied out.pdf remains unchanged.

Additional document changes in this publication: README.md, docs/API.md, docs/LIMITATIONS.md and docs/RUNBOOK.md now link the actual services and preserve runtime UNRUN; evidence/public_release.json records compact public evidence. REPORT.md is append-only; SHA256SUMS.txt covers the new source/document snapshot. No web/, Worker behavior or test implementation changed.

Remaining requirements: authenticated Lightning smoke; reduced matrix; conditional full matrix within residual time/cost/call allowance; controlled Korean feedback; receipt-derived results/feedback; actual-call Receipts capture and measured proposal update. Each still requires the Nebius key. Optional Tavily key is absent (`tavily_ok=false`). No model credentials, promo balance or runtime success are inferred from publication. The full handoff goal remains incomplete. PDF sending, video and Devpost submission remain human actions and were not performed.


## §11-v2 Credential entry and observed authentication failure · 2026-10-30T07:36:39.301673+00:00

The user entered a credential through a native hidden-answer macOS dialog. An initial whitespace-containing entry was not stored; a later entry created the local regular credential file with mode600. The first single, bounded Lightning smoke returned HTTP401 at 2026-10-30 16:26:30 KST (error-response latency1427.02ms), with provider model null and usage null. After explicit user replacement through a second hidden-answer dialog, a separate single smoke returned HTTP401 at16:30:44 KST (879.32ms). No unchanged automatic inference retry occurred. The official Bearer header and Token Factory endpoint were checked against current primary documentation.

Two additional read-only `/v1/models` authentication diagnostics also returned401. One used native `/usr/bin/curl -q` with default user config disabled. A synthetic loopback check confirmed exact Authorization-header serialization; it does not prove what the provider received or diagnose whether the cause is revocation, account, project or credential selection. The provider rejected authentication; the reason beyond its error text is unverified. The official Token Factory API-key management page was opened for human account/project checking.

Current result: completion-POST requests2, read-only authenticated GET diagnostics2, successful model responses0, provider usage unavailable. Actual usage-based cost remains null/unconfirmed and must not be replaced with$0. Model-backed matrix, Korean feedback probe, first successful-reply timing, tool support, sentence-length rates, real model Receipts captures and measured proposal results remain UNRUN. This is credential gate H1 failure, not a completed inference experiment.

The approved total inference limit remains$3. Each bounded direct smoke retains a987-microUSD conservative allowance at the freshly checked public Lightning rates; cumulative outside-Worker allowance1974microUSD. A future enabled Worker must therefore have a budget no higher than$2.998026 before any further direct smoke; any additional smoke allowance reduces it again. This is reserved worst-case headroom, not measured spend. No provider credential or session credential has been uploaded to Cloudflare, and deployed inference remains disabled with the original default$3 ceiling. The existing Worker/DO ledger was not reset, replaced or used for model dispatch.

`evidence/nebius_auth_check.json` records sanitized numeric outcomes; `evidence/model-prices-live-20261030.json` retains the fresh public planning prices separately from the original snapshot. README, API, LIMITATIONS, RUNBOOK and FEEDBACK now distinguish the current present-but-rejected local key from the historical pre-key state. Original public-release checks and263 local/public-clone tests remain valid for unchanged application/test code. No new model-quality or invoice claim follows from this status update.

The private designer proposal was updated to0 successful model responses and2 HTTP401 attempts, with usage/cost unreported and runtime comparison UNRUN. Gate9/9:2A4 pages,3images,3public links, no secret hits/widgets/JS/unembedded fonts; full render/DOM review found0overflow/footer overlaps. Private final PDF SHA-256:`422780bae856630fcd8faf2f50cd59626d382a58c825d63a424f3f894aaac905`. Previous public-link PDF and original supplied PDF were preserved. Contact/PDF/secret files remain outside the public repository. Hook H1/H2/H4 failures remain open design findings.

Remaining external input: a Token Factory credential accepted for the intended project. Direct publication and total$3 execution approvals remain valid; no repeat approval is required. The handoff goal remains incomplete. No video, message, designer sending or Devpost submission was performed.
