select
    to_timestamp(snapshot_time) as snapshot_ts,
    run_started_at,
    api_latency_ms,
    row_count,
    parquet_bytes,
    credits_remaining,
    status
from {{ source('lake', 'raw_runs') }}
qualify row_number() over (partition by snapshot_time order by run_started_at desc) = 1
