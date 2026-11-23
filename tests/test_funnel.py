import os
import sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
import funnel as fn  # noqa: E402


def _toy():
    return pd.DataFrame({
        "user_id": range(10),
        "variant": ["control"] * 5 + ["treatment"] * 5,
        "activated": [1, 1, 0, 0, 0, 1, 1, 1, 0, 0],
        "retained": [1, 0, 0, 0, 0, 1, 1, 0, 0, 0],
        "expanded": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    })


def test_funnel_rates_monotone():
    stages, rates = fn.funnel(_toy())
    assert stages["signups"] >= stages["activated"] >= stages["retained_d7"] >= stages["expanded"]
    assert 0 <= rates["activation_rate"] <= 1
