# Growth Experimentation Platform

End-to-end growth-analytics stack on product-event data: **Pub/Sub-style event streaming
→ dbt warehouse (BigQuery dialect) → funnel & cohort marts → an experimentation engine**
(power/MDE, CUPED, sequential testing) and a Streamlit growth app.

Built to own a growth funnel end to end — **acquisition → activation → retention →
expansion** — the way a product growth team runs it.

## Results (reproducible, `seed=42`, 40,000 users / 70,645 events)

| Area | Result |
|---|---|
| **Onboarding A/B — activation** | control **41.8%** → treatment **47.7%**, lift **+5.9 pp** (95% bootstrap CI **4.9–6.9 pp**, p < 1e-10) |
| **Design sensitivity** | minimum detectable effect **1.39 pp** at 80% power, 20k/arm |
| **CUPED** | **15.3%** variance reduction on revenue using prior-period revenue, effect unchanged |
| **Sequential test (mSPRT)** | always-valid CI clears zero at **~4,242 users vs 40,000** fixed-horizon (≈**9× faster**) |
| **Funnel** | activation **44.3%** · retention-of-activated **54.6%** · expansion-of-retained **30.3%** · signup→paid **7.4%** |
| **Warehouse** | dbt `build` = **7/7 pass** (models + tests) on DuckDB; same SQL on BigQuery |

## Pipeline

```
src/generate_events.py   # product events + experiment assignment + CUPED covariate
src/streaming.py         # Pub/Sub-style topic -> subscription -> JSONL landing
dbt/                     # stg_events -> funnel_by_variant (+ schema tests)
src/funnel.py            # funnel + weekly cohort retention -> reports/funnel.json
src/experiment.py        # power/MDE, two-proportion z, bootstrap, CUPED, mSPRT
src/app.py               # Streamlit growth app (Hex / data-app stand-in)
```

## Run it

```bash
pip install -r requirements.txt
python src/generate_events.py && python src/funnel.py && python src/experiment.py
python src/streaming.py
cd dbt && dbt build --profiles-dir .      # DuckDB dev warehouse
pytest -q
streamlit run src/app.py
```

## Deploy on Google Cloud (makes BigQuery + Pub/Sub live)

The code is GCP-ready; the only change is the target.

1. **Pub/Sub** — `gcloud pubsub topics create product-events` and a `events-to-bq`
   subscription; point `streaming.py` at the topic (same publish/pull interface).
2. **BigQuery** — `dbt build -t prod` runs the identical models on BigQuery
   (`profiles.yml` `prod` target; set `GCP_PROJECT`). Dataset `growth_marts`, EU.
3. **Orchestration** — schedule `dbt build` on Cloud Run / Composer; stream Pub/Sub →
   BigQuery via a subscription or Dataflow.

## Stack

Python (pandas, NumPy, SciPy) · **SQL / dbt** · **BigQuery** (dialect, prod target) ·
DuckDB (dev) · **Pub/Sub-style streaming** · A/B & uplift experimentation · **CUPED** ·
**sequential testing (mSPRT)** · power analysis · funnel & cohort analytics · Streamlit ·
GitHub Actions CI.
