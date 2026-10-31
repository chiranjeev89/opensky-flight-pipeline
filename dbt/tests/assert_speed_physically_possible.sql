-- Published data must never contain impossible speeds (glitches are filtered in staging).
select icao24, snapshot_ts, ground_speed_kt
from {{ ref('fct_flight_phases') }}
where ground_speed_kt > {{ var('max_ground_speed_kt') }}
