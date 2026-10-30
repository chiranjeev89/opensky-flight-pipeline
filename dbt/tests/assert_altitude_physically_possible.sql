-- Fails if any airborne altitude is outside physical limits.
-- Note: this checks the cleaned model; outliers would mean a parsing bug
-- (e.g. wrong field index), which is exactly what we want to catch.
select icao24, snapshot_ts, altitude_ft
from {{ ref('stg_state_vectors') }}
where not on_ground
  and altitude_ft is not null
  and (altitude_ft > {{ var('max_altitude_ft') }} or altitude_ft < {{ var('min_altitude_ft') }})
