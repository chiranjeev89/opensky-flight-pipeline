-- FEATURE-004: every airport row must be one we collect. Anything else means the
-- AIRPORTS env var and the dbt var 'airports' drifted apart.
select distinct airport
from {{ ref('stg_airport_flights') }}
where airport not in ({% for a in var('airports') %}'{{ a }}'{% if not loop.last %}, {% endif %}{% endfor %})
