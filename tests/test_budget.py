from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from eta_model import budget


@pytest.mark.parametrize("remaining,rate,margin,expected", [
    (0, 4.51, 20, 0), (20, 4.51, 20, 0), (21, 4.51, 20, 4),
    (120, 4.51, 20, 451), (60, 2, 10, 100), (-10, 4.51, 20, 0),
])
def test_fixed_budget_cases(remaining, rate, margin, expected):
    assert budget(remaining, rate, margin) == expected


@pytest.mark.parametrize("args", [(float("nan"),), (float("inf"),), (60, 0), (60, 1, -1), (True,)])
def test_invalid_budget_inputs(args):
    with pytest.raises(ValueError):
        budget(*args)
