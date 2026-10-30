#!/usr/bin/env python3
"""Record Seoul sample observations. Gaps are records, never invented trains.

The API's trainSttus=1 is a station-arrival observation, not a door sensor.
Use --key SAMPLE or --key-file PATH; real keys never enter argv or output.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

KST = dt.timezone(dt.timedelta(hours=9))
FIELDS = ("subwayId", "trainNo", "statnId", "statnNm", "updnLine", "trainSttus", "recptnDt")


def now():
    return dt.datetime.now(KST).isoformat(timespec="seconds")


def poll(line, key="sample", timeout=12, opener=urllib.request.urlopen):
    url = "http://swopenapi.seoul.go.kr/api/subway/" + urllib.parse.quote(key, safe="")
    url += "/json/realtimePosition/0/5/" + urllib.parse.quote(line)
    try:
        with opener(url, timeout=timeout) as response:
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                return None, "response-too-large"
            body = json.loads(payload)
    except urllib.error.HTTPError as exc:
        return None, "HTTP-" + str(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return None, type(exc).__name__
    if not isinstance(body, dict):
        return None, "invalid-schema"
    status = body.get("errorMessage", {})
    if not isinstance(status, dict):
        return None, "invalid-schema"
    if status.get("code") != "INFO-000":
        return None, str(status.get("code", "invalid-schema"))[:80]
    rows = body.get("realtimePositionList")
    if not isinstance(rows, list):
        return None, "invalid-record-list"
    return [{k: row.get(k) for k in FIELDS} for row in rows if isinstance(row, dict)], None


def record(output, line, minutes=40, interval=20, key="sample", max_polls=None, fallback_key=None):
    if minutes <= 0 or interval <= 0 or (max_polls is not None and max_polls < 1):
        raise ValueError("minutes and interval must be positive")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"schema": "last-sentence/trace-v1", "source": "seoul-sample" if key == "sample" else "seoul-api",
                "line": line, "started_at": now(), "planned_minutes": minutes,
                "interval_s": interval, "polls": 0, "observations": 0, "gaps": 0,
                "complete": False, "arrival_event": "station-arrival-proxy"}
    metadata_path = output.with_suffix(".meta.json")
    deadline = time.monotonic() + minutes * 60
    consecutive_errors = 0
    try:
        with output.open("a", encoding="utf-8") as stream:
            while time.monotonic() < deadline:
                begun = time.monotonic()
                rows, error = poll(line, key)
                ts = now()
                metadata["polls"] += 1
                if error:
                    consecutive_errors += 1
                    records = [{"ts": ts, "source": metadata["source"], "line": line, "gap": True, "error": error}]
                    metadata["gaps"] += 1
                else:
                    consecutive_errors = 0
                    records = [dict(row, ts=ts, line=line, source=metadata["source"], poll=metadata["polls"]) for row in rows]
                    metadata["observations"] += len(records)
                    if not records:
                        records = [{"ts": ts, "source": metadata["source"], "line": line, "gap": True, "error": "empty-poll"}]
                        metadata["gaps"] += 1
                for row in records:
                    stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                metadata["last_poll_at"] = ts
                if consecutive_errors > 3 and key == "sample" and fallback_key and fallback_key.upper() != "SAMPLE":
                    key = fallback_key
                    metadata["source"] = "seoul-api"
                    metadata["fallback_used"] = True
                    consecutive_errors = 0
                metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                if max_polls is not None and metadata["polls"] >= max_polls:
                    break
                time.sleep(max(0, min(interval - (time.monotonic() - begun), deadline - time.monotonic())))
        metadata["complete"] = max_polls is None or time.monotonic() >= deadline
    except KeyboardInterrupt:
        metadata["interrupted"] = True
    finally:
        metadata["finished_at"] = now()
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line", default="2호선", choices=["2호선", "5호선", "7호선"])
    parser.add_argument("--minutes", type=float, default=40)
    parser.add_argument("--interval", type=float, default=20)
    parser.add_argument("--key", choices=["SAMPLE"], default="SAMPLE")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--fallback-key-file", type=Path, default=Path.home() / ".seoul_rt_key")
    parser.add_argument("--max-polls", type=int)
    parser.add_argument("--out", type=Path, default=Path("web/replay/trace_2026-10-30.jsonl"))
    args = parser.parse_args()
    key = args.key_file.expanduser().read_text().strip() if args.key_file else "sample"
    if key.upper() == "SAMPLE":
        key = "sample"
    fallback_key = args.fallback_key_file.expanduser().read_text().strip() if args.fallback_key_file.expanduser().is_file() else None
    print(json.dumps(record(args.out, args.line, args.minutes, args.interval, key, args.max_polls, fallback_key), ensure_ascii=False))


if __name__ == "__main__":
    main()
