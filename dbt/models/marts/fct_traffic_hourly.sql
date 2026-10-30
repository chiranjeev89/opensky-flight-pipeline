-- Hourly traffic over the bounding box: the headline dashboard metric.
select
    snapshot_hour,
    count(distinct icao24)                                          as unique_aircraft,
    count(distinct case when flight_phase <> 'ground' then icao24 end) as airborne_aircraft,
    count(*)                                                        as observations,
    count(distinct snapshot_ts)                                     as snapshots,
    round(avg(case when flight_phase = 'cruise' then altitude_ft end), 0)     as avg_cruise_altitude_ft,
    round(avg(case when flight_phase = 'cruise' then ground_speed_kt end), 0) as avg_cruise_speed_kt,
    sum(case when flight_phase = 'climb' then 1 else 0 end)         as climb_obs,
    sum(case when flight_phase = 'descent' then 1 else 0 end)       as descent_obs
from {{ ref('fct_flight_phases') }}
group by 1
