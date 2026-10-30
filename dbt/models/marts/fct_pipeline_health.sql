-- MEASURE: daily health of the ingestion itself. These numbers go in the README.
-- expected_runs assumes the 10-minute schedule (144/day); a partial first/last
-- day will show lower completeness, which is honest, not a bug.
select
    cast(snapshot_ts as date)                                   as run_date,
    count(*)                                                    as runs_landed,
    144                                                         as expected_runs,
    round(100.0 * count(*) / 144, 1)                            as completeness_pct,
    round(avg(api_latency_ms), 0)                               as avg_api_latency_ms,
    round(quantile_cont(api_latency_ms, 0.95), 0)               as p95_api_latency_ms,
    round(avg(row_count), 0)                                    as avg_rows_per_snapshot,
    sum(row_count)                                              as total_rows,
    round(sum(parquet_bytes) / 1024.0 / 1024.0, 2)              as total_mb,
    min(credits_remaining)                                      as min_credits_remaining
from {{ ref('stg_pipeline_runs') }}
group by 1
