-- We query a box; positions far outside it mean a lat/lon swap bug.
-- 1 degree tolerance: OpenSky includes aircraft near the edge.
select icao24, latitude, longitude
from {{ ref('fct_flight_phases') }}
where (latitude  not between {{ var('bbox_lamin') }} - 1 and {{ var('bbox_lamax') }} + 1
    or longitude not between {{ var('bbox_lomin') }} - 1 and {{ var('bbox_lomax') }} + 1)
