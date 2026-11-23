import json
import os
import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
import sys
sys.path.insert(0, os.path.join(ROOT, "src"))
import experiment as ex  # noqa: E402


def test_two_prop_detects_known_lift():
    # 10pp lift on large samples must be significant
    lift, p, z = ex.two_prop(4000, 10000, 5000, 10000)
    assert lift == pytest.approx(0.10, abs=1e-9)
    assert p < 1e-6


def test_cuped_preserves_effect_and_cuts_variance():
    rng = np.random.default_rng(0)
    n = 20000
    x = rng.normal(0, 1, n)                     # pre-period covariate
    variant = np.where(rng.random(n) < 0.5, "treatment", "control")
    eff = np.where(variant == "treatment", 0.5, 0.0)
    y = 3 * x + eff + rng.normal(0, 1, n)       # strong covariate
    naive, adj, cut = ex.cuped(y, x, variant)
    assert adj == pytest.approx(0.5, abs=0.1)   # effect unchanged
    assert cut > 0.5                            # big variance reduction


def test_mde_positive_and_small_for_large_n():
    assert 0 < ex.power_mde(0.4, 20000) < 0.02


@pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "reports/experiment.json")),
                    reason="run src/experiment.py first")
def test_reported_lift_is_significant():
    d = json.load(open(os.path.join(ROOT, "reports/experiment.json")))
    assert d["activation_lift_pp"] > d["mde_pp_at_80pct_power"]
    assert d["bootstrap_ci_pp"][0] > 0          # CI excludes zero
