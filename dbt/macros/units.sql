{# Unit conversions used across models. Aviation reports altitude in feet and
   speed in knots, so marts use those; raw data stays SI (metres, m/s). #}
{% macro m_to_ft(col) %}({{ col }} * 3.28084){% endmacro %}
{% macro ms_to_kt(col) %}({{ col }} * 1.943844){% endmacro %}
{% macro ms_to_fpm(col) %}({{ col }} * 196.8504){% endmacro %}
