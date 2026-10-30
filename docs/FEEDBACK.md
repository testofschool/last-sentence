# Feedback draft · observed October 31, 2026 KST

This is an evidence-backed draft, not a feedback submission. Token Factory authentication and actual Super/Ultra Writer responses have now been verified. The observations below cover the direct smokes, controlled Korean probe, reduced runs 01–07 and one completed connected-browser capture cycle, including all recorded failures and one interrupted unknown outcome. The reduced evaluation completed with one retained model rejection; its clock is simulated. Invoice cost remains unknown, and no speech/door-opening performance is claimed. Real inference remains directly authorized within the existing **$3 total** limit.

## Authentication and first verified completion

The first two direct POST `/v1/chat/completions` smokes on October 30 returned HTTP 401. Each retained null provider identity, usage and actual cost. Two separate credential-bearing GET `/v1/models` diagnostics also returned HTTP 401 without requesting completions. These earlier failures remain part of the record; their account-side cause was not established.

A replacement credential's read-only GET `/v1/models` check returned **HTTP 200**, with 30 models, at the recorded **October 30 23:58:27.634123 KST** timestamp. The third direct POST smoke then returned HTTP 200 with exact requested/provider identity `nvidia/Nemotron-3_5-Lightning`, **19 prompt + 16 completion = 35 total tokens**, and **1052.11 ms** HTTP latency. Its usage-price estimate is **$0.00000498** at the fresh catalog's $0.06/$0.24 input/output rates per million tokens. All 16 completion tokens were reported as reasoning tokens; the smoke artifact retains no generated text, so it does not establish a user-visible story or tool execution.

The smoke's saved **23:58:59.311470 KST** timestamp is dispatch start, not response arrival. Adding its HTTP latency gives an **approximate response time of 23:59:00.363580 KST**. The interval from the recorded successful credential-verification GET to that approximate verified completion response is **about 32.7 seconds**. This includes intervening setup and request time and is not key creation, signup or an exact response-event measurement. Do not replace it with the later collector's 8.0169-minute interval or describe the local-presence-marker interval as onboarding.

## Controlled Korean Super–Ultra probe · completed October 31

Both models received the identical Korean scene and unchanged protocol: exactly three trimmed nonempty lines, at most 40 Unicode code points per line, 120 total characters, 180 output tokens, and no required station ending. Common request SHA-256: `bde448c43d5203f3e317c3e4f1452a0cbda4b2f0089a45e76fc4e2c12eab8305`.

> 서울 지하철 빈 좌석에서 노란 봉투를 발견한 사람이 봉투 속 손그림 지도를 펼치는 장면입니다. 인물과 장소를 늘리지 말고 이 장면만 짧은 한국어 이야기로 쓰세요.

| Observation | Super | Ultra |
| --- | --- | --- |
| Exact requested/provider model | `nvidia/nemotron-3-super-120b-a12b` | `nvidia/Nemotron-3-Ultra-550b-a55b` |
| HTTP / validation | 200 / accepted | 200 / accepted |
| Prompt / completion / total tokens | 156 / 49 / 205 | 156 / 36 / 192 |
| Recounted line lengths | 24, 29, 28 | 19, 19, 17 |
| Total characters | 81 | 55 |
| Countable lines within 40 characters | 3/3 | 3/3 |
| Provider-call latency | 1351 ms | 2940 ms |
| Worker response latency | 2056 ms | 3605 ms |
| Client POST latency | 2633.76 ms | 4134.57 ms |
| Usage-price cost estimate | $0.0000909 | $0.000264 |

There were **2 Worker write requests, 2 provider completion receipts, 2 accepted outputs, 6/6 countable line units within the cap, and 0 rejected, excluded or unknown rows**. Combined usage-price estimate: **$0.0003549**. Successful text was independently recounted and matched each receipt's validation summary. The denominator is trimmed nonempty lines, not a semantic sentence parser. This is one response per model on one scene; it does not establish a general obedience rate, Korean quality ranking or superiority.

Verified Super sample, with no quality grade assigned:

```text
지하철 빈 좌석에 앉아 노란 봉투를 꺼냈다.
봉투 안에는 아이 같은 손그림 지도가 펼쳐져 있었다.
길목마다 작은 별이 그려져 있어 마음이 따뜻해졌다.
```

Verified Ultra sample, with no quality grade assigned:

```text
지하철 빈 좌석에 노란 봉투가 있다
손그림 지도가 봉투 속에서 펼쳐진다
누군가 길을 찾으려 지도를 본다
```

Both responses returned request-rate headers `limit=1000, remaining=999`. Super's token headers were `limit=1000000, remaining=999698`; Ultra's were `limit=2000000, remaining=1999698`. These are the returned values for these calls, not universal throughput guarantees. Writer-only probe calls do not test Super or Ultra tool-call support. This same-Korean-scene probe is separate from the English-Super/Korean-Ultra timing pair.

The collector records **481.013955 seconds / 8.01689925 minutes** from a local file-presence marker to its first verified Korean-probe response near **00:07:00 KST**. The earlier Lightning smoke already produced a verified response near 23:59; the collector interval must not be called the first provider reply overall. It also does not measure signup, key creation or which local credential bytes the Worker used.

## Rejected normal-story outputs · distinct prompt versions

| Run / protocol | Exact provider receipt | Usage and estimate | Validated inspection | Outcome |
| --- | --- | --- | --- | --- |
| `model-reduced-20261031-02.json`, original prompt | Super, identity matched | 170 + 363 = 533 tokens; $0.0003777 | 10 line units: 2 within 90, 8 over; max 202; total 1433 within budget 2130; station ending valid | Worker HTTP 502; only `sentence_cap` failed; 0 scored rows/pairs |
| `model-reduced-20261031-03.json`, `normal-writer-short-lines-v2-20261031` | Super, identity matched | 350 + 1033 = 1383 tokens; $0.0010347 | 82/82 line units within 90, max 60; total 3847 exceeds budget 2130 by 1717; station ending valid | Worker HTTP 502; only `scene_budget` failed; 0 scored rows/pairs |

Each file contains one dispatched completion and no automatic retry. The rejected text is discarded; its bounded Worker inspection counters were independently checked for protocol and arithmetic consistency. The original prompt's **2/10** and v2's **82/82** per-line observations retain separate denominators. A changed prompt and one sample each do not establish a controlled performance improvement. Both stories were rejected, so neither supplies landing-error, accepted-story or speech-timing results. Their real costs remain counted despite the absence of scored rows.

The earlier `model-reduced-20261031-01.json` aborted during client/status setup with **0 inference dispatches, 0 completion receipts and 0 rows**. It is not a paid model trial. Saved diagnostics show default Python User-Agent HTTP 403/Cloudflare 1010 and explicit `Last-Sentence-Evaluation/0.1` HTTP 200; the local client fix is distinct from model behavior.

## Later reduced runs 04–06 and interrupted outcome

`model-reduced-20261031-04.json` used Writer v3 (`ebe570fdada95775676c7e64ccf61e785df4913b`). It completed two policy rows, then aborted on Conductor HTTP 502 `invalid_plan` for an unsupported operation. Its **3 Worker dispatch groups / 5 provider completion receipts** retain **$0.00086118** of known usage-price estimates. The two completed rows do not form a complete three-policy comparison.

`model-reduced-20261031-05.json` was stopped after a failed prompt-envelope regression was discovered following deploy/run. The preserved checkpoint still says `running`, but the interruption sidecar records exit 130 and **1 dispatched Worker write, 0 returned receipts, unknown outcome/cost**. Its **$0.0059952 local upper-bound reservation** is retained. Do not silently replace the unknown outcome with zero, retry the unchanged request or count it as a successful output. A later Worker ledger showing no extra reservation does not independently resolve the provider outcome.

`model-reduced-20261031-06.json` records source `e65f3b6f2cfd20440cf54e6ae35d971ed51eb210`, `writer-budgeted-lines-v3/conductor-ops-compact-v4`; its sidecar's Worker-source hash matches that commit. It completed **3 policy rows on one frozen line-2 journey**, then aborted on the next journey's Writer station-ending check. Exact identities, canonical leaf/aggregate token and cost arithmetic, validation summaries and row receipt references were independently checked.

| Run06 policy | Completed rows | Simulated landing error | Within ±30 seconds |
| --- | ---: | ---: | ---: |
| fixed_clip | 1 | −100.51 s | 0/1 |
| single_fit | 1 | −213.73 s | 0/1 |
| sentence_replan | 1 | −230.68 s | 0/1 |

All three rows share the same frozen journey and arrival proxy, so completed-row coverage is one fully paired journey; it is not completion of the planned five-journey matrix. Completed model coverage is line 2 only. The selected-input list names lines 2/5/7, but that list is not completed evaluation coverage. There are **0 EN/KO timing-pair rows** in this run. Negative errors mean early ending. The clock is **4.51 Unicode characters/second plus measured HTTP latency**; no browser speech or door-opening time was measured. The single-fit story had already ended before its midpoint update; the replanning story ended before the next station event. These observations do not establish a timing improvement.

Run06 contains **6 Worker dispatch groups / 10 exact-identity provider completion receipts**, **5744 prompt + 997 completion = 6741 total tokens**, with **$0.00153714** of known usage-price estimates. Three Writer outputs were accepted. The final rejected Writer response had **15/15 line units within 90 characters, max 52, total 609 ≤ budget 2002**, but `ending_station_ok:false`; only `station_ending` failed. Its raw rejected text is unavailable, so no translation, punctuation or other specific cause is inferred. The rejected call's cost remains included despite supplying no scored row.

Lightning emitted and the Worker executed tools in **2/2 successful planning requests** in run06. Both executed **`eta_to_station` and `budget`**; neither executed `scene_ops`, so **0/2 completed all three required tools**. Each plan retained its three completion attempts, including final JSON. This establishes actual partial tool-loop behavior for this tested model/protocol, not complete tool-chain execution or tool support for Super/Ultra. Provider receipt count, planning-request count and executed-tool count are different units.

## Reduced07 · all scheduled slots visited, one model rejection retained

Run07 records source `0cf2badf6990287422fee94d53767c58c4c193a3`, with the same Worker hash and Writer-v3/compact-Conductor-v4 prompt as run06. Its runner records independent slots, validates exact leaf and aggregate token totals, and moves past a fully costed model-output rejection without retrying that slot. All **17 scheduled slots were attempted exactly once: 16 scored, 1 failed, 0 aborted and 0 unstarted**. Canonical attempt references partition the 35 HTTP dispatch groups without duplication.

| Main policy | Scheduled / scored / failed | Scored within ±30 s | Median absolute simulated error |
| --- | --- | --- | --- |
| fixed_clip | 5 / 5 / 0 | 0/5 | 160.77 s |
| single_fit | 5 / 4 / 1 | 1/4 | 255.38 s |
| sentence_replan | 5 / 5 / 0 | 0/5 | 219.17 s |

The missing single-fit row is an explicit failure, not an invented timing error. Its Writer returned 21 line units, all within 90 characters, total 1103 within budget 2130, but failed the station-ending check. No rejected text is retained, so no specific translation/punctuation cause is asserted. Its **$0.0003627** usage-price estimate remains in the run total.

The main table has **14 scored rows on five frozen journeys**, with **4 fully paired journeys and 1 unpaired journey**; marginal policy summaries therefore mix paired and unpaired coverage. Selected lines 2/5/7 contributed 2/2/1 journeys. This tiny reduced sample does not establish a controlled aggregate policy improvement, and sentence-replanning achieved **0/5 within ±30 seconds** here. All timing uses the declared fixed-character-rate clock and recorded station-arrival proxies, not browser speech or doors.

Two additional language-pair slots both scored on the same frozen line-2 journey, policy, arrival proxy and 4.51-character/s clock:

| Pair row | Exact Writer | Simulated error | Total tokens including Conductor | Usage-price estimate |
| --- | --- | ---: | ---: | ---: |
| English | Super | −183.16 s | 7142 | $0.0007116 |
| Korean | Ultra | −354.30 s | 2606 | $0.00074294 |

This is a two-run descriptive comparison, not a language-quality score. It is separate from the identical-Korean-scene probe above. The full 30-journey experiment was not run.

Run07 retained **35 Worker HTTP dispatch groups and 69 exact-identity completion receipts**, **42690 prompt + 5597 completion = 48287 tokens**, with **$0.00908516** of known usage-price estimates. Exact model IDs, token sums, prices, cost arithmetic, slot costs, completed-row copies and source hash were independently audited. The 69 leaves include 51 Lightning completions in 17 plan groups and 18 Writer completions.

Lightning executed **ETA + budget in 17/17 plan groups**, while **0/17 completed all three tools**: `scene_ops` was absent. English Writer inspection retained **399/399 line units within 90 characters across 17 completions**, with **16 accepted outputs and 1 station-ending rejection**. The Korean timing-pair Writer retained **12/12 lines within 40 characters and one accepted output**. Each denominator belongs to run07's normal-story protocol; it is not pooled with the controlled three-line probe or earlier prompt versions, and it is not a general model-obedience or semantic-quality claim.

## Connected browser capture · terminal October 31 00:33 KST

One paused Korean replay generation cycle completed on the public Worker. The UI recorded **2 service events**: one `/api/plan` response containing **3 Lightning completions**, and one `/api/write` response containing **1 Ultra completion**. Thus **4 provider completions** must not be labeled as two model calls merely because the panel shows `2 SERVICE EVENTS`.

| Retained capture receipt | Prompt / completion / total tokens | Usage-price estimate |
| --- | --- | ---: |
| Lightning 1 | 818 / 17 / 835 | $0.00005316 |
| Lightning 2 | 890 / 15 / 905 | $0.00005700 |
| Lightning final JSON | 445 / 16 / 461 | $0.00003054 |
| Korean Ultra Writer | 415 / 80 / 495 | $0.00065500 |

The retained extracts have exact requested/provider IDs, consistent token sums, fresh acknowledged rates and independently recomputed costs. Capture subtotal: **2568 prompt + 128 completion = 2696 tokens**, **$0.00079570**. Saved Writer validation reports **10/10 lines within 40 characters and a valid station ending**. The capture artifact retains a reduced validation summary rather than the raw output lines/full counter contract, so this audit does not claim an independent text recount for that capture. Plan tool-execution metadata is also absent from this capture artifact; three Lightning completions alone do not prove a complete three-tool chain.

These are actual generated text and receipts in a **known-recorded-replay/text-only timing simulation**. Screenshot timing indicators remain examples, not speech/door-opening measurements. The three captured images are preserved; the separate keyless captures remain historical. The capture's conservative cycle bound **$0.023224** stayed within its allocated **$0.03**, while actual receipt-based price estimates are reported separately.

## Scoped accounting and remaining measurements

The scope through terminal run07 and connected capture contains **93 provider completion receipts/extracts with exact requested/reported IDs**, including the reasoning-only smoke, accepted and rejected normal-story/Conductor attempts, two controlled-probe outputs and four capture completions. Known returned usage is **54545 prompt + 8924 completion = 63469 tokens**, with a known usage-price subtotal of **$0.01405146**. Two earlier HTTP 401 POST attempts have no returned usage/cost, and interrupted run05 has one dispatched request without a receipt. **Overall invoice cost remains unknown.** This is the audited terminal snapshot; any later call would require a new accounting entry. Costs are aggregated across protocols for accounting only; performance/compliance results remain versioned separately.

Count each canonical leaf once: matrix `attempts[].response.calls[]` or controlled-probe `rows[].receipt.calls[]`. Parent aggregate receipts and completed-row copies are duplicates, not extra calls. Three direct smokes retain a conservative **2961 microUSD ($0.002961)** outside-Worker reserve; the enabled Worker's **$2.997039** budget preserves the directly authorized **$3 total**. Reservations, usage-price estimates and invoices are separate quantities; keep the shared ledger and account for every later attempt. The final saved authenticated status reports **92 Worker completions used, 1956 remaining, $0.126296 reserved**, with zero search/Seoul calls. The 92 known Worker receipt reservations reconcile exactly: after06 19 / $0.033669; run07 added 69 / $0.081527; capture added 4 / $0.011100. Adding the direct-smoke reserve gives **$0.129257 of known conservative application/direct reserves**, separate from the usage-price subtotal. This reconciliation does not assign a zero outcome to interrupted05.

| Measurement | Current evidence boundary |
| --- | --- |
| Lightning tool calls and required tool execution | Run07: 17/17 plans executed ETA + budget; 0/17 executed all three required tools. Capture tool-execution metadata is not retained; smoke did not request tools |
| Super/Ultra tool-call support | Not tested by Writer-only calls |
| Korean semantic quality | UNMEASURED; verified samples are provided without a quality grade |
| Model-backed timing comparison | Run07 visited all 17 reduced slots: 14 main-policy rows + 2 language rows scored, 1 explicit failure. Four fully paired journeys; replan 0/5 within ±30 seconds in character-rate simulation |
| Browser speech / door opening | UNMEASURED by these artifacts; character-rate simulation and station-arrival proxies do not establish either |
| Tavily usefulness | UNRUN; no search requested in this finished scope |
| Full 30-journey matrix | Skipped: valid-key observation after 23:58 KST missed the handoff's 19:30 conditional cutoff |

## Evidence paths

Repository-relative paths are rooted at `/Users/felix/dev/last-sentence/`. Private proposal evidence is rooted at `/Users/felix/dev/last-sentence-proposal/evidence/`; those local files are not public links and no credentials are included here.

| Observation | Exact source path |
| --- | --- |
| Earlier rejected smokes | `/Users/felix/dev/last-sentence-proposal/evidence/nebius-smoke-20261030-01.json` and `nebius-smoke-20261030-02.json` in the same directory |
| Successful credential check | `/Users/felix/dev/last-sentence-proposal/evidence/new-key-readonly-auth-check.json` |
| Verified Lightning smoke / independent audit | `/Users/felix/dev/last-sentence-proposal/evidence/nebius-smoke-20261030-03.json`; `smoke-success-audit.json` in the same directory |
| Frozen fresh price snapshots | `evidence/model-prices-live-20261030.json`; run07 uses `evidence/model-prices-live-20261031.json` |
| Client/setup-only abort | `evidence/model-reduced-20261031-01.json` |
| Original normal-story failure | `evidence/model-reduced-20261031-02.json`; private `reduced02-audit.json` |
| V2 normal-story failure and source | `evidence/model-reduced-20261031-03.json`; `evidence/model-reduced-20261031-03.metadata.json` records commit `00d630348835dcfd7ce30f482ebc2a54aa016950`; private `reduced03-audit.json` |
| Controlled Korean raw run / audit | `.local/feedback-run-20261031-01.json`; private `feedback01-audit.json` |
| Historical finished subtotal before04 | `/Users/felix/dev/last-sentence-proposal/evidence/inference-known-subtotal-before04.json` |
| Public sanitized final runtime audit | `evidence/runtime-live-audit.json` |
| Public sanitized Korean probe | `evidence/feedback-probe-live.json` |
| Reduced04 / interrupted05 | `evidence/model-reduced-20261031-04.json`; `evidence/model-reduced-20261031-05.json`; `evidence/model-reduced-20261031-05.interruption.json` |
| Run06 / independent audit | `evidence/model-reduced-20261031-06.json`; `evidence/model-reduced-20261031-06.metadata.json`; private `reduced06-audit.json` |
| Terminal run07 / audit | `evidence/model-reduced-20261031-07.json`; `evidence/model-reduced-20261031-07.metadata.json`; private `reduced07-audit.json` |
| Connected capture / audit | `/Users/felix/dev/last-sentence-proposal/shots-connected/capture-evidence.json`; private `connected-capture01-audit.json` |
| Shared guard | `/Users/felix/dev/last-sentence-proposal/evidence/inference-budget-guard.json` |

## Earlier public/keyless snapshot · October 30 before credential setup

The original keyless preflight found 30 public catalog entries and all five preregistered model IDs, while unauthenticated `/v1/models` returned HTTP 401. The saved catalog/card review kept advertised prices and supported-language lists distinct from measured generation quality. Key absence and no-runtime-result statements in that earlier snapshot are historical, not the current credential or Writer-response status.

A concrete documentation concern remains: model discovery, prices and model-card links live in the catalog, while supported languages live in model cards. The ordinary-story failures also show why applications must retain rejected-output usage and separate per-line limits from total scene budgets. Whether planning/writing separation improves story timing or cost still requires the same-trace comparison; no such outcome follows from the samples above.
