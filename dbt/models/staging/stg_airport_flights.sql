-- Staging for FEATURE-004: one row per flight per airport query, cleaned and deduped.
-- Grain: (airport, direction, icao24, departure_ts).
-- "airport" is the airport we asked about (EDDF/EDDM); "event_ts" is when the
-- flight touched it (landing for arrivals, take-off for departures).
with source as (
    select * from {{ source('lake', 'raw_airport_flights') }}
    where query_airport <> 'NONE'          -- 0-row bootstrap file (storage.ensure_bootstrap_files)
),

cleaned as (
    select
        lower(trim(icao24))                                        as icao24,
        nullif(trim(callsign), '')                                 as callsign,
        upper(query_airport)                                       as airport,
        direction,
        flight_date,
        to_timestamp(first_seen)                                   as departure_ts,
        to_timestamp(last_seen)                                    as arrival_ts,
        upper(nullif(trim(est_departure_airport), ''))             as departure_airport,
        upper(nullif(trim(est_arrival_airport), ''))               as arrival_airport,
        case when direction = 'arrival' then to_timestamp(last_seen)
             else to_timestamp(first_seen) end                     as event_ts,
        round((last_seen - first_seen) / 60.0, 1)                  as duration_min,
        dep_horiz_distance_m,
        arr_horiz_distance_m,
        ingested_at
    from source
    where icao24 is not null
      and first_seen is not null
      and last_seen is not null
),

deduped as (
    -- A re-run of the same day overwrites the file, but a retry mid-day could
    -- land a row twice: keep the newest ingest (same rule as state vectors).
    select *
    from cleaned
    qualify row_number() over (
        partition by airport, direction, icao24, departure_ts order by ingested_at desc
    ) = 1
)

select
    *,
    -- Same idea as BUG-009: flag tracking errors instead of blocking everything.
    arrival_ts >= departure_ts
        and duration_min <= {{ var('max_flight_duration_min') }}  as is_plausible,
    timezone('Europe/Berlin', event_ts)                             as event_local_ts
from deduped
