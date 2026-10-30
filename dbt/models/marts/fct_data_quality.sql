-- MEASURE: how clean is the raw feed? One row per day.
with raw as (
    select cast(to_timestamp(snapshot_time) as date) as d, count(*) as raw_rows
    from {{ source('lake', 'raw_states') }}
    group by 1
),
stg as (
    select
        cast(snapshot_ts as date) as d,
        count(*)                                                     as clean_rows,
        round(100.0 * avg(case when not has_position then 1 else 0 end), 2)     as pct_missing_position,
        round(100.0 * avg(case when altitude_ft is null then 1 else 0 end), 2)  as pct_missing_altitude,
        round(100.0 * avg(case when callsign is null then 1 else 0 end), 2)     as pct_missing_callsign,
        round(avg(seconds_since_contact), 1)                                     as avg_seconds_since_contact
    from {{ ref('stg_state_vectors') }}
    group by 1
)
select
    stg.d as run_date,
    raw.raw_rows,
    stg.clean_rows,
    raw.raw_rows - stg.clean_rows as duplicates_removed,
    stg.pct_missing_position,
    stg.pct_missing_altitude,
    stg.pct_missing_callsign,
    stg.avg_seconds_since_contact
from stg join raw using (d)
