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
)

select * from deduped
