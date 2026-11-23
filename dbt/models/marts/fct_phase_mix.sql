-- Flight-phase share for the dashboard: a few rows instead of scanning every
-- observation on each page load (also keeps the public demo snapshot small).
select
    flight_phase,
    count(*)                                                    as observations,
    round(100.0 * count(*) / sum(count(*)) over (), 1)          as pct_of_observations
from {{ ref('fct_flight_phases') }}
group by 1
