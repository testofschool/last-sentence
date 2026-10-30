#!/usr/bin/env python3
"""Inventory the full handoff scope without equating local code with execution."""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path, default=None):
    file = ROOT / path
    return json.loads(file.read_text()) if file.exists() else default


def main():
    requirements = []
    def item(identifier, requirement, status, evidence, remaining=None):
        requirements.append({"id": identifier, "requirement": requirement,
                             "status": status, "evidence": evidence, "remaining": remaining})

    recordings = [dict(path=str(p.relative_to(ROOT)), **json.loads(p.read_text()))
                  for p in sorted((ROOT / "web/replay").glob("*.meta.json"))]
    complete_lines = sorted({r["line"] for r in recordings if r.get("line") in ("2호선", "5호선", "7호선")
                             and r.get("complete") and r.get("finished_at")})
    all_lines = complete_lines == ["2호선", "5호선", "7호선"]
    manifest = read("web/replay/recorded-manifest.json", {})
    replay_lines = sorted({j["line"] for j in manifest.get("journeys", [])})
    verification = read("evidence/verification.json", {})
    full = read("evidence/cost-plan-full.json", {})
    window_plan = read("evidence/matrix_windows.json", {})
    prices = read("evidence/model-prices.json", {})
    previous_clone = read(".local/clone-check.json", {})
    source_name = "CODEX_HANDOFF_LASTSENTENCE_v1_20261029.md"
    source_path = Path.home() / "Downloads" / source_name
    previous_source = read("evidence/completion_audit.json", {}).get("source_document", {})
    source = {"name": source_name, "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path.is_file() else previous_source.get("sha256"),
              "hash_basis": "original local attachment" if source_path.is_file() else "retained attachment hash; original file unavailable in this checkout"}
    item("G0", "Spoken last sentence within ±30 seconds of actual door opening", "UNMEASURED",
         ["docs/LIMITATIONS.md"], "An independently observed door timestamp, actual model output and uninterrupted browser speech are required. Provider receipt/arrival status is a separate proxy.")
    item("T1.1", "Full 40-minute actual sample recording, gaps retained", "PASS_RECORDED" if all_lines else "RECORDING_IN_PROGRESS",
         [r["path"] for r in recordings], None if all_lines else "Finish the active recordings; do not freeze checksums while they change.")
    item("T1.2", "Median/SD segment model, line fallback, requested predict CLI, train-held-out 3–10-stop evaluation",
         "LOCAL_IMPLEMENTATION_WITH_SEPARATE_QUALITY_GATES", ["scripts/eta_model.py", "scripts/prepare_eta.py", "tests/test_eta_model.py"],
         "Read each frozen line's actual evaluation; a code-test pass cannot substitute for the ≤15% data-quality gate or field accuracy.")
    item("T1.3", "Character budget from remaining seconds, 4.51 cps and 20-second margin", "LOCAL_CODE_TESTED",
         ["scripts/contracts.py", "tests/test_budget.py"])
    item("T2.4a", "Position proxy, 15-second cache, atomic 950-attempt/day replay fallback", "LOCAL_RUNTIME_AND_MOCK_TESTED",
         ["worker/src/core.js", "worker/src/limits.js", "tests/worker_quota.test.mjs", "evidence/worker/runtime_all_lines.json"], "Deployed behavior is unrun.")
    item("T2.4b", "Lightning tool loop, bounded fallback, authoritative ETA/budget and visible plan", "UNRUN_REAL_MODEL",
         ["worker/src/core.js", "tests/worker.test.mjs"], "Observe genuine tool calls, fallback support, usage and latency with a Nebius key.")
    item("T2.4c", "Super English / Ultra Korean Writer, sentence limits and destination ending", "UNRUN_REAL_MODEL",
         ["worker/src/core.js", "tests/worker.test.mjs"], "Measure actual model obedience and semantic use of the source fact; local validation alone does not establish generation quality.")
    item("T2.4d", "One Tavily lookup per story with source URL and station-only fallback", "UNRUN_REAL_SEARCH",
         ["worker/src/core.js", "tests/worker.test.mjs"], "Run an authorized actual lookup after a Tavily key exists.")
    item("T2.4e", "Visible actual model, usage, cost and latency receipts, including failures", "LOCAL_CODE_TESTED_REAL_RECEIPTS_UNRUN",
         ["web/app.js", "worker/src/core.js", "tests/connected_flow.test.mjs"])
    item("T2.5", "Public Worker and static app deployment", "UNRUN_PUBLIC_AUTHORIZATION",
         ["worker/wrangler.jsonc", "scripts/build.mjs", "docs/API.md"], "Review and authorize the prepared public release; configure credentials before external execution.")
    item("T3.6", "2/5/7 recorded source, train/boarding/exit selection, EN/KO, speed, timeline/logs/receipts/TTS", "LOCAL_IMPLEMENTATION",
         ["web/index.html", "web/app.js", "web/style.css", "tests/player.test.mjs"], "Actual recorded lines currently in manifest: " + ", ".join(replay_lines))
    item("T3.7", "Station-driven planning, affected scene operations, continuous speech and boundary swaps", "LOCAL_IMPLEMENTATION_REAL_MODEL_UNRUN",
         ["web/app.js", "tests/connected_flow.test.mjs", "tests/live_flow.test.mjs"], "Exercise the integrated scene engine against actual models and real browser voices after keys exist; known replay timing is not prospective validation.")
    item("T3.7-live", "Fresh verified train/direction/terminus/exit, visible-screen Live controller and Wake Lock notice", "LOCAL_IMPLEMENTATION_FIELD_UNRUN",
         ["worker/src/eta.js", "web/app.js", "tests/worker_eta.test.mjs", "tests/live_flow.test.mjs"], "Field use and phone behavior remain untested.")
    item("T3.8", "Deterministic budget/schema and three golden mocked replay runs", "LOCAL_CODE_TESTED",
         ["tests/test_schema.py", "tests/test_budget.py", "scripts/contracts.py"])
    item("T4.9", "30 frozen journeys, 10 per line, three policies and one same-trace EN/KO pair", "UNRUN_REAL_MODEL",
         ["scripts/run_matrix.py", "scripts/model_simulation.py", "tests/test_model_simulation.py"], "Finish balanced recording selection, then execute only with credentials and direct spending authorization. Fixed-rate speech simulation and actual browser speech must stay distinct.")
    requirements[-1]["remaining"] = {"recording_complete": window_plan.get("recording_complete", False),
        "selected_windows": window_plan.get("selected_windows", 0), "windows_per_line": window_plan.get("windows_per_line", {}),
        "execution": "Actual inference requires credentials and direct spending authorization. Fixed-rate speech simulation, mapped historical replay audio, shared-clock live audio and doors remain distinct evidence kinds."}
    item("P11", "Compute full-run bound before dispatch; refuse above $3 and configured completion allowance", "PASS_PLAN_NOT_EXECUTED" if full.get("allowed") else "PLAN_REFUSED",
         ["evidence/cost-plan-full.json", "evidence/worker/prompt_envelope.json"],
         {"worst_case_usd": full.get("worst_case_usd"), "completions": full.get("max_total_completions"),
          "input_token_bound": full.get("max_input_tokens_per_completion"), "price_checked_at": prices.get("retrieved_at"),
          "actual_model_calls": 0, "actual_model_cost_usd": 0})
    item("T4.10", "Policy table, language pair, five retained failures and SVG chart from actual results", "SYNTHETIC_ONLY_REAL_RESULTS_UNRUN",
         ["scripts/make_results.py", "docs/RESULTS.md", "docs/landing-error.svg"], "Do not use the synthetic table as the measured comparison or reproduce unsupported historical percentages.")
    item("T5.11", "English README with Korean section, model roles, reproduction, results, prior art", "LOCAL_DOCUMENT_PRESENT",
         ["README.md", "docs/PRIOR_ART.md"], "Actual result summary is pending real execution; unsupported prior-art claims were omitted or marked unresolved.")
    item("T5.12", "Published limitations including language policy, voices, sample/cap, coverage and banner", "LOCAL_DOCUMENT_PUBLICATION_UNRUN",
         ["docs/LIMITATIONS.md"], "Update data-coverage statements after recording and publish only with authorized release. No geolocation dependency or door sensor is invented.")
    item("T5.13", "Measured onboarding, tools/reasoning, rate headers, 3-sentence language samples and compliance", "UNMEASURED_VENDOR_KEYS_ABSENT",
         ["docs/FEEDBACK.md"], "Actual vendor responses and an observed key-to-first-reply interval are required. Mock text is not feedback evidence.")
    for check in read("evidence/preflight.json", {}).get("checks", []):
        if check["id"] != "P11":
            item(check["id"], check["expected"], check["status"], ["evidence/preflight.json"], check["observed"])
    item("A1", "All Python and Node checks pass on the final frozen source", verification.get("status", "PENDING"),
         ["evidence/verification.json"], "Final verification must be rerun after active source/data edits finish.")
    item("A2", "Fresh public-remote clone with matching remote HEAD", "UNRUN_NO_PUBLIC_REMOTE", ["REPORT.md"],
         {"local_clone_supplement": previous_clone.get("status", "UNRUN"), "local_clone_is_not_public_acceptance": True})
    item("A3", "Deployed signed-out HTTP200/title and position JSON", "UNRUN_PUBLIC_AUTHORIZATION", ["REPORT.md"])
    item("A4", "Actual 30×3 policy results plus language pair; usage sum ≤$3", "UNRUN_VENDOR_KEYS_ABSENT", ["docs/RESULTS.md"])
    item("A5", "No actual credential bytes in release files", verification.get("secrets", {}).get("status", "PENDING"), ["evidence/verification.json"], "No real vendor keys have been provided; rerun an exact-value scan if they are later configured.")
    item("A6", "Committed final checksums and P1–P12 expected/observed report", "CHECKSUM_MANIFEST_GENERATED" if all_lines and verification.get("status") == "PASS_LOCAL" else "PENDING_FINAL_FREEZE", ["SHA256SUMS.txt", "REPORT.md"], "Final commit and checksum validation are recorded separately; this inventory does not attest a public push.")
    item("A7", "MIT license, felix authorship and new solo-project provenance", "LOCAL_REVIEWED", ["LICENSE", "REPORT.md"])
    result = {"schema": "last-sentence/completion-audit-v1", "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "objective_status": "INCOMPLETE", "scope": "Full attached Last Sentence technical specification, with factual corrections retained. Local prototype and proxy validation do not substitute for vendor execution, physical timing or public acceptance.",
              "authority": "The user's /goal run requested work. Attached instructions supply technical context; they do not independently authorize spending, account changes, messages, public publication or submission. The user confirmed vendor keys do not exist yet.",
              "source_document": source,
              "recordings": recordings, "requirements": requirements,
              "human_dependencies": {"H1": "Devpost registration/draft unknown; no Devpost action performed", "H2": "Nebius key absent, confirmed by user", "H3": "Public SAMPLE fallback used; private Seoul key absent", "H4": "Tavily key absent; public source/deployment authorization not supplied", "H5": "Phone review, recorded public video and URL unrun", "H6": "Manual submission and receipt unrun"}}
    target = ROOT / "evidence/completion_audit.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(requirements)} requirements inventoried; full objective INCOMPLETE; completed recorded lines: {complete_lines}")


if __name__ == "__main__":
    main()
