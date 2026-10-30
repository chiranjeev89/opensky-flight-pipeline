-- Warn (not fail) if the newest snapshot is older than max_staleness_hours.
-- Severity warn: stale data should alert us, not block the last good publish.
{{ config(severity = 'warn') }}
select max(snapshot_ts) as newest
from {{ ref('stg_state_vectors') }}
having max(snapshot_ts) < now() - interval {{ var('max_staleness_hours') }} hour
