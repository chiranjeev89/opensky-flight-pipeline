-- BUG-010: warn (not fail) when an airport day looks incomplete, e.g. 8 Nov 2026 with
-- 1 Frankfurt arrival instead of ~540. Warn only: the live pipeline must keep
-- publishing; the daily job re-fetches the last 3 days, and older days are repaired
-- by clearing their airport_flights_daily run (docs/OPERATIONS.md).
{{ config(severity = 'warn') }}
select airport, flight_date, movements, typical_movements
from {{ ref('fct_airport_daily') }}
where not is_complete_day
