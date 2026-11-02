-- FEATURE-004: flights per airport per hour (the core airport metric).
-- Grain: airport x UTC hour. Hours with no movements are simply absent.
select
    airport,
    date_trunc('hour', event_ts)                                         as movement_hour,
    date_trunc('hour', any_value(event_local_ts))                        as movement_hour_local,
    hour(any_value(event_local_ts))                                      as hour_of_day_local,
    count(*) filter (where direction = 'arrival')                        as arrivals,
    count(*) filter (where direction = 'departure')                      as departures,
    count(*)                                                             as movements
from {{ ref('stg_airport_flights') }}
where is_plausible
group by 1, 2
