-- FEATURE-004: busiest routes touching the collected airports.
-- A FRA->MUC flight appears in FRA departures AND MUC arrivals, so count each
-- physical flight once: (icao24, departure_ts) identifies it.
with flights as (
    select
        icao24,
        departure_ts,
        any_value(departure_airport)  as departure_airport,
        any_value(arrival_airport)    as arrival_airport,
        any_value(duration_min)       as duration_min,
        any_value(flight_date)        as flight_date
    from {{ ref('stg_airport_flights') }}
    where is_plausible
      and departure_airport is not null
      and arrival_airport is not null
      and departure_airport <> arrival_airport       -- round trips / training circuits
    group by icao24, departure_ts
),

routes as (
    select
        departure_airport,
        arrival_airport,
        count(*)                      as flights,
        round(median(duration_min), 0) as median_duration_min,
        min(flight_date)              as first_day,
        max(flight_date)              as last_day
    from flights
    group by 1, 2
)

select
    r.*,
    coalesce(d.iata, r.departure_airport) || ' → ' || coalesce(a.iata, r.arrival_airport) as route,
    coalesce(d.city, r.departure_airport) || ' → ' || coalesce(a.city, r.arrival_airport) as route_cities,
    a.country                                                                           as arrival_country,
    d.country                                                                           as departure_country
from routes r
left join {{ ref('airports') }} d on d.icao = r.departure_airport
left join {{ ref('airports') }} a on a.icao = r.arrival_airport
