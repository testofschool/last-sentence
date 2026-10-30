# Last Sentence · 마지막 문장

A story intended to finish at your subway stop. Select a destination, follow the sentence stream, and inspect how the available time changes the story.

**Current build, October 31, 2026 KST: public recorded/fixture replay, a protected Worker API with verified real Nemotron responses, and an offline model-backed comparison with one retained output rejection.** Default replay uses authored text and needs no account or key. Connected generation requires an application session token and makes billable requests. Recorded replay knows the provider timestamps in advance; it does not establish prospective train, browser-speech or door-opening accuracy.

[Open the demo](https://last-sentence.felix-market-radar.workers.dev) · [Public MIT source](https://github.com/testofschool/last-sentence) · [UI specification](docs/UI_SPEC.md). The Worker is the canonical same-origin UI/API deployment. [Cloudflare Pages](https://last-sentence.pages.dev) remains a static keyless mirror.

```sh
cd ~/dev/last-sentence
npm run dev
```

Choose Replay, a source, train journey and destination, then start. Try ×16 to inspect the ending; pause, scrub, switch language or restart. Audio is optional and browser voices vary. Keep the screen open. The local preview binds to `127.0.0.1`, loads no provider credentials and keeps its live API disabled.

## Which model does what

| Component | Model/service | Observed scope |
| --- | --- | --- |
| Conductor | `nvidia/Nemotron-3_5-Lightning` on Nebius Token Factory | Real planning responses and receipts observed; tool execution and failures are retained per request |
| English Writer | `nvidia/nemotron-3-super-120b-a12b` | Real generated text and validation receipts observed; rejected outputs remain failures |
| Korean Writer | `nvidia/Nemotron-3-Ultra-550b-a55b` | Real controlled probe, timing pair and connected browser generation observed; Korean quality remains unmeasured |
| Neighbourhood fact | Tavily | Optional source URL path; real search remains UNRUN |
| Train position | Seoul real-time subway sample API | Frozen observations recorded separately from synthetic fixtures |

The model cards were checked on October 30, 2026 KST. Ultra explicitly lists Korean among its supported languages; omission from another card does not prove inability. In the controlled same-Korean-scene probe, one request per Writer produced six inspected nonempty lines, all within the 40-Unicode-character cap. This **6/6 mechanical observation** is not a language-quality score, model ranking or general obedience rate.

The prepared Live controller requires a fresh verified train-arrival anchor, actual train/direction, forward exit and a passing per-line ETA gate. Wall-clock time continues during requests; rewritten text waits for a sentence boundary. Real rider operation, model-backed Live narration, browser TTS and door timing remain unvalidated.

## Run and inspect

Node.js 22+ and Python 3.10+ are used; the frontend has no package dependencies. The Python tests require pytest.

```sh
npm test
python3 -I scripts/preflight.py
python3 -I scripts/verify.py
```

Preflight makes public read-only requests and checks key-file presence. It does not install tools, read key bytes, spend credits or deploy. `verify.py` tests code, checks local credential bytes without printing them, and hashes deliverables. `npm run build` prepares `dist/` with app assets and linked documents.

“Generate with connected models” is an explicit optional billable action. It uses the configured Worker and a separate **application session token**, never a provider key in the browser. The frontend generation flow and offline Worker measurements have separate evidence: authenticated Worker responses do not by themselves prove that a browser journey or live rider session completed. See [API setup](docs/API.md) and [limitations](docs/LIMITATIONS.md).

## Evidence and current execution boundary

| Evidence | Meaning |
| --- | --- |
| 3 × 40-minute recordings | 600 actual sample observations per line, 1,800 total and no gap records; station-arrival proxy data |
| 3 fixture journeys | Explicitly synthetic line 2, 5 and 7 scenarios |
| Verified real Nemotron receipts | 93 exact-ID responses including rejected outputs; $0.01405146 known usage/catalog estimate, with missing prior costs separate |
| Controlled Korean probe | One request per Super/Ultra; six of six inspected lines within 40 characters; semantic quality unmeasured |
| [Reduced attempt 07](evidence/model-reduced-20261031-07.json) | All17 planned slots visited:16 scored,1 retained output rejection;4/5 fully paired windows; sentence-replan0/5 within±30seconds |
| Full 30×3 comparison | **UNRUN**: the handoff's before-19:30 KST condition was missed |

The reduced comparison finished with one retained model-output failure. Earlier versions and interrupted05 remain separate. Failed slots receive no invented score; missing usage/cost is not replaced by zero. See [final runtime audit](evidence/runtime-live-audit.json), [results](docs/RESULTS.md) and [feedback](docs/FEEDBACK.md).

The [final runtime audit](evidence/runtime-live-audit.json) records **93 exact-ID provider responses**, including rejected outputs, with a known usage/catalog subtotal of **$0.01405146**. The two earlier401 POST costs and interrupted05 outcome remain unknown; the account invoice is unverified. [reduced attempt 07](evidence/model-reduced-20261031-07.json) visited **17/17 slots:16 scored,1 known output rejection,0 unstarted**. Sentence-replan scored **0/5 within±30seconds**; this is fixed-character-rate simulation, not browser speech or doors. The connected capture contains **4 provider completions grouped into2 UI service events**.

The direct authorization is **$3 total**. Three direct smokes retain a conservative **$0.002961 outside-Worker reserve**; the deployed Worker portion is **$2.997039**, so the two bounds sum to $3. These are reservation limits, not an account invoice. Known usage/catalog estimates are separate from the unknown costs of the two earlier 401 requests and the interrupted attempt-05 dispatch. The same Durable Object ledger is retained across redeployments.

The checked-in configuration keeps `ENABLE_LIVE=false` and its default completion allowance. The current protected deployment uses explicit overrides; repeat them for an authorized redeploy rather than silently changing the recorded profile:

```sh
npx wrangler deploy --config worker/wrangler.jsonc \
  --var ENABLE_LIVE:true --var LIVE_BUDGET_USD:2.997039 \
  --var LIVE_MAX_COMPLETIONS:2048
```

Do not reset the Durable Object ledger to obtain fresh capacity. Refresh prices and inspect authenticated remaining reservations before any further experiment. The historical full-plan bound of $2.60596288 at saved catalog prices is a planning artifact, not a completed experiment or current spending total.

[Prior art](docs/PRIOR_ART.md) includes systems that already adapt stories to journeys; no novelty or superiority claim follows from this prototype. [Runbook](docs/RUNBOOK.md) separates the remaining work from the released build. Video publication, messaging and Devpost submission remain human actions outside the current execution authorization.

## 한국어

기본 화면은 기록된 역 관측 시각 또는 합성 시간표와 사람이 쓴 문장을 재생합니다. Worker에서는 유효한 키로 실제 Nemotron 응답을 확인했고, 별도 앱 세션 토큰으로 보호된 모델 호출이 가능합니다. 공급자 API 키는 브라우저나 Git에 넣지 않습니다. Pages는 키 없는 정적 미러입니다.

축소 비교 07은 예정17건을 모두 시도해16건을 채점하고1건의 출력 탈락을 보존했습니다. 재계획 방식은±30초 이내0/5였습니다. 실제 모델 응답93건의 알려진 비용 추정은$0.01405146이며, 이전 비용 미반환3건은 별도입니다. 전체 30×3 비교는 19:30 실행 조건을 지나 미실행입니다. 한국어 동일 장면 실험은 모델별 1회, 총 6줄이 40자 이내였다는 기계적 관측이며 한국어 품질이나 우열을 입증하지 않습니다. 문자 속도 기반 타이밍 시뮬레이션을 실제 음성·열차·문 열림 정확도로 해석하면 안 됩니다.

MIT · felix · 2026
