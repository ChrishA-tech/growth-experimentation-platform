"""Generate a realistic product-analytics event stream for a growth experiment.

Simulates an onboarding experiment on a software-creation product: new users are
split 50/50 into control vs a treatment onboarding flow. We emit GA4/Pub-Sub-style
events across the growth funnel (signup -> activation -> retention -> expansion) plus
a pre-experiment spend covariate used later for CUPED variance reduction.

Output: data/events.parquet  (one row per event)  and  data/users.parquet (one row per user)
Deterministic (seed=42) so CI and the README numbers match.
"""
import numpy as np
import pandas as pd

SEED = 42
N_USERS = 40_000
ACTIVATION_BASE = 0.42       # control activation probability
ACTIVATION_LIFT = 0.055      # true treatment effect on activation (absolute)
RETENTION_GIVEN_ACTIVE = 0.55
EXPANSION_GIVEN_RETAINED = 0.30
ARPU_EXPANDED = 29.0         # monthly revenue for an expanded (paid) user


def main():
    rng = np.random.default_rng(SEED)
    uid = np.arange(1, N_USERS + 1)
    variant = rng.integers(0, 2, N_USERS)  # 0 control, 1 treatment
    signup_day = rng.integers(0, 28, N_USERS)  # 4-week acquisition window

    # Pre-experiment engagement covariate (prior 14-day sessions). Correlates with
    # the post outcome -> CUPED can remove variance without touching the estimate.
    pre_sessions = rng.poisson(3.0, N_USERS).astype(float)
    latent = 0.18 * (pre_sessions - pre_sessions.mean()) / pre_sessions.std()

    # Pre-period value of the KPI (prior-month revenue): the standard CUPED covariate,
    # strongly correlated (~0.6) with post-period revenue and unaffected by the variant.
    user_quality = rng.normal(0, 1, N_USERS)
    pre_revenue = np.clip(12.0 + 8.0 * user_quality + rng.normal(0, 5.0, N_USERS), 0, None)

    p_act = ACTIVATION_BASE + ACTIVATION_LIFT * variant + latent
    p_act = np.clip(p_act, 0.01, 0.99)
    activated = rng.random(N_USERS) < p_act

    retained = activated & (rng.random(N_USERS) < RETENTION_GIVEN_ACTIVE)
    expanded = retained & (rng.random(N_USERS) < EXPANSION_GIVEN_RETAINED)

    # Continuous revenue metric (for CUPED / t-test): paid users pay ARPU with noise,
    # driven by the same user_quality so prior-month revenue is a valid CUPED covariate.
    revenue = (np.where(expanded, ARPU_EXPANDED, 0.0)
               + 7.0 * user_quality + rng.normal(0, 4.0, N_USERS))
    revenue = np.clip(revenue, 0, None)

    users = pd.DataFrame({
        "user_id": uid,
        "variant": np.where(variant == 1, "treatment", "control"),
        "signup_day": signup_day,
        "pre_sessions": pre_sessions,
        "pre_revenue": pre_revenue.round(2),
        "activated": activated,
        "retained": retained,
        "expanded": expanded,
        "revenue": revenue.round(2),
    })

    # Explode into an event log (what a Pub/Sub topic would carry).
    rows = []
    for _, u in users.iterrows():
        base = int(u.signup_day) * 86400
        rows.append((u.user_id, u.variant, base, "signup", 0.0))
        if u.activated:
            rows.append((u.user_id, u.variant, base + 1800, "activation", 0.0))
        if u.retained:
            rows.append((u.user_id, u.variant, base + 7 * 86400, "retention_d7", 0.0))
        if u.expanded:
            rows.append((u.user_id, u.variant, base + 10 * 86400, "expansion", float(u.revenue)))
    events = pd.DataFrame(rows, columns=["user_id", "variant", "event_ts", "event_type", "revenue"])
    events["event_ts"] = pd.to_datetime("2026-10-01") + pd.to_timedelta(events["event_ts"], unit="s")

    users.to_parquet("data/users.parquet", index=False)
    events.to_parquet("data/events.parquet", index=False)
    print(f"users={len(users):,}  events={len(events):,}  "
          f"activation(control)={users.query('variant==\"control\"').activated.mean():.3f}  "
          f"activation(treatment)={users.query('variant==\"treatment\"').activated.mean():.3f}")


if __name__ == "__main__":
    main()
