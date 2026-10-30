import datetime as dt
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from eta_model import arrivals, evaluate, fit, load_trace, predict


def train(identity, start, segments=(120, 120, 120, 120)):
    base = dt.datetime(2026, 10, 30, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    elapsed = start
    rows = []
    for i, station in enumerate(("강남", "역삼", "선릉", "삼성", "종합운동장")):
        value = (base + dt.timedelta(seconds=elapsed)).isoformat()
        rows.append(dict(ts=value, recptnDt=value, line="2호선", trainNo=identity, statnNm=station, updnLine="0", trainSttus="1", source="seoul-api"))
        if i < len(segments):
            elapsed += segments[i]
    return rows


def test_build_requires_repeated_segment_observations():
    model = fit(train("a", 0))
    assert model["usable_segments"] == 0
    assert model["segment_observations"] == 4
    # Line-median fallback is explicitly disclosed for sparse segments.
    result = predict(model, "2호선", ["강남", "역삼"])
    assert result["remaining_s"] == 120
    assert result["fallback_segments"] == [["강남", "역삼"]]


def test_empty_data_has_no_synthetic_eta():
    with pytest.raises(ValueError, match="insufficient recorded"):
        predict(fit([]), "2호선", ["강남", "역삼"])
    evaluation = evaluate([])
    assert evaluation["n"] == 0
    assert evaluation["gate_lte_15_percent"] is None


def test_fit_uses_arrival_timestamps_and_deduplicates_status_polls():
    rows = train("a", 0) + train("b", 1000)
    duplicate = dict(rows[0])
    duplicate["ts"] = "2026-10-30T10:00:05+09:00"
    rows.append(duplicate)
    model = fit(rows)
    assert model["segments"]["2호선|강남|역삼"]["n"] == 2
    assert predict(model, "2호선", ["강남", "역삼", "선릉"], 20)["remaining_s"] == 220


def test_whole_train_is_withheld_and_bad_accuracy_is_not_hidden():
    rows = train("a", 0) + train("b", 1000) + train("c", 2000, (300, 300, 300, 300))
    withheld = fit(rows, exclude_train="2호선|0|2026-10-30|c")
    assert withheld["segments"]["2호선|강남|역삼"]["median_s"] == 120
    result = evaluate(rows)
    assert result["n"] == 9
    assert result["gate_lte_15_percent"] is False


def test_skipped_station_never_becomes_one_segment():
    rows = train("a", 0)
    del rows[1]
    model = fit(rows)
    assert "2호선|강남|선릉" not in model["segments"]
    assert model["segment_observations"] == 2
    with pytest.raises(ValueError, match="station skip"):
        predict(model, "2호선", ["강남", "선릉"])


def test_stale_non_arrival_and_synthetic_records_rejected():
    stale = train("a", 0)[0]
    stale["ts"] = "2026-10-30T10:20:00+09:00"
    non_arrival = dict(stale, trainSttus="2")
    synthetic = dict(stale, source="synthetic-fixture")
    _, rejected = arrivals([stale, non_arrival, synthetic, {"gap": True}])
    assert rejected == {"gaps": 1, "non_arrival": 1, "missing_fields": 0, "stale": 1, "synthetic": 1,
                        "continuity_gaps": 0, "source_breaks": 0, "direction_breaks": 0}


@pytest.mark.parametrize("bad", ["not json", "[]", '{"ts":"invalid"}', '{"ts":null}'])
def test_malformed_trace_fails_with_line_number(tmp_path, bad):
    path = tmp_path / "broken.jsonl"
    path.write_text(bad + "\n")
    with pytest.raises(ValueError, match="line 1"):
        load_trace(path)


def test_perfect_held_out_fixture_reports_its_actual_sample_size():
    result = evaluate(train("a", 0) + train("b", 1000) + train("c", 2000))
    assert result["median_relative_error"] == 0
    assert result["n"] == 9
    assert result["train_identities"] == 3


def test_observation_gap_splits_a_train_instead_of_bridging_it():
    rows = train("a", 0)
    rows.append({"ts":"2026-10-30T10:03:00+09:00", "line":"2호선", "source":"seoul-api", "gap":True})
    chains, rejected = arrivals(rows)
    assert [[e["station"] for e in chain] for chain in chains] == [["강남","역삼"],["선릉","삼성","종합운동장"]]
    assert rejected["continuity_gaps"] == 1
    assert fit(rows)["segment_observations"] == 3


def test_source_switch_does_not_join_sample_and_private_observations():
    rows = train("a", 0)
    rows[0]["source"] = "seoul-sample"
    chains, rejected = arrivals(rows)
    assert [e["station"] for e in chains[0]] == ["역삼","선릉","삼성","종합운동장"]
    assert rejected["source_breaks"] == 1


def test_direction_reversal_under_same_identity_breaks_continuity():
    rows = train("a", 0)[:3]
    rows[2]["statnNm"] = "강남"
    chains, rejected = arrivals(rows)
    assert [[e["station"] for e in chain] for chain in chains] == [["강남","역삼"]]
    assert rejected["direction_breaks"] == 1


def test_different_train_identities_are_never_stitched_together():
    first = train("a", 0)[:2]
    second = train("b", 0)[2:]
    chains, rejected = arrivals(first + second)
    assert [[e["station"] for e in chain] for chain in chains] == [["강남","역삼"],["선릉","삼성","종합운동장"]]
