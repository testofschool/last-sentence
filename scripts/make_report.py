#!/usr/bin/env python3
"""Assemble a local-run report from saved evidence. Does not run external actions."""
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]

def read(name, default=None):
    p = ROOT/name
    return json.loads(p.read_text()) if p.exists() else default

def cell(value):
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return html.escape(s, quote=False).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

def main():
    pre = read("evidence/preflight.json", {})
    verification = read("evidence/verification.json", {})
    meta = read("web/replay/trace_2026-10-30.meta.json", {})
    manifest = read("web/replay/recorded-manifest.json", {})
    eta = read("evidence/eta_evaluation.json", {})
    full = read("evidence/cost-plan-full.json", {})
    small = read("evidence/cost-plan-default-cap.json", {})
    quality = read("evidence/trace_quality.json", {})
    ages = quality.get("receipt_timestamp_age_s", {})
    checks = verification.get("checks", [])
    local_ok = verification.get("status") == "PASS_LOCAL"
    clone = read(".local/clone-check.json", {})
    clone_text = "PASS_LOCAL_ONLY" if clone.get("status") == "PASS" else "NOT_RUN"
    integrity_text = "PASS_LOCAL_CHECKS — checksum manifest generated" if (ROOT/"SHA256SUMS.txt").exists() and local_ok else "PENDING until recording finishes and final verification runs"
    error = eta.get("median_relative_error")
    error_text = f"{error:.4%}" if error is not None else "UNAVAILABLE"
    eta_gate = "PASS" if eta.get("gate_lte_15_percent") is True else "FAIL" if eta.get("gate_lte_15_percent") is False else "UNAVAILABLE"
    stamp = dt.datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    lines = ["# Last Sentence · execution report", "", f"Updated {stamp}.", "",
             "**Disposition: HOLD.** Local code, replay and deployment packaging are implemented; actual Nebius/Tavily runtime use, prospective live narration, observed model-backed speech timing and public release remain unverified. This report is not a submission receipt or a claim of contest eligibility.", "",
             "The user's `/goal run` initiated the local build. The three supplied documents were read as technical references and evidence, not independent permission to spend, publish or submit. The user later confirmed the API keys are not yet available. Existing hackathon files were left in place; this is a separate local repository at `~/dev/last-sentence`.", "",
             "## §0 Preflight", "", "| Item | Observed |", "| --- | --- |"]
    for name, path in pre.get("tools", {}).items():
        lines.append(f"| {name} | {cell(path or 'not global; project-local fallback where available')} |")
    lines += ["| Wrangler fallback | Project-local Wrangler 4.156.0 installed from npm; dry-run and generated types checked |",
              "| Keys | Nebius absent; Tavily absent; private Seoul key absent; public sample used for read-only recording |",
              "| GitHub | Existing login observed; read-only target lookup was unresolved/inaccessible. No remote created, push or public clone performed. See `evidence/github_probe.json`. |",
              "| Network | Token Factory catalog 200; unauthenticated inference models 401; Seoul HTTP sample 200; separate HTTPS sample timed out after 20 s |", "",
              "## §1 Preregistered P1–P12", "", "| ID | Expected | Observed | Status |", "| --- | --- | --- | --- |"]
    for c in pre.get("checks", []):
        observed, status = c["observed"], c["status"]
        if c["id"] == "P11" and full:
            observed = {"full_plan_usd":full.get("worst_case_usd"),"cap_usd":full.get("cap_usd"),"allowed":full.get("allowed"),"actual_inference_calls":0}
            status = "REFUSED_PREDISPATCH" if not full.get("allowed") else "PLANNED_NOT_EXECUTED"
        lines.append(f'| {c["id"]} | {cell(c["expected"])} | {cell(observed)} | {status} |')
    lines += ["", "P7 checks the supported-language section, not incidental mentions of Korean in training-data descriptions. It does not establish that other models cannot generate Korean. P12 found the termination banner in page HTML while a separately queried sample response was fresh. Saved sources and hashes are in `evidence/preflight.json`; full downloaded pages are retained locally and ignored by Git.", "",
              "## §2 Track status", "", "| Track | Status and concrete evidence |", "| --- | --- |",
              f"| T1 recording | {'40-minute planned run completed' if meta.get('complete') else 'Partial recording'}; {meta.get('polls',0)} polls, {meta.get('observations',0)} observations, {meta.get('gaps',0)} gaps; `{meta.get('started_at','?')}` to `{meta.get('finished_at',meta.get('last_poll_at','?'))}` |",
              f"| T1 ETA | Held-out train identities; {eta.get('n',0)} eligible 3–10-segment windows; median relative error {error_text}; registered ≤15% gate **{eta_gate}**. Station-arrival proxy only. |",
              f"| T1 data quality | Receipt timestamp age: median {ages.get('p50','?')} s / p95 {ages.get('p95','?')} s across repeated poll records. This is not network delay or a door-opening offset. Overlapping forecast windows are not independent journeys. |",
              f"| T1 replay data | {len(manifest.get('journeys',[]))} contiguous recorded journey segments; known future replay clock, not an ETA forecast. Three separate synthetic fixtures. |",
              "| T2 Worker | Implemented tools, fallback, Writer validation, receipts, atomic quotas and authenticated observed ETA. Actual public SAMPLE position → verified arrival/terminus → 3-stop ETA passed in local workerd; `/api/plan` correctly refused the missing Nebius key. Model behavior remains mock-tested only. See `evidence/worker/runtime_frozen_eta.json`. H2/H4 parked: inference and deployment unrun. |",
              "| T3 app | Recorded/fixture source and train selection, language, replay controls, optional sequential TTS, receipts and explicit connected generation. Prepared Live controller selects actual train/direction/forward exit, keeps wall time during requests and swaps rewritten text at a sentence boundary. Desktop keyless flows checked; connected/Live paths use mocked tests until vendor keys and field validation. |",
              "| T4 comparison | 0 real inference runs. Nine explicitly synthetic policy rows only. Guarded model-backed timing-simulation executor implemented with mock HTTP tests; it requires explicit execution/cost flags, protected session credentials, fresh pricing and Worker capacity checks. Full plan refused. Real browser timing is imported separately. |",
              "| T5 documents | README, LIMITATIONS, FEEDBACK, PRIOR_ART, RESULTS, DATA, API, RUNBOOK and VIDEO_SCRIPT present. Feedback and video remain local drafts. |", "",
              "## §3 Acceptance A1–A7", "", "| Gate | Result |", "| --- | --- |",
              f"| A1 local tests | {'PASS' if local_ok else 'See evidence/verification.json'}; exact commands/counts below. This code-test result does not override the separate ETA quality gate. |",
              f"| A2 public remote clone | PARKED — no public remote/push. Supplementary local fresh-clone check: {clone_text}; evidence path `.local/clone-check.json`. It cannot satisfy the public-remote gate. |",
              "| A3 deployed replay | PARKED — no deployed URL. Loopback title/asset/API/doc checks passed, including real local workerd. Local preview: `http://127.0.0.1:4188/`. |",
              "| A4 actual matrix | PARKED — 0 measured model-backed runs; keys unavailable. `docs/RESULTS.md` states the 9-row synthetic boundary. |",
              f"| A5 secret check | {verification.get('secrets',{}).get('status','PENDING')}; no actual key bytes existed for an exact-value credential scan. Provider keys were never loaded or embedded. |",
              f"| A6 integrity | {integrity_text}. `SHA256SUMS.txt` covers documents, web/replay, app, scripts, Worker source, tests and sanitized evidence. The self-updating verification JSON is excluded. |",
              "| A7 provenance | Git author configured as `felix`. New project source only; the supplied handoff and prior-project code were not copied into the repository. |", ""]
    for c in checks:
        summary = "\n".join(c.get("stdout", "").strip().splitlines()[-10:])
        lines += ["```text", " ".join(c["command"]), summary, f"exit_code={c['exit_code']}", "```", ""]
    lines += ["## §4 Cost", "", "Actual model calls: **0**. Actual Tavily calls: **0**. Actual model/search API spend from this run: **$0**. Public position/API documentation requests are separate from model inference.", "",
              f"- Full 30×3 + language pair: bound ${full.get('worst_case_usd','?')}, {full.get('max_total_completions','?')} completions; refused.",
              f"- Default-cap alternative 5×3 + language pair: bound ${small.get('worst_case_usd','?')}, {small.get('max_total_completions','?')} completions; planning only.",
              "- 17×3 + language pair: $2.89791392 / 811 completions; requires an explicitly raised call-count configuration, available reservation capacity and separate authorization. It remains unrun.",
              "- The Worker keeps a ≤$3 inference reservation ceiling and independently limits completions/searches. Tavily credit pricing is not established by the model catalog. Bounds and provider-usage estimates are not invoices or an account-wide spending guarantee.", "",
              "## §5 Changes from the supplied plan", "",
              "- Created a new isolated local repository; public GitHub and Cloudflare actions were not inferred from the attachment.",
              "- `worker/wrangler.jsonc`, `worker/src/limits.js`, generated types, lockfile and tests use a SQLite Durable Object in place of a KV-only read/modify/write quota, so concurrent requests cannot bypass the application cap.",
              "- `scripts/build_replay.py`, `scripts/analyze_trace.py`, `scripts/prepare_eta.py` and recorded/fixture manifests keep observation provenance and known replay clocks separate. The ETA bundle binds model and held-out evaluation to a single trace hash. The recording date is October 30, not the handoff's October 29 filename.",
              "- `scripts/build.mjs`, `scripts/serve.mjs`, `scripts/verify.py` and `scripts/make_report.py` provide local preview, complete static app/doc packaging and reproducible local checks. No global tool installation or automatic login occurred.",
              "- `tests/player.test.mjs`, `tests/connected_flow.test.mjs` and local workerd tests exercise UI timing, cancellation, cost retention and atomic quotas without vendor inference.",
              "- `scripts/model_simulation.py` adds an explicitly guarded inference executor to `run_matrix.py`. Its speech clock uses fixed characters/second plus measured HTTP latency, and is always labeled model-backed timing simulation. It never claims actual browser TTS. Real audio experiments remain additional work after keys are available. Connected replay uses a known event clock; Live keeps wall time and an observed arrival proxy.",
              "- The registered ETA gate is reported as measured, including failure or insufficient data. The handoff's earlier percentages, example +4 s, install count and unverified competitive claims are not presented as new results.",
              "- Full downloaded third-party pages, node_modules, build output, credentials and temporary clone artifacts are excluded from version control. Compact source/pricing/verification evidence is retained.", "",
              "## §6 Human gates", "",
              "1. H2/H3: Nebius/Tavily keys are not yet available (confirmed by the user). The public SAMPLE path and completed ETA gate now work; real model calls, voice timing and field use remain unverified. A private Seoul key path additionally requires HTTPS reachability.",
              "2. H4: after reviewing this local build, explicitly authorize any real inference experiment and its total spending limit, then separately approve public source/deployment. No such external operation was performed here.",
              "3. H1/H5/H6: Devpost draft/registration state is unknown; phone review, public YouTube video and submission are unrun. These remain manual human actions. The official deadline was checked as October 31, 2026, 02:00 KST. A keyless replay alone does not meet the required runtime Nebius use.", "",
              "Primary rule source: https://nebiusglobalaihackathon.devpost.com/rules. Reproduction and resumption steps are in `docs/RUNBOOK.md` and `docs/API.md`.", ""]
    (ROOT/"REPORT.md").write_text("\n".join(lines))
    print(ROOT/"REPORT.md")

if __name__ == "__main__":
    main()
