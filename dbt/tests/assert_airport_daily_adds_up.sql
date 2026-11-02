-- Movements must equal arrivals + departures, and hourly totals must add up to the day.
with hourly as (
    select airport, cast(movement_hour as date) as d, sum(movements) as m
    from {{ ref('fct_airport_hourly') }}
    group by 1, 2
)
select daily.airport, daily.flight_date, daily.movements, daily.arrivals, daily.departures
from {{ ref('fct_airport_daily') }} daily
where daily.movements <> daily.arrivals + daily.departures
union all
select h.airport, h.d, h.m, null, null
from hourly h
left join (
    select airport, cast(event_ts as date) as d, count(*) as m
    from {{ ref('stg_airport_flights') }}
    where is_plausible
    group by 1, 2
) s using (airport, d)
where h.m <> s.m
