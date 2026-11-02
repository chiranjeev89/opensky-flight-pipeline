-- Data freshness for airports: the newest complete day should be at most
-- max_airport_data_age_days old. Warn only: OpenSky's nightly batch can be late,
-- and stale airport data must not block the live traffic publish.
{{ config(severity = 'warn') }}
select max(flight_date) as newest_day
from {{ ref('stg_airport_flights') }}
having count(*) > 0
   and max(flight_date) < current_date - {{ var('max_airport_data_age_days') }}
