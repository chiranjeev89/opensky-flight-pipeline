# FEATURE-001: OpenSky → Azure Blob ingestion
Goal: land one Germany snapshot every 10 min as Parquet in Blob, idempotently, without exceeding credits.
Scope: OAuth2 client, retries, parse, fixed schema, partitioned upload, run metrics. Out of scope: trajectory reconstruction.
Design: see FLOW.md path 1, D-002, D-005.
Steps:
- [x] TokenManager with cache + early refresh
- [x] fetch_states with 429/5xx/401 handling
- [x] parse_states + to_parquet_bytes (fixed schema)
- [x] deterministic blob path + overwrite
- [x] run metrics Parquet
- [x] unit tests (13)
- [x] first live run on Docker
Status: live since 2026-10-30.
Open questions: Q-01 backfill.

## Log
- 2026-10-28 Built and unit-tested locally.
- 2026-10-30 First live run on Docker (Windows): green after BUG-007/008 fixes.
