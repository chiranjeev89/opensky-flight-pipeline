{# Generic test: combination of columns is unique. Written by hand instead of
   pulling dbt_utils so the project has zero package dependencies (D-008). #}
{% test dbt_utils_free_unique_combo(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
