-- Same rule as BUG-009: a few bad flight records are flagged and skipped, but if
-- more than max_glitch_share of a day is implausible, the feed itself is broken.
select airport, flight_date, count(*) as rows_in_day,
       sum(case when not is_plausible then 1 else 0 end) as implausible_rows
from {{ ref('stg_airport_flights') }}
group by 1, 2
having sum(case when not is_plausible then 1 else 0 end) > {{ var('max_glitch_share') }} * count(*)
