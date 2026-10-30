import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from eta_model import LINE2, adjacent, predict
from topology import DATA, canonical_station, resolve_route


def test_line5_branch_junction_has_three_real_neighbors_and_no_branch_jump():
    assert adjacent("5호선","강동","길동")
    assert adjacent("5호선","강동","둔촌동")
    assert adjacent("5호선","천호","강동")
    assert not adjacent("5호선","하남검단산","둔촌동")
    assert not adjacent("5호선","둔촌동","천호")
    with pytest.raises(ValueError,match="not concatenated"):
        resolve_route("5호선","길동","둔촌동")
    with pytest.raises(ValueError,match="crosses line-5 branches"):
        predict({"source":"recorded-station-arrival-proxy","segments":{},"line_medians_s":{"5호선":120}},"5호선",["길동","강동","둔촌동"])


def test_full_line7_extensions_aliases_and_direction_are_supported():
    assert len(DATA["lines"]["7호선"]["stations"]) == 53
    assert adjacent("7호선","부평구청","산곡")
    assert adjacent("7호선","산곡","석남(거북시장)")
    assert canonical_station("7호선","뚝섬유원지") == "자양"
    assert canonical_station("7호선","상도(중앙대앞)") == "상도"
    assert canonical_station("7호선","이수") == "총신대입구(이수)"
    assert resolve_route("7호선","부평구청","석남",direction="1") == ["부평구청","산곡","석남"]
    with pytest.raises(ValueError):
        resolve_route("7호선","부평구청","석남",direction="0")


def test_cli_from_to_at_is_a_forecast_anchor_and_ring_ambiguity_is_explicit(tmp_path):
    model=tmp_path/"model.json"
    model.write_text(json.dumps({"source":"recorded-station-arrival-proxy","segments":{},"line_medians_s":{"5호선":120,"2호선":120}}))
    command=[sys.executable,str(ROOT/"scripts/eta_model.py"),"predict","--model",str(model)]
    result=subprocess.run(command+["--line","5호선","--from","마포","--to","애오개","--at","2026-10-30T11:00:00+09:00"],capture_output=True,text=True)
    assert result.returncode == 0,result.stderr
    data=json.loads(result.stdout)
    assert data["route"] == ["마포","공덕","애오개"]
    assert data["remaining_s"] == 240
    assert data["estimated_arrival_at"] == "2026-10-30T11:04:00+09:00"
    assert data["clock_kind"] == "explicit-forecast-anchor-not-observed-arrival"
    ambiguous=subprocess.run(command+["--line","2호선","--from","강남","--to","역삼"],capture_output=True,text=True)
    assert ambiguous.returncode == 2
    assert "ambiguous line-2 ring" in ambiguous.stderr
    explicit=subprocess.run(command+["--line","2호선","--stations","강남,역삼"],capture_output=True,text=True)
    assert explicit.returncode == 0
