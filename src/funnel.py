"""Growth-funnel and cohort-retention metrics from the event stream.

Computes the acquisition -> activation -> retention -> expansion funnel (overall and
by variant) and weekly signup-cohort retention. Writes reports/funnel.json.
"""
import json
import os
import pandas as pd

os.makedirs("reports", exist_ok=True)


def funnel(u):
    n = len(u)
    stages = {
        "signups": n,
        "activated": int(u.activated.sum()),
        "retained_d7": int(u.retained.sum()),
        "expanded": int(u.expanded.sum()),
    }
    rates = {
        "activation_rate": round(stages["activated"] / n, 4),
        "retention_rate_of_activated": round(stages["retained_d7"] / max(stages["activated"], 1), 4),
        "expansion_rate_of_retained": round(stages["expanded"] / max(stages["retained_d7"], 1), 4),
        "signup_to_paid": round(stages["expanded"] / n, 4),
    }
    return stages, rates


def main():
    u = pd.read_parquet("data/users.parquet")
    stages, rates = funnel(u)

    by_variant = {}
    for v, g in u.groupby("variant"):
        s, r = funnel(g)
        by_variant[v] = {"stages": s, "rates": r}

    # weekly signup cohorts -> share still paying (expansion) as a simple retention proxy
    u = u.copy()
    u["cohort_week"] = (u.signup_day // 7).astype(int)
    cohorts = (u.groupby("cohort_week")
               .agg(signups=("user_id", "size"),
                    activation_rate=("activated", "mean"),
                    paid_rate=("expanded", "mean"))
               .round(4).reset_index().to_dict("records"))

    out = {"overall_stages": stages, "overall_rates": rates,
           "by_variant": by_variant, "weekly_cohorts": cohorts}
    with open("reports/funnel.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({"overall_rates": rates,
                      "activation_by_variant": {k: v["rates"]["activation_rate"]
                                                for k, v in by_variant.items()}}, indent=2))


if __name__ == "__main__":
    main()
