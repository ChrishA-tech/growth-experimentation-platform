-- Acquisition -> activation -> retention -> expansion funnel by experiment variant.
with ev as (select * from {{ ref('stg_events') }}),
flags as (
    select
        user_id,
        max(variant) as variant,
        max(case when event_type = 'signup'       then 1 else 0 end) as signed_up,
        max(case when event_type = 'activation'   then 1 else 0 end) as activated,
        max(case when event_type = 'retention_d7' then 1 else 0 end) as retained,
        max(case when event_type = 'expansion'    then 1 else 0 end) as expanded,
        sum(revenue) as revenue
    from ev
    group by user_id
)
select
    variant,
    count(*)                                             as signups,
    sum(activated)                                       as activated,
    sum(retained)                                        as retained_d7,
    sum(expanded)                                        as expanded,
    round(sum(activated) * 1.0 / count(*), 4)            as activation_rate,
    round(sum(retained)  * 1.0 / nullif(sum(activated),0), 4) as retention_rate,
    round(sum(expanded)  * 1.0 / nullif(sum(retained),0), 4)  as expansion_rate,
    round(sum(revenue), 2)                               as total_revenue
from flags
group by variant
order by variant
