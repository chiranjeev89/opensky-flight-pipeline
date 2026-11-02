-- FEATURE-004: one trustworthy row per airport per day, with data-quality columns.
-- pct_unknown_* = flights where OpenSky could not tell the other airport
-- (it estimates airports from the track; short tracks leave it null).
select
    airport,
    flight_date,
    count(*) filter (where direction = 'arrival')                                  as arrivals,
    count(*) filter (where direction = 'departure')                                as departures,
    count(*)                                                                       as movements,
    count(distinct icao24)                                                         as unique_aircraft,
    round(100.0 * avg(case when direction = 'arrival' and departure_airport is null then 1
                           when direction = 'arrival' then 0 end), 1)              as pct_unknown_origin,
    round(100.0 * avg(case when direction = 'departure' and arrival_airport is null then 1
                           when direction = 'departure' then 0 end), 1)            as pct_unknown_destination,
    round(median(duration_min), 0)                                                 as median_duration_min
from {{ ref('stg_airport_flights') }}
where is_plausible
group by 1, 2
