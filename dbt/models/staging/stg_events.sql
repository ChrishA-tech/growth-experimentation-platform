-- Raw Pub/Sub events landed in the warehouse, typed and de-duplicated.
-- BigQuery-compatible SQL (read_parquet works on DuckDB dev; swap to the raw
-- events table on BigQuery prod).
with src as (
    select * from read_parquet('../data/events.parquet')
)
select
    cast(user_id as integer)      as user_id,
    variant,
    event_type,
    cast(event_ts as timestamp)   as event_ts,
    cast(revenue as double)       as revenue
from src
