#!/usr/bin/env python3
"""Run local checks and hash stable deliverables. No network, deployment or inference."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(args):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return {"command": args, "exit_code": result.returncode, "stdout": result.stdout[-14000:], "stderr": result.stderr[-4000:]}

def scan_secrets():
    skipped = {".git", "node_modules", ".wrangler", ".local", "__pycache__", ".pytest_cache"}
    files = [p for p in ROOT.rglob("*") if p.is_file() and not any(s in skipped for s in p.relative_to(ROOT).parts)]
    checked = []
    matches = []
    for name in ("nebius", "seoul_rt", "tavily"):
        path = Path.home() / f".{name}_key"
        if not path.is_file() or path.stat().st_size == 0:
            continue
        key = path.read_bytes().strip()
        # SAMPLE is a published placeholder, not a credential.
        if not key or key == b"SAMPLE":
            continue
        checked.append(name)
        for f in files:
            if key in f.read_bytes():
                matches.append(str(f.relative_to(ROOT)))
    return {"status": "FAIL" if matches else "PASS" if checked else "NOT_APPLICABLE_NO_KEYS",
            "key_names_checked": checked, "matching_paths": sorted(set(matches)), "files_scanned": len(files)}

def hashes():
    paths = []
    for folder in ("docs", "web", "scripts", "worker/src", "tests"):
        paths += [p for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [p for p in (ROOT/"evidence").rglob("*") if p.is_file() and p.suffix in (".json", ".png") and p.name != "verification.json"]
    paths += [ROOT / name for name in ("README.md", "LICENSE", "REPORT.md", ".gitignore", "package.json",
              "worker/package.json", "worker/package-lock.json", "worker/wrangler.jsonc",
              "worker/.gitignore", "worker/.dev.vars.example", "worker/.dev.vars.matrix.example")
              if (ROOT / name).is_file()]
    lines = [hashlib.sha256(p.read_bytes()).hexdigest() + "  " + str(p.relative_to(ROOT)) for p in sorted(paths)]
    (ROOT/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n")
    return len(lines)

def main():
    active = []
    for p in sorted((ROOT / "web/replay").glob("*.meta.json")):
        data = json.loads(p.read_text())
        # A concatenated snapshot has source completion times, not its own
        # recorder process or fabricated finish timestamp.
        sources = data.get("recordings") if data.get("line") == "combined" else None
        finished = all(r.get("metadata", {}).get("finished_at") for r in sources) if sources else data.get("finished_at")
        if not finished:
            active.append(str(p.relative_to(ROOT)))
    if active:
        print("Trace recording is still active. Finish it before final verification: " + ", ".join(active), file=sys.stderr)
        return 2
    commands = [[sys.executable, "-m", "pytest", "-q", "tests"],
                ["node", "--test", *[str(p.relative_to(ROOT)) for p in sorted((ROOT/"tests").glob("*.test.mjs"))]],
                ["git", "diff", "--check"], ["git", "diff", "--cached", "--check"]]
    outcomes = [run(c) for c in commands]
    secrets = scan_secrets()
    result = {"verified_at":dt.datetime.now(dt.timezone.utc).isoformat(),"checks":outcomes,"secrets":secrets,"hashed_files":hashes(),
              "network_inference_calls":0,"public_deployment":"UNRUN","remote_clone":"UNRUN_NO_REMOTE"}
    eta_path = ROOT/"evidence/eta_evaluation.json"
    result["eta_validation"] = json.loads(eta_path.read_text()) if eta_path.exists() else None
    result["release_status"] = "HOLD: real inference, observed audio timing and public release are unverified"
    result["status"] = "PASS_LOCAL" if all(r["exit_code"] == 0 for r in outcomes) and secrets["status"] != "FAIL" else "FAIL"
    (ROOT/"evidence/verification.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(result["status"])
    for r in outcomes:
        print(" ".join(r["command"]) + ": " + str(r["exit_code"]))
        print(r["stdout"].strip())
        if r["exit_code"]:
            print(r["stderr"].strip())
    print("Secret scan: " + secrets["status"])
    return 0 if result["status"] == "PASS_LOCAL" else 1

if __name__ == "__main__":
    raise SystemExit(main())
