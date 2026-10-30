# BUG-002: Dashboard map would break on the serving copy
Symptom (caught in review, before running): map query read `stg_state_vectors`.
Root cause: staging models are **views** whose SQL points at `read_parquet('/opt/lake/raw/...')`. That works, but couples the dashboard to raw file paths and does a full Parquet scan per page load. If the dashboard container ever lacks the raw path, the view fails.
Fix: add latitude/longitude to `fct_flight_phases` (a table) and query that. Rule added: dashboard reads marts only (FLOW.md path 3).
Verification: Streamlit AppTest run → no exceptions, all 4 metrics rendered.
