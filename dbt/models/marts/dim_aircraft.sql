-- One row per transponder seen. Latest callsign wins (callsigns change per flight).
select
    icao24,
    arg_max(callsign, snapshot_ts) filter (where callsign is not null) as latest_callsign,
    arg_max(origin_country, snapshot_ts)                               as origin_country,
    min(snapshot_ts)                                                   as first_seen_ts,
    max(snapshot_ts)                                                   as last_seen_ts,
    count(*)                                                           as observations,
    round(max(altitude_ft), 0)                                         as max_altitude_ft
from {{ ref('stg_state_vectors') }}
group by icao24
