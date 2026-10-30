# HANDOVER
Newest entry on top. Read this + ARCHITECTURE.md + CONSTRAINTS.md first, update this last.

## 2026-10-30
Done:
- First live run on Windows + Docker Desktop: both DAGs green, dashboard live (580 aircraft, p95 API 260 ms).
- Fixed BUG-007 (start script died on docker stderr) and BUG-008 (airflow-init ran as root).
- Docker disk image moved to D:\docker-data (C: has little space).
In progress:
- Collecting live data for 7 days for README results.
Broken or risky:
- Running anonymously: 400 credits/day vs 288 used. Add OpenSky API client for headroom.
- Airflow UI shows Triggerer red: no triggerer service (not used by these DAGs).
Next:
- Push to GitHub, confirm CI green.
- After 7 days: measure, replace synthetic results in README.
Do not touch:
- `ARROW_SCHEMA` order/types (C-09), bounding box without D-002 maths (C-02).

## 2026-10-28
Done:
- Full repo: ingest client, transform, Blob storage, 2 DAGs, dbt (8 models, 25 tests), dashboard, Docker Compose, CI.
- Verified locally: ruff clean, pytest 17 passed / 1 skipped, dbt 33/33, negative test blocks publish.
