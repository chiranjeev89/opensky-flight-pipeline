select icao24, snapshot_ts, ground_speed_kt
from {{ ref('stg_state_vectors') }}
where ground_speed_kt > {{ var('max_ground_speed_kt') }}
