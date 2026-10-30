import json
import datetime as dt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_replay import build


def test_recorded_manifest_requires_real_contiguous_arrivals(tmp_path):
    rows = []
    for station, value in [("강남", "10:00:00"), ("역삼", "10:02:00"), ("삼성", "10:05:00")]:
        rows.append(dict(ts="2026-10-30T" + value + "+09:00", recptnDt="2026-10-30T" + value + "+09:00", line="2호선", trainNo="42", statnNm=station, updnLine="0", trainSttus="1", source="seoul-sample"))
    path = tmp_path / "trace.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    result = build(path)
    assert result["partial"] is True
    assert len(result["journeys"]) == 1
    journey = result["journeys"][0]
    assert journey["stations"] == [{"name":"강남", "offset_s":0}, {"name":"역삼", "offset_s":120}]
    assert journey["clock_kind"] == "known-recorded-timeline-not-forecast"
    assert journey["forecast_s"] is None


def test_empty_recording_produces_empty_replay_instead_of_fixtures(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text("")
    assert build(path)["journeys"] == []


def test_long_observed_chain_displays_only_five_real_consecutive_stations(tmp_path):
    stations = ["강남", "역삼", "선릉", "삼성", "종합운동장", "잠실새내", "잠실"]
    start = dt.datetime(2026, 10, 30, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    rows = []
    for i, station in enumerate(stations):
        value = (start + dt.timedelta(seconds=120 * i)).isoformat()
        rows.append(dict(ts=value,recptnDt=value,line="2호선",trainNo="42",statnNm=station,updnLine="0",trainSttus="1",source="seoul-sample"))
    path = tmp_path / "trace.jsonl"
    original = "".join(json.dumps(row) + "\n" for row in rows)
    path.write_text(original)
    journey = build(path)["journeys"][0]
    assert [s["name"] for s in journey["stations"]] == stations[:5]
    assert journey["total_observed_station_count"] == 7
    assert journey["replay_window_station_count"] == 5
    assert journey["window_limited"] is True
    assert journey["eta_s"] == 480
    assert journey["stations"][0]["offset_s"] == 0
    assert path.read_text() == original
    assert build(path, max_stations=3)["journeys"][0]["replay_window_station_count"] == 3
