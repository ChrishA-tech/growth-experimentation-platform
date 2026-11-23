"""Streamlit growth app: funnel, experiment readout and cohort retention.

A lightweight stand-in for a Hex / Lovable-style data app. Run:  streamlit run src/app.py
Reads the JSON the pipeline writes to reports/.
"""
import json
import os
import streamlit as st

R = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")


def load(name):
    with open(os.path.join(R, name)) as f:
        return json.load(f)


st.set_page_config(page_title="Growth Experimentation", layout="wide")
st.title("Growth Experimentation Platform")

exp, fun = load("experiment.json"), load("funnel.json")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Activation lift", f"+{exp['activation_lift_pp']} pp",
          help=f"95% CI {exp['bootstrap_ci_pp']} pp")
c2.metric("CUPED variance cut", f"{exp['cuped_variance_reduction_pct']}%")
c3.metric("Users at sequential stop", f"{exp['msprt_users_at_stop']:,}",
          delta=f"vs {exp['fixed_horizon_users']:,} fixed-horizon", delta_color="inverse")
c4.metric("Signup -> paid", f"{fun['overall_rates']['signup_to_paid']*100:.1f}%")

st.subheader("Funnel by variant")
st.dataframe({v: d["rates"] for v, d in fun["by_variant"].items()})

st.subheader("Weekly signup cohorts")
st.dataframe(fun["weekly_cohorts"])
