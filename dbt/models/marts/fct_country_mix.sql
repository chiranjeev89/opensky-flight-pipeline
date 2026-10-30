-- Share of unique aircraft by registration country (inferred from ICAO block).
with per_country as (
    select origin_country, count(*) as unique_aircraft
    from {{ ref('dim_aircraft') }}
    group by 1
)
select
    origin_country,
    unique_aircraft,
    round(100.0 * unique_aircraft / sum(unique_aircraft) over (), 2) as pct_of_aircraft
from per_country
