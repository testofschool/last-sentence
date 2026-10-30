#!/usr/bin/env python3
"""Render a matrix without turning fixtures into real-world evidence."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import shlex
import statistics

from run_matrix import SUPER, ULTRA, policy_coverage


def table_text(value):
    return html.escape(str(value), quote=False).replace("|", "\\|").replace("`", "&#96;").replace("\n", " ").replace("\r", " ")


def metric(value, suffix="", digits=1):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return "UNMEASURED"
    return f"{value:.{digits}f}{suffix}"


def writer_identity(row):
    requested = row.get("writer_models_requested", [])
    reported = row.get("writer_models_reported", [])
    verified = row.get("model_identities_verified") is True
    if not requested and not reported:
        calls = [call for receipt in row.get("receipts", []) for call in receipt.get("calls", [receipt])]
        writers = [call for call in calls if call.get("requested_model", call.get("model")) in (SUPER, ULTRA)]
        requested = sorted({call.get("requested_model") for call in writers if isinstance(call.get("requested_model"), str)})
        reported = sorted({call.get("provider_reported_model") for call in writers if isinstance(call.get("provider_reported_model"), str)})
        verified = bool(writers) and all(call.get("identity_match") is True and
            call.get("requested_model") == call.get("provider_reported_model") for call in writers)
    if not verified or not requested or requested != reported:
        return "UNVERIFIED"
    return ", ".join({SUPER: "Super", ULTRA: "Ultra"}.get(model, model) for model in reported)


def language_pair_section(matrix):
    pair = matrix.get("language_pair", [])
    lines = ["## English / Korean comparison", ""]
    if not pair:
        return lines + ["**UNRUN.** No completed same-journey EN/Super and KO/Ultra pair is recorded. No language results are inferred from fixtures.", ""]
    fields = ("id", "line", "trainNo", "exit_station", "policy")
    paired = len(pair) == 2 and {row.get("lang") for row in pair} == {"en", "ko"} and all(
        pair[0].get(field) is not None and pair[0].get(field) == pair[1].get(field) for field in fields)
    for key in ("arrival_at", "arrival_proxy_s", "speech_clock", "controller_policy"):
        if any(key in row for row in pair):
            paired = paired and all(row.get(key) is not None and row.get(key) == pair[0].get(key) for row in pair)
    if paired:
        lines += [f"Both rows cover the same frozen journey `{table_text(pair[0]['id'])}` and policy. "
                  "This is a two-run descriptive comparison, not a language-quality score or independent evidence of door timing.", ""]
    else:
        lines += ["**INCOMPLETE_PAIR.** Available rows do not establish one EN and one KO result on the same journey, policy and clock. They must not be described as a paired comparison.", ""]
    if matrix.get("execution_transport") == "injected-test-transport":
        lines += ["Injected test transport: the values below are mocked, not actual provider measurements.", ""]
    if matrix.get("mode") == "model-backed-timing-simulation":
        lines += ["Speech timing uses the declared character-rate simulation; browser TTS remains unmeasured by this table.", ""]
    lines += ["| Language | Writer reported with matching identity | Landing error | Cost/story | Tokens | Call p50 | Call p95 |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for row in sorted(pair, key=lambda value: str(value.get("lang", ""))):
        cost = metric(row.get("cost_usd"), digits=6)
        lines.append(f"| {table_text(row.get('lang', 'unknown'))} | {table_text(writer_identity(row))} | "
                     f"{metric(row.get('landing_error_s'), ' s')} | {'$'+cost if cost != 'UNMEASURED' else 'UNKNOWN'} | "
                     f"{metric(row.get('tokens'), digits=0)} | {metric(row.get('p50_latency_ms'), ' ms')} | {metric(row.get('p95_latency_ms'), ' ms')} |")
    lines += ["", "| Language | Conductor completions | Writer attempts | Tool calls supported | Tavily result |",
              "|---|---:|---:|---|---|"]
    for row in sorted(pair, key=lambda value: str(value.get("lang", ""))):
        flag = lambda value: str(value).lower() if isinstance(value, bool) else "not recorded"
        lines.append(f"| {table_text(row.get('lang', 'unknown'))} | {metric(row.get('conductor_calls'), digits=0)} | "
                     f"{metric(row.get('writer_calls'), digits=0)} | {flag(row.get('tool_calls_supported'))} | {flag(row.get('tavily_ok'))} |")
    return lines + ["", "Writer identities require explicit matching requested/provider-reported IDs in the receipts. Unknown provenance or cost is never converted to an expected model or zero spend. The original matrix retains full receipts and clock provenance.", ""]


def observed_eta_section(eta, quality, line=None):
    title="## Observed ETA proxy validation"+(f" · {line}" if line else "")
    lines = [title, "",
             "This section describes recorded station-arrival ETA validation. "
             "It is separate from the story-policy comparison above and does not measure "
             "Nemotron story generation, browser speech timing, or model-backed story landing accuracy.", ""]
    if eta:
        median = eta.get("median_relative_error")
        error = f"{median:.4%}" if isinstance(median, (int, float)) else "UNAVAILABLE"
        passed = eta.get("gate_lte_15_percent")
        gate = "PASS" if passed is True else "FAIL" if passed is False else "UNAVAILABLE"
        lines += ["| Recorded ETA measure | Value |", "|---|---:|",
                  f"| Eligible held-out forecast windows | {eta.get('n', 0)} |",
                  f"| Train identities represented by arrival chains | {eta.get('train_identities', 0)} |",
                  f"| Median relative error | {error} |",
                  f"| Registered median error ≤15% gate | {gate} |", "",
                  f"Method: `{eta.get('method', 'unspecified')}`. Status: `{eta.get('status', 'unspecified')}`. "
                  "Forecast windows can overlap and reuse stations within a train identity; "
                  "the window count is not a count of independent journeys or independent samples. "
                  "The complete held-out train identity is excluded from fitting. "
                  "No result here establishes performance on unobserved routes or operating periods.", ""]
    else:
        lines += ["Recorded ETA validation artifact: **UNAVAILABLE**.", ""]
    if quality:
        ages = quality.get("receipt_timestamp_age_s", {})
        def seconds(value):
            return f"{value:g} s" if isinstance(value, (int, float)) else "UNAVAILABLE"
        lines += [f"Receipt timestamp age: **p50 {seconds(ages.get('p50'))} / p95 {seconds(ages.get('p95'))}** "
                  f"across **{ages.get('n', 0)} repeated polling records**. "
                  "This is polled `ts` minus provider `recptnDt`: timestamp age, **not network lag, transport delay, "
                  "or door-open offset**. Repeated polls are not independent journeys.", "",
                  f"Trace snapshot: {quality.get('observation_records', 0)} observation records, "
                  f"{quality.get('distinct_polls_from_line_and_ts', 0)} distinct polls, "
                  f"{quality.get('gap_records', 0)} gap records. "
                  f"Recording marked partial: `{quality.get('sampling', {}).get('partial', 'unknown')}`.", ""]
    else:
        lines += ["Trace-quality artifact: **UNAVAILABLE**.", ""]
    snapshots = {}
    if eta and eta.get("trace_sha256"):
        snapshots["ETA artifact"] = eta["trace_sha256"]
    if quality and quality.get("trace_sha256"):
        snapshots["Trace-quality artifact"] = quality["trace_sha256"]
    if quality and quality.get("trace_path"):
        trace_path = Path(quality["trace_path"])
        if trace_path.is_file():
            snapshots["Current local trace"] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    if len(snapshots) >= 2 and len(set(snapshots.values())) > 1:
        lines += ["**Snapshot mismatch:** the ETA, trace-quality, or current local trace hashes differ. "
                  "These values describe different recording snapshots. Refresh both artifacts after recording ends "
                  "before treating them as one fixed sample.", ""]
    elif eta and quality and "ETA artifact" in snapshots and "Trace-quality artifact" in snapshots:
        lines += ["ETA and trace-quality artifacts reference the same trace snapshot" +
                  (", also matching the current local trace." if "Current local trace" in snapshots else "."), ""]
    else:
        lines += ["Snapshot alignment is unverified because one or both artifact trace hashes are missing.", ""]
    if snapshots:
        lines += ["| Snapshot | SHA-256 |", "|---|---|"]
        lines += [f"| {name} | `{value}` |" for name, value in snapshots.items()]
        lines += [""]
    return lines


def reproduction_section(matrix, output, matrix_path=None, matrix_sha256=None):
    lines = ["## Reproduce", ""]
    if matrix.get("mode") not in ("model-backed-timing-simulation", "recorded-browser-measurements"):
        return lines + ["```sh",
            "python3 scripts/run_matrix.py --mode plan --journeys 30 --max-completions 2048 --out evidence/cost-plan-full.json",
            "python3 scripts/run_matrix.py --mode simulation --out evidence/simulation-matrix.json",
            "python3 scripts/make_results.py evidence/simulation-matrix.json", "```", ""]
    lines += ["Re-render the retained results from the repository root. This makes no inference requests "
              "and does not replace the input with a synthetic fixture.", "",
              f"Retained mode: `{table_text(matrix['mode'])}`; execution transport: "
              f"`{table_text(matrix.get('execution_transport', 'not recorded'))}`.", "",
              f"Trace SHA-256 recorded by the matrix: `{table_text(matrix.get('trace_sha256', 'not recorded'))}`.", "",
              f"Trace source path recorded by the matrix: `{table_text(matrix.get('trace_path', 'not recorded'))}`.", ""]
    if matrix_path is None:
        return lines + ["The retained matrix source path was not supplied to this renderer; "
                        "no executable reproduction command is invented.", ""]
    if matrix_sha256 is None:
        matrix_sha256 = hashlib.sha256(Path(matrix_path).read_bytes()).hexdigest()
    return lines + [f"Retained matrix: `{table_text(matrix_path)}`; SHA-256: `{matrix_sha256}`.", "", "```sh",
                    f"python3 scripts/make_results.py {shlex.quote(str(matrix_path))} --out {shlex.quote(str(output))}",
                    "```", ""]


def render(matrix, output, eta_evaluation=None, trace_quality=None, line_evidence=None, *, matrix_path=None, matrix_sha256=None):
    rows = matrix.get("rows", [])
    measured = matrix.get("mode") == "recorded-browser-measurements"
    model_simulated = matrix.get("mode") == "model-backed-timing-simulation"
    kind = "Recorded browser measurements" if measured else "Model-backed timing simulation" if model_simulated else "Synthetic timing simulation"
    coverage = matrix.get("coverage") or policy_coverage(rows)
    cost = matrix.get("actual_api_cost_usd", 0)
    cost_text = f"${cost:.6f}" if isinstance(cost, (int, float)) else "UNKNOWN (incomplete usage receipts)"
    execution = (f"Completed simulation runs: **{matrix.get('completed_simulation_runs', len(rows))}**. "
                 f"Inference dispatch attempts: **{matrix.get('inference_dispatch_attempts', 0)}**. "
                 f"Measured TTS runs: **{matrix.get('measured_tts_runs', 0)}**. Status: **{matrix.get('status', 'unspecified')}**. "
                 if model_simulated else f"Measured inference runs: **{matrix.get('measured_inference_runs', 0)}**. ")
    lines = ["# Results", "", f"**{kind}.**", "", matrix["notice"], "",
             execution + f"Rows in this table: **{len(rows)}**. Actual API cost represented: **{cost_text}**.", "",
             f"Paired coverage: **{coverage['complete_paired_journeys']} of {coverage['journeys']} journeys** have all three policies. "
             f"Unpaired journeys: **{coverage['unpaired_journeys']}**. Comparison basis: **{coverage['comparison_basis']}**.", "",
             "The table below is descriptive. Policy groups contain unpaired journeys and must not be treated as a controlled same-journey comparison." if coverage["unpaired_journeys"] else
             "All policy groups below cover the same journey fixtures or frozen observed journeys.", "",
             ("Coverage below contains completed timing simulations on recorded windows, not measured audio. "
              f"EN/KO pair rows: {len(matrix.get('language_pair', []))}. Failures/attempts remain in the source matrix." if model_simulated else
              "The full 30-journey × 3-policy evaluation and EN/KO model pair are **UNRUN**." if not measured else
              "Coverage below is the set imported from recorded measurements."), "",
             "| Policy | n | ≤30 s | ≤10 s | Median absolute error | Cost/story | Median story call p50 | Median story call p95 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for policy in ("fixed_clip", "single_fit", "sentence_replan"):
        group = [r for r in rows if r["policy"] == policy]
        if not group:
            continue
        errors = [abs(r["landing_error_s"]) for r in group]
        latencies = [r["p50_latency_ms"] for r in group if r["p50_latency_ms"] is not None]
        latency = f"{statistics.median(latencies):.1f} ms" if latencies else "UNMEASURED"
        p95 = [r.get("p95_latency_ms") for r in group if isinstance(r.get("p95_latency_ms"), (int, float))]
        tail = metric(statistics.median(p95), " ms") if p95 else "UNMEASURED"
        lines.append(f"| {policy} | {len(group)} | {sum(e <= 30 for e in errors) / len(errors):.1%} | "
                     f"{sum(e <= 10 for e in errors) / len(errors):.1%} | {statistics.median(errors):.1f} s | "
                     f"${statistics.mean(r['cost_usd'] for r in group):.6f} | {latency} | {tail} |")
    lines += ["", "Latency summaries are medians of each story's call-latency quantile; they are not pooled call percentiles.", ""]
    lines += language_pair_section(matrix)
    lines += ["", "Positive error means the story ended after the arrival proxy; negative means before it.", "",
              "![Landing error by policy](landing-error.svg)", "",
              "## Interpretation", "",
              "The fixture controller uses a boarding forecast of 600 seconds and a historical segment forecast of 150 seconds. "
              "Only station events already observed at a sentence boundary can revise the forecast. "
              "The final arrival timestamp is withheld from scheduling and used only to score the result. "
              "Mocked speech lasts 12 seconds per sentence. These assumptions do not establish Nemotron, TTS, live-train, or door-open accuracy." if not measured and not model_simulated else
              "Text comes from protected Worker model calls; speech duration is estimated from a fixed Unicode-character rate. "
              "Measured HTTP latency advances the simulation clock, and revisions take effect at sentence boundaries. "
              "Forecasts fit only other train identities. Only observed station timestamps reach the controller; final arrival is withheld for scoring. "
              "Offline request pacing and public-price audit waits count in real session runtime but are excluded from this speech simulation. "
              "This is not browser speech, forward-in-time ETA, semantic story-quality, or door-open validation." if model_simulated else
              "The arrival event is the provider's station-arrival status. Polling and provider latency are not removed. "
              "Browser speech-end timestamps reflect the imported browser session. Historical replay retains its explicit uninterrupted 1× playback-origin mapping; "
              "known-clock replay audio does not establish prospective ETA or door-open accuracy and must not be generalized to all devices.", "",
              "A numerical comparison with the earlier handoff's simulation is unavailable: its uncertainty model and data were not reproduced here.", ""]
    lines += observed_eta_section(eta_evaluation, trace_quality,"2호선")
    for evidence in line_evidence or []:
        if evidence.get("eta") is not None or evidence.get("quality") is not None:
            lines += observed_eta_section(evidence.get("eta"),evidence.get("quality"),evidence["line"])
    if model_simulated:
        lines += [f"Offline pacing: `{matrix.get('pacing',{}).get('rpm',45)} RPM / {matrix.get('pacing',{}).get('tpm',300000)} TPM`, "
                  f"waited `{matrix.get('pacing',{}).get('wait_s',0):.3f} s`, "
                  f"real runtime ceiling `{matrix.get('max_execution_seconds',7200)} s`. "
                  "Pacing reserves worst-case completion groups/input+output tokens and assumes no competing account traffic. "
                  "These artificial experiment waits are excluded from simulated speech timing. Provider failures remain failures.", ""]
        lines += ["## Model execution failures", "", "```json", json.dumps(matrix.get("failures", []), ensure_ascii=False, indent=2), "```", "",
                  "All attempted calls, including failures and unknown usage/cost, are retained in the source matrix's `attempts` array. "
                  "An aborted run with incomplete receipts is never reported as zero spend.", ""]
    lines += [
              "## Five largest absolute errors", "",
              "Largest errors among completed scored rows, retained verbatim. Unscored execution failures have no invented landing error; "
              "they remain in the separate failures/attempts records and model-failure section when applicable:", "", "```json",
              json.dumps(sorted(rows, key=lambda r: abs(r["landing_error_s"]), reverse=True)[:5], ensure_ascii=False, indent=2),
              "```", ""]
    lines += reproduction_section(matrix, output, matrix_path, matrix_sha256)
    lines += [
              "Planning uses the saved live model catalog and includes all Conductor fallback attempts. "
              "Both the dollar ceiling and the default 300 lifetime completion ceiling are checked; "
              "5 journeys × 3 policies plus 2 language runs have a conservative 295-completion bound. "
              "The full 30-journey plan plus language pair requires 1,370 maximum completions and an explicitly configured "
              "Worker ceiling of 2,048; its 16,384-token input envelope is enforced before every completion. "
              "At the checked prices its bound is $2.60596288, within the same $3 guard. This is planning, not execution. "
              "The guarded runner inspects authorized Worker status for remaining "
              "capacity before beginning and before every inference dispatch. A denied plan exits with code 2 and makes no requests. "
              "Default modes make no inference requests. `--mode model-simulation` requires `--execute`, "
              "`--ack-cost 3`, a protected session-token file, a price snapshot checked within one hour, and an inference-ready Worker. "
              "The full experiment defaults to a real-runtime ceiling of 7,200 seconds (`--max-runtime-s`, maximum 7,200). "
              "Conservative 45RPM/300000TPM offline pacing counts in that runtime but is excluded from simulated speech time. "
              "Public prices are revalidated after one hour; changed/unavailable rates stop further dispatch without raising the acknowledged cost bound. "
              "Each inference request also supplies acknowledged rates to a Worker advertising expected-pricing support; "
              "the Worker checks a fresh public catalog before each completion attempt and refuses a changed rate before reservation/provider dispatch. "
              "For actual timing results, instrument browser speech-end events and import them with "
              "`run_matrix.py --mode measured --measurements FILE --trace RECORDED.jsonl`. "
              "The importer requires matching trace SHA-256, actual arrival records, complete usage/cost/latency receipts, "
              "and a total cost no higher than $3.00. Character-count speech estimates are rejected as measured audio.", ""]
    if measured or model_simulated:
        lines += ["Starting a new data acquisition is a separate experiment, not the retained-results reproduction above. "
                  "Any model-backed rerun requires the guarded runner's explicit `--execute` and cost acknowledgement, "
                  "fresh prices, protected credentials and sufficient remaining cumulative budget/call capacity. "
                  "Choose a fresh output filename; never overwrite or automatically retry the retained matrix. "
                  "New browser-speech measurements additionally require actual instrumented speech events; "
                  "model-backed timing simulation cannot replace them.", ""]
    else:
        lines += ["Model-backed timing simulation example (requires separately authorized execution and configured credentials):", "", "```sh",
              "python3 scripts/run_matrix.py --mode model-simulation --journeys 30 --max-completions 2048 \\",
              "  --trace web/replay/trace_2026-10-30_all_lines.jsonl --catalog evidence/model-prices.json \\",
              "  --worker-url https://YOUR-WORKER.example --session-key-file ~/.last_sentence_session \\",
              "  --execute --ack-cost 3 --max-runtime-s 7200 --out evidence/model-simulation-run.json", "```", "",
              "Refresh the public price snapshot first with `python3 -I scripts/preflight.py`. "
              "This command was not executed in the keyless build. It writes real call receipts alongside simulated timing; "
              "the output is never accepted as measured browser/audio landing performance. A fresh public catalog check is not atomic with provider billing.", ""]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    chart(output.with_name("landing-error.svg"), rows, kind)


def chart(path, rows, kind):
    width, row_height = 840, 34
    height = 100 + row_height * len(rows)
    maximum = max([abs(r["landing_error_s"]) for r in rows] + [30])
    scale = 220 / maximum
    middle = 530
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#f7f7f4"/>',
           f'<text x="24" y="30" font-family="system-ui" font-size="18">{html.escape(kind)} · landing error (seconds)</text>',
           f'<line x1="{middle}" y1="50" x2="{middle}" y2="{height - 20}" stroke="#777"/>']
    for i, row in enumerate(rows):
        y = 70 + i * row_height
        value = row["landing_error_s"]
        endpoint = middle + value * scale
        x, bar_width = min(middle, endpoint), max(1, abs(value * scale))
        label = html.escape(row["id"] + " · " + row["policy"])
        svg += [f'<text x="24" y="{y}" font-family="system-ui" font-size="12">{label}</text>',
                f'<rect x="{x:.1f}" y="{y-13}" width="{bar_width:.1f}" height="18" fill="#396b57"/>',
                f'<text x="{endpoint + 8 if value >= 0 else endpoint - 42:.1f}" y="{y}" font-family="system-ui" font-size="12">{value:+.1f}</text>']
    svg.append("</svg>")
    Path(path).write_text("\n".join(svg) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--out", type=Path, default=Path("docs/RESULTS.md"))
    parser.add_argument("--eta-evaluation", type=Path, default=Path("evidence/eta_evaluation.json"))
    parser.add_argument("--trace-quality", type=Path, default=Path("evidence/trace_quality.json"))
    for number in (5,7):
        parser.add_argument(f"--eta-evaluation-{number}",type=Path,default=Path(f"evidence/eta_evaluation_{number}.json"))
        parser.add_argument(f"--trace-quality-{number}",type=Path,default=Path(f"evidence/trace_quality_{number}.json"))
    args = parser.parse_args()
    eta = json.loads(args.eta_evaluation.read_text()) if args.eta_evaluation.is_file() else None
    quality = json.loads(args.trace_quality.read_text()) if args.trace_quality.is_file() else None
    line_evidence=[]
    for number in (5,7):
        eta_path=getattr(args,f"eta_evaluation_{number}");quality_path=getattr(args,f"trace_quality_{number}")
        line_evidence.append({"line":f"{number}호선","eta":json.loads(eta_path.read_text()) if eta_path.is_file() else None,
                              "quality":json.loads(quality_path.read_text()) if quality_path.is_file() else None})
    matrix_raw = args.matrix.read_bytes()
    render(json.loads(matrix_raw), args.out, eta, quality,line_evidence,
           matrix_path=args.matrix, matrix_sha256=hashlib.sha256(matrix_raw).hexdigest())
    print(args.out)


if __name__ == "__main__":
    main()
