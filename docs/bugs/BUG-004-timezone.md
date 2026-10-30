# BUG-004: Timestamps shown in machine-local time, labelled UTC
Symptom: dashboard "Data as of (UTC)" showed 19:40 when UTC was 18:40 (dev machine clock = UTC+1).
Root cause: `to_timestamp()` gives TIMESTAMPTZ; DuckDB renders and `date_trunc('hour')` buckets in the session TimeZone, which defaults to the host's.
Impact: hourly buckets would shift on a laptop in Germany (CET/CEST), and DST changes could merge or split hours.
Fix: `settings: TimeZone: UTC` in every dbt target; `SET TimeZone='UTC'` in dashboard and measure script.
Verification: rebuilt → "Data as of (UTC) 18:40" at 18:42 UTC; dbt 33/33.
