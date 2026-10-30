import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from extract_timetable_topology import extract


def row(station, at, **kwargs):
    return dict(LINE="5", GUBHANG="0", STATION_NM=station, STT=at, EDT=at,
                WEEKTAG="DAY", INOUTTAG="DOWN", TRAIN_NO="5001", ST_STT_NM="방화", ED_STT_NM="마천", **kwargs)


def test_branch_termini_and_operating_days_do_not_cross_connect():
    a = row("강동", "10:00:00")
    b = row("길동", "10:02:00")
    b["ED_STT_NM"] = "하남검단산"
    c = row("둔촌동", "10:02:00")
    d = row("길동", "10:04:00")
    d["WEEKTAG"] = "SAT"
    rows = [a, b, c, d]
    rows += [dict(r, TRAIN_NO="5002") for r in (a, c)]
    edges = extract(rows)["5호선"]["edges"]
    assert edges == [{"stations": ["강동", "둔촌동"], "scheduled_occurrences": 2}]


def test_origin_zero_arrival_uses_departure_and_rejects_breaks_express():
    a = row("강동", "00:00:00")
    a["EDT"] = "23:59:00"
    b = row("둔촌동", "24:01:00")
    c = row("방이", "24:30:00")
    express = row("올림픽공원", "24:32:00")
    express["GUBHANG"] = "1"
    result = extract([a, b, c, express, dict(a, TRAIN_NO="5002"), dict(b, TRAIN_NO="5002")])["5호선"]
    assert result["edges"] == [{"stations": ["강동", "둔촌동"], "scheduled_occurrences": 2}]
    assert result["rejected_gaps_or_duplicates"] == 1
