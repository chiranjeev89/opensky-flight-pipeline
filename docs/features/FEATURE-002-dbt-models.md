# FEATURE-002: dbt models + data tests
Goal: turn raw snapshots into tested hourly traffic, phases, aircraft, health and quality marts.
Design: bronze → stg views → mart tables. DATA.md §3-4.
Steps:
- [x] sources over Hive-partitioned Parquet (union_by_name)
- [x] stg_state_vectors (clean, convert, dedupe), stg_pipeline_runs
- [x] 6 marts
- [x] 20 generic + 5 singular (25 total) tests, freshness as warn
- [x] negative test proves bad data blocks publish
Status: done (synthetic). Re-check thresholds on live data (A-10).

## Log
- 2026-10-28 33/33 PASS on 72 h synthetic data; negative test 3 FAIL / 15 SKIP.
