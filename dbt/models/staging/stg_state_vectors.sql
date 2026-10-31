-- Staging: clean + type + dedupe raw state vectors. One row per (icao24, snapshot).
-- Cleaning lives here (not in Python) so it is versioned and tested (D-004).
with source as (
    select * from {{ source('lake', 'raw_states') }}
),

cleaned as (
    select
        lower(trim(icao24))                              as icao24,
        nullif(trim(callsign), '')                       as callsign,   -- API pads with spaces
        origin_country,
        to_timestamp(snapshot_time)                      as snapshot_ts,
        to_timestamp(last_contact)                       as last_contact_ts,
        snapshot_time - last_contact                     as seconds_since_contact,
        latitude,
        longitude,
        baro_altitude                                    as baro_altitude_m,
        geo_altitude                                     as geo_altitude_m,
        {{ m_to_ft('coalesce(baro_altitude, geo_altitude)') }} as altitude_ft,
        velocity                                         as velocity_ms,
        {{ ms_to_kt('velocity') }}                       as ground_speed_kt,
        vertical_rate                                    as vertical_rate_ms,
        true_track                                       as track_deg,
        on_ground,
        squawk,
        position_source,
        latitude is not null and longitude is not null   as has_position,
        ingested_at
    from source
    where icao24 is not null
),

deduped as (
    -- A retried task can land the same snapshot twice: keep the latest ingest.
    select *
    from cleaned
    qualify row_number() over (
        partition by icao24, snapshot_ts order by ingested_at desc
    ) = 1
),

flagged as (
    -- BUG-009: real ADS-B feeds contain occasional transponder glitches
    -- (e.g. 2 aircraft reporting > 750 kt). Flag them instead of letting one
    -- bad aircraft block the whole publish. Marts use only plausible rows;
    -- the systemic test below still fails if MANY rows are implausible.
    select
        *,
        not (
            coalesce(ground_speed_kt, 0) > {{ var('max_ground_speed_kt') }}
            or (not on_ground and altitude_ft is not null
                and (altitude_ft > {{ var('max_altitude_ft') }} or altitude_ft < {{ var('min_altitude_ft') }}))
            or (has_position and (
                latitude  not between {{ var('bbox_lamin') }} - 1 and {{ var('bbox_lamax') }} + 1
                or longitude not between {{ var('bbox_lomin') }} - 1 and {{ var('bbox_lomax') }} + 1))
        ) as is_plausible
    from deduped
)

select * from flagged
