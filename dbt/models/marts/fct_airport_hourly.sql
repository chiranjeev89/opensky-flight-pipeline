-- FEATURE-004: flights per airport per hour (the core airport metric).
-- Grain: airport x UTC hour. Hours with no movements are simply absent.
-- BUG-010: is_complete_day comes from fct_airport_daily so profiles can skip bad days.
with hourly as (
    select
        airport,
        flight_date,
        date_trunc('hour', event_ts)                                     as movement_hour,
        date_trunc('hour', any_value(event_local_ts))                    as movement_hour_local,
        hour(any_value(event_local_ts))                                  as hour_of_day_local,
        count(*) filter (where direction = 'arrival')                    as arrivals,
        count(*) filter (where direction = 'departure')                   as departures,
        count(*)                                                         as movements
    from {{ ref('stg_airport_flights') }}
    where is_plausible
    group by airport, flight_date, date_trunc('hour', event_ts)
)

select h.*, d.is_complete_day
from hourly h
join {{ ref('fct_airport_daily') }} d using (airport, flight_date)
