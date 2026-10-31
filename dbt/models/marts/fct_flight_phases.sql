-- Classify every airborne observation into a flight phase.
-- Domain logic (aerospace): vertical rate beyond +/- 2.5 m/s (~500 ft/min) is
-- climb/descent; level above FL200 is cruise; level below is "level_low"
-- (holding, approach segments, low-level transit).
with obs as (
    select * from {{ ref('stg_state_vectors') }}
    where has_position
      and is_plausible   -- BUG-009: glitch rows excluded, counted in fct_data_quality
)

select
    icao24,
    callsign,
    snapshot_ts,
    date_trunc('hour', snapshot_ts) as snapshot_hour,
    latitude,
    longitude,
    altitude_ft,
    ground_speed_kt,
    vertical_rate_ms,
    case
        when on_ground then 'ground'
        when vertical_rate_ms >  {{ var('level_flight_vr_ms') }} then 'climb'
        when vertical_rate_ms < -{{ var('level_flight_vr_ms') }} then 'descent'
        when altitude_ft >= 20000 then 'cruise'
        when altitude_ft is not null then 'level_low'
        else 'unknown'
    end as flight_phase
from obs
