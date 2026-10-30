import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_trace import analyze


def observation(polled, provided, station="강남", train="42", status="1"):
    return {"ts": "2026-10-30T" + polled + "+09:00", "recptnDt": "2026-10-30T" + provided + "+09:00" if provided else None,
            "line":"2호선", "trainNo":train, "statnNm":station, "updnLine":"0", "trainSttus":status, "source":"seoul-sample"}


def write_trace(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_gap_counts_polls_without_counting_each_train_as_a_poll(tmp_path):
    rows = [observation("10:00:10", "10:00:00"), observation("10:00:10", "10:00:00", train="43"),
            {"ts":"2026-10-30T10:01:00+09:00", "line":"2호선", "source":"seoul-sample", "gap":True},
            observation("10:02:10", "10:02:00", station="역삼")]
    path = tmp_path / "trace.jsonl"
    write_trace(path, rows)
    path.with_suffix(".meta.json").write_text(json.dumps({"polls":3,"observations":3,"gaps":1,"complete":False,"interval_s":20}))
    result = analyze(path)
    assert result["distinct_polls_from_line_and_ts"] == 3
    assert result["observation_records"] == 3
    assert result["gap_records"] == 1
    assert result["poll_status_counts"] == {"observation":2,"gap":1,"mixed":0}
    assert result["distinct_train_identities"] == 2
    assert result["adjacent_segment_observations"] == 0
    assert result["continuity_rejections"]["continuity_gaps"] == 1
    assert result["sampling"]["metadata_poll_count_matches_snapshot"] is True
    assert result["sampling"]["partial"] is True


def test_timestamp_ages_retain_future_values_and_quantiles_ignore_record_order(tmp_path):
    rows = [observation("10:00:40","10:00:00", status="0"), observation("10:00:20","10:00:00", status="0"),
            observation("10:00:10","10:00:00", status="0"), observation("10:00:00","10:00:00", status="0"),
            observation("10:00:00","10:00:05", status="0"), observation("10:00:50",None, status="0"),
            dict(observation("10:01:00",None, status="0"), recptnDt="malformed")]
    path = tmp_path / "trace.jsonl"
    write_trace(path, rows)
    result = analyze(path)
    assert result["receipt_timestamp_age_s"] == {"n":5,"p50":10,"p95":40,"min":-5,"max":40}
    assert result["future_receipt_timestamp_count"] == 1
    assert result["missing_receipt_timestamp_count"] == 1
    assert result["invalid_receipt_timestamp_count"] == 1
    assert result["out_of_order_record_timestamps"] == 3
    assert result["first_poll_at"] == "2026-10-30T10:00:00+09:00"
    assert result["last_poll_at"] == "2026-10-30T10:01:00+09:00"


def test_malformed_rows_are_counted_without_fabricating_timestamp_statistics(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text('not-json\n[]\n{"ts":null,"source":"seoul-sample"}\n')
    result = analyze(path)
    assert result["invalid_json_lines"] == 1
    assert result["non_object_lines"] == 1
    assert result["parsed_object_records"] == 1
    assert result["invalid_poll_timestamp_count"] == 1
    assert result["receipt_timestamp_age_s"]["n"] == 0
    assert result["receipt_timestamp_age_s"]["p95"] is None
    assert result["contiguous_arrival_chains"] == 0
