-- A snapshot in the future means a clock or unit bug (ms vs s).
select snapshot_ts
from {{ ref('stg_state_vectors') }}
where snapshot_ts > now() + interval 10 minute
