# Last Sentence · 마지막 문장

A story that is intended to finish at your subway stop. Select a destination, follow the sentence stream, and inspect how the available time changes the story.

**Current build: working local recorded/fixture replay and prepared connected-model API; real Nemotron/Tavily inference, live timed narration and public deployment are unverified.** Stories are hand-authored until connected generation is explicitly selected. Recorded replay uses known provider timestamps; synthetic fixtures are separate. It needs no account or keys. It is not evidence of ±30-second performance on a train.

```sh
cd ~/dev/last-sentence
npm run dev
```

Open the printed local URL. Choose Replay, a source, train journey and destination, then start. Try ×16 to inspect the ending; pause, scrub, switch language or restart. Audio is optional and browser voices vary. Keyless replay has no inference cost. Keep the screen open.

## Which model does what

| Component | Intended live model/service | Implementation and execution status |
| --- | --- | --- |
| Conductor | `nvidia/Nemotron-3_5-Lightning` on Nebius Token Factory | Tools for ETA, character budget and scene operations; API implemented, runtime model behavior UNMEASURED |
| English Writer | `nvidia/nemotron-3-super-120b-a12b` | Sentence and destination checks implemented; real output UNMEASURED |
| Korean Writer | `nvidia/Nemotron-3-Ultra-550b-a55b` | Selected because its supported-language list includes Korean; real output UNMEASURED |
| Neighbourhood fact | Tavily | Source URL retained when available; real search UNRUN |
| Train position | Seoul real-time subway sample API | Dated observations recorded separately from fixture journeys |

The prepared Live controller uses a completed, provenance-bound ETA artifact and server-cached train arrivals. It requires a selected actual train/direction and a forward line-2 exit. The train clock keeps advancing while model requests run; rewritten text waits for a sentence boundary. These behaviors have mock tests; actual model-backed Live use remains unrun.

The public model catalog and model cards were checked on October 30, 2026 KST. A language missing from a card's supported-language list does not prove that the model cannot generate that language. This is a conservative model-selection policy.

## Run and inspect

Node.js 22+ and Python 3.10+ are used; the local frontend has no package dependencies. The test command also needs pytest (`python3 -m pip install pytest` if absent).

```sh
npm test
python3 -I scripts/preflight.py
python3 -I scripts/verify.py
```

Preflight makes public read-only requests, saves dated primary-source evidence, and checks only whether the three expected key files exist. It does not install tools, read key bytes, register accounts, spend credits or deploy. `verify.py` tests the code, checks local credential bytes without printing them, and hashes deliverables. Finish or stop recording before the final integrity check.

The local server binds to `127.0.0.1` and never loads credentials. It serves `/api/status` with live services disabled. Cloudflare Worker development and a protected live setup are documented in [API.md](docs/API.md). Keep vendor keys on the server. `npm run build` prepares `dist/` with both app assets and linked documents for one-origin hosting.

“Generate with connected models” is an explicit optional billable action. It checks a separately configured Worker and session credential before requesting a fact, a plan and a story; subsequent station events can replan. This path was reviewed and mock-tested, but has not executed against real models. Its replay clock is known in advance and cannot establish prospective arrival accuracy.

## Evidence and results

| Quantity | Current meaning |
| --- | --- |
| 3 fixture journeys | Synthetic line 2, 5 and 7 scenarios for deterministic UI checks |
| $0 inference cost | No paid model/search requests were made in this build run |
| 0 measured model-backed journeys | The 30×3 comparison is gated on actual observations and credentials |

The conservative full plan is **$4.85581376 / 1,370 completions**, so it is refused by the $3/default-300-call gates. A **5-journey × 3-policy + 2-language** plan is **$1.09062176 / 295 completions** at the checked prices. This is a bound, not actual spend or reserved capacity. The 17-journey alternative needs an explicitly raised completion-count setting and remains unrun.

[Results](docs/RESULTS.md) separate deterministic scheduling tests from observed train records and real inference. A guarded model-backed timing-simulation runner is prepared for an explicitly approved, authenticated run; it retains actual model receipts while labeling character-rate speech timing as simulation. Actual browser-speech results require separately recorded events. [Limitations](docs/LIMITATIONS.md) explain the gaps. [Prior art](docs/PRIOR_ART.md) includes systems that already adapt stories to journeys; no novelty or superiority claim follows from this prototype.

`REPORT.md` records acceptance A1–A7, P1–P12 and remaining gates. [Feedback](docs/FEEDBACK.md) contains only observations that were actually made. [Runbook](docs/RUNBOOK.md) lists the next steps needed for a model-backed, reviewable release; [video script](docs/VIDEO_SCRIPT.md) is a draft using the current evidence boundary.

## 한국어

목적지에 도착할 때 끝나는 이야기를 실험하는 로컬 프로토타입입니다. 직접 쓴 예시 문장에 실제 열차의 기록된 시각이나 별도의 합성 시간표를 연결해 재생합니다. 화면의 종료 오차를 실제 문 열림 시각이나 앞으로의 도착 예측 성능으로 해석하면 안 됩니다.

현재 Nemotron·Tavily 실제 호출, 실시간 운행에 맞춘 이야기 생성, 공개 배포와 제출은 완료되지 않았습니다. 기록이 부족한 역 구간은 검증된 ETA로 표시하지 않습니다. API 키는 브라우저나 Git에 넣지 않습니다.

MIT · felix · 2026
