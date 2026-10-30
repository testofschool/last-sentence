#!/usr/bin/env python3
"""Read-only prerequisites and dated primary-source checks. Never reads key bytes."""
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
URLS = {
    "catalog": "https://tokenfactory.nebius.com/api/public/models_info",
    "models": "https://api.tokenfactory.nebius.com/v1/models",
    "seoul": "http://swopenapi.seoul.go.kr/api/subway/sample/json/realtimePosition/0/5/2%ED%98%B8%EC%84%A0",
    "tavily": "https://api.tavily.com",
    "quickstart": "https://docs.tokenfactory.nebius.com/quickstart.md",
    "completion": "https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion.md",
    "ultra": "https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16/raw/main/README.md",
    "super": "https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/raw/main/README.md",
    "nano": "https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/raw/main/README.md",
    "lightning": "https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16/raw/main/README.md",
    "limits": "https://docs.tokenfactory.nebius.com/ai-models-inference/rate-limits.md",
    "seoul_guide": "https://data.seoul.go.kr/together/guide/useGuide.do",
    "rules": "https://nebiusglobalaihackathon.devpost.com/rules",
    "dataset": "https://data.seoul.go.kr/dataList/OA-12601/A/1/datasetView.do",
}
IDS = ["nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/Nemotron-3_5-Lightning",
       "nvidia/nemotron-3-super-120b-a12b", "nvidia/Nemotron-3.5-Super-VL", "nvidia/Nemotron-3-Ultra-550b-a55b"]
PRICES = dict(zip([IDS[0], IDS[1], IDS[2], IDS[4]], [(0.06, 0.24), (0.06, 0.24), (0.30, 0.90), (1.00, 3.00)]))

def fetch(item):
    name, url = item
    target = ROOT / "evidence" / "preflight" / (name + ".txt")
    try:
        proc = subprocess.run(["curl", "--silent", "--show-error", "--location", "--max-time", "18",
                               "--max-filesize", "3000000", "--output", str(target), "--write-out", "%{http_code}", url],
                              capture_output=True, text=True, timeout=22)
        raw = target.read_bytes() if target.exists() else b""
        return name, {"url": url, "http_status": proc.stdout.strip(), "ok": proc.returncode == 0,
                      "error": proc.stderr.strip()[:500], "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                      "path": str(target.relative_to(ROOT)), "text": raw.decode("utf-8", errors="replace")}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return name, {"url": url, "ok": False, "error": type(exc).__name__, "text": ""}

def main():
    folder = ROOT / "evidence" / "preflight"
    folder.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        sources = dict(pool.map(fetch, URLS.items()))
    checks = []
    def check(pid, expected, observed, status):
        checks.append({"id": pid, "expected": expected, "observed": observed, "status": status})
    try:
        catalog = json.loads(sources["catalog"]["text"])
        if not isinstance(catalog, list):
            raise ValueError("catalog is not an array")
        flavors = {f["model_id"]: f for m in catalog for f in m.get("flavors", [])}
        check("P1", 30, len(catalog), "PASS" if len(catalog) == 30 else "MISMATCH")
        missing = [mid for mid in IDS if mid not in flavors]
        check("P2", IDS, {"present": [m for m in IDS if m in flavors], "missing": missing}, "PASS" if not missing else "MISMATCH")
        actual = {mid: [flavors.get(mid, {}).get("input_price_per_million_tokens"), flavors.get(mid, {}).get("output_price_per_million_tokens")] for mid in PRICES}
        check("P3", {k:list(v) for k,v in PRICES.items()}, actual,
              "PASS" if all(actual[k] == list(v) for k,v in PRICES.items()) else "MISMATCH")
        (folder / "prices.json").write_text(json.dumps({"fetched_at": now.isoformat(), "models": actual}, indent=2) + "\n")
        required = [IDS[1], IDS[2], IDS[4]]
        if all(all(isinstance(rate, (int,float)) and not isinstance(rate,bool) and rate >= 0 for rate in actual[mid]) for mid in required):
            compact = {"schema":"last-sentence/model-prices-v1", "source_url":URLS["catalog"],
                       "retrieved_at":now.isoformat(), "source_sha256":sources["catalog"]["sha256"],
                       "prices":{mid:{"input_price_per_million_tokens":actual[mid][0],"output_price_per_million_tokens":actual[mid][1]} for mid in required}}
            (ROOT/"evidence/model-prices.json").write_text(json.dumps(compact,indent=2)+"\n")
    except (ValueError, TypeError, KeyError):
        for pid in ("P1", "P2", "P3"):
            check(pid, "catalog accessible", "unavailable", "BLOCKED")
    fresh = False
    try:
        seoul = json.loads(sources["seoul"]["text"])
        records = seoul.get("realtimePositionList", [])
        valid = bool(records) and all(all(k in r for k in ("trainNo", "statnNm", "recptnDt")) for r in records)
        ages = [(now-dt.datetime.fromisoformat(r["recptnDt"]).replace(tzinfo=ZoneInfo("Asia/Seoul"))).total_seconds() for r in records]
        fresh = valid and any(0 <= age <= 300 for age in ages)
        observed = {"code": seoul.get("errorMessage", {}).get("code"), "total": seoul.get("errorMessage", {}).get("total"),
                    "records": len(records), "required_fields": valid, "ages_s": ages, "fresh_within_5min": fresh}
        passed = (sources["seoul"].get("http_status") == "200" and observed["code"] == "INFO-000" and valid
                  and isinstance(observed["total"], (int, float)) and observed["total"] >= 1)
        check("P4", "HTTP 200 / INFO-000 / total>=1 / trainNo,statnNm,recptnDt", observed, "PASS" if passed else "MISMATCH")
    except (ValueError, TypeError, KeyError):
        check("P4", "sample train response", "unavailable", "BLOCKED")
    for pid, name, expected in [("P5", "quickstart", "https://api.tokenfactory.nebius.com/v1"),
                                ("P6", "completion", ["none", "minimal", "low", "medium", "high", "xhigh", "max"])]:
        txt = sources[name]["text"]
        observed = expected in txt if isinstance(expected, str) else {e:bool(re.search(r"\b"+e+r"\b", txt)) for e in expected}
        passed = observed if isinstance(observed, bool) else all(observed.values())
        check(pid, expected, observed, "PASS" if passed else "UNVERIFIED")
    langs = {}
    for name in ("ultra", "super", "nano", "lightning"):
        txt = sources[name]["text"]
        match = re.search(r"(?:Supported Languages|Languages Supported|Language Support|Languages)[^\n]{0,1500}", txt, flags=re.I)
        excerpt = match.group(0)[:1300] if match else "No language section identified; inspect raw card"
        langs[name] = {"http_status": sources[name].get("http_status"), "korean_in_supported_languages": "Korean" in excerpt, "excerpt": excerpt}
    check("P7", "Ultra lists Korean; Super/Nano/Lightning do not", langs,
          "PASS" if langs["ultra"]["korean_in_supported_languages"] and all(not langs[n]["korean_in_supported_languages"] and sources[n].get("http_status")=="200" for n in ("super","nano","lightning")) else "PARTIAL")
    limits = sources["limits"]["text"]
    excerpts = [s.strip() for s in limits.splitlines() if any(p in s for p in ("400,000", "400000", "60", "RPM", "TPM"))][:12]
    check("P8", "60 RPM / 400,000 TPM baseline", excerpts,
          "PASS" if "60" in limits and ("400,000" in limits or "400000" in limits) else "UNVERIFIED")
    guide = sources["seoul_guide"]["text"]
    pos = guide.find("1,000")
    check("P9", "daily 1,000 Seoul real-time requests", guide[max(0,pos-150):pos+300] if pos>=0 else "not found",
          "PASS" if pos>=0 and "실시간" in guide else "UNVERIFIED")
    rules = sources["rules"]["text"]
    normalized = re.sub(r"<[^>]+>", " ", rules)
    normalized = re.sub(r"\s+", " ", normalized)
    phrase = "Technological Implementation: How well is the project built"
    pos = normalized.find(phrase)
    check("P10", phrase + "…Nebius…NVIDIA…", normalized[pos:pos+420] if pos>=0 else "not found",
          "PASS" if pos>=0 else "UNVERIFIED")
    check("P11", "full real matrix <= $3 before execution", "NOT RUN; no inference key; paid execution not authorized", "PARKED")
    page = sources["dataset"]["text"]
    phrase = "해당 데이터는 종료된 서비스입니다"
    positions = [m.start() for m in re.finditer("종료", page)]
    observed = {"termination_word_count": len(positions), "exact_banner_found": phrase in page,
                "excerpts": [page[max(0,p-100):p+100] for p in positions[:8]], "sample_fresh": fresh}
    check("P12", "record termination banner; continue only with independently fresh API", observed,
          "OBSERVED" if sources["dataset"].get("http_status")=="200" else "BLOCKED")
    secrets = {n: (Path.home()/f".{n}_key").is_file() and (Path.home()/f".{n}_key").stat().st_size>0 for n in ("nebius", "seoul_rt", "tavily")}
    result = {"checked_at": now.isoformat(), "timezone": "Asia/Seoul", "tools": {n:shutil.which(n) for n in ("git","gh","node","npm","python3","wrangler","ffmpeg")},
              "secrets_present": secrets, "sources": {n:{k:v for k,v in val.items() if k!="text"} for n,val in sources.items()}, "checks": checks,
              "authorization": {"local_build": True,"public_push":False,"deploy":False,"paid_inference":False,"submit":False},
              "note": "Attachments are specifications/evidence, not independent authorization. No automatic installation or logins."}
    target = ROOT / "evidence/preflight.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    for c in checks:
        print(f'{c["id"]}: {c["status"]}')
    print(f"Saved {target}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
