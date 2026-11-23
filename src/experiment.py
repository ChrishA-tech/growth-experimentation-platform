"""A/B experiment readout for the onboarding growth test.

Covers the full experimentation toolkit a growth DS is expected to own:
  - pre-experiment power / minimum detectable effect (MDE)
  - two-proportion z-test on the primary metric (activation) with a bootstrap CI
  - CUPED variance reduction on the continuous revenue metric using pre_sessions
  - an always-valid sequential test (mSPRT) that reports the day the test could stop

Writes reports/experiment.json with every figure the README and CV cite.
"""
import json
import numpy as np
import pandas as pd
from scipy import stats

Z = stats.norm.ppf


def power_mde(p, n_per_arm, alpha=0.05, power=0.80):
    """Minimum detectable absolute lift on a proportion for a two-sided test."""
    se = np.sqrt(2 * p * (1 - p) / n_per_arm)
    return (Z(1 - alpha / 2) + Z(power)) * se


def two_prop(c_succ, c_n, t_succ, t_n):
    pc, pt = c_succ / c_n, t_succ / t_n
    p = (c_succ + t_succ) / (c_n + t_n)
    se = np.sqrt(p * (1 - p) * (1 / c_n + 1 / t_n))
    z = (pt - pc) / se
    return pt - pc, 2 * (1 - stats.norm.cdf(abs(z))), z


def bootstrap_diff(c, t, B=4000, seed=1):
    rng = np.random.default_rng(seed)
    diffs = np.empty(B)
    for b in range(B):
        diffs[b] = (rng.choice(t, t.size).mean() - rng.choice(c, c.size).mean())
    return np.percentile(diffs, [2.5, 97.5])


def cuped(y, x, variant):
    """Return the naive and CUPED-adjusted treatment effect on y and the variance cut."""
    theta = np.cov(x, y)[0, 1] / np.var(x)
    y_adj = y - theta * (x - x.mean())
    c, t = variant == "control", variant == "treatment"
    naive = y[t].mean() - y[c].mean()
    adj = y_adj[t].mean() - y_adj[c].mean()
    var_cut = 1 - np.var(y_adj) / np.var(y)
    return naive, adj, var_cut


def msprt_stop_day(df):
    """Mixture SPRT confidence sequence on activation; first day the CI excludes 0."""
    df = df.sort_values("signup_day")
    for day in sorted(df.signup_day.unique()):
        cur = df[df.signup_day <= day]
        c = cur[cur.variant == "control"].activated.values
        t = cur[cur.variant == "treatment"].activated.values
        if len(c) < 200 or len(t) < 200:
            continue
        diff = t.mean() - c.mean()
        n = len(c) + len(t)
        # always-valid radius (sub-Gaussian confidence sequence, phi=var proxy)
        var = 0.25
        rad = np.sqrt(2 * var * np.log(np.sqrt(n + 1) / 0.05) / min(len(c), len(t)))
        if diff - rad > 0:
            return int(day), float(diff), float(rad), n
    return None, None, None, len(df)


def main():
    u = pd.read_parquet("data/users.parquet")
    c, t = u[u.variant == "control"], u[u.variant == "treatment"]
    n_arm = min(len(c), len(t))

    mde = power_mde(u.activated.mean(), n_arm)
    lift, pval, z = two_prop(c.activated.sum(), len(c), t.activated.sum(), len(t))
    ci = bootstrap_diff(c.activated.values.astype(float), t.activated.values.astype(float))
    naive, adj, var_cut = cuped(u.revenue.values, u.pre_revenue.values.astype(float), u.variant.values)
    stop_day, stop_diff, stop_rad, stop_n = msprt_stop_day(u)

    out = {
        "n_per_arm": int(n_arm),
        "primary_metric": "activation_rate",
        "control_activation": round(float(c.activated.mean()), 4),
        "treatment_activation": round(float(t.activated.mean()), 4),
        "activation_lift_pp": round(float(lift) * 100, 2),
        "z_score": round(float(z), 1),
        "p_value": "<1e-10" if pval < 1e-10 else float(f"{pval:.2e}"),
        "bootstrap_ci_pp": [round(ci[0] * 100, 2), round(ci[1] * 100, 2)],
        "mde_pp_at_80pct_power": round(float(mde) * 100, 2),
        "revenue_effect_naive": round(float(naive), 3),
        "revenue_effect_cuped": round(float(adj), 3),
        "cuped_variance_reduction_pct": round(float(var_cut) * 100, 1),
        "msprt_stop_signup_day": stop_day,
        "msprt_users_at_stop": stop_n,
        "fixed_horizon_users": int(len(u)),
    }
    with open("reports/experiment.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
