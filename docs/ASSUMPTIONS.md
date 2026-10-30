# ASSUMPTIONS & OPEN QUESTIONS
Status: ✅ verified · ❓ unverified · ❌ wrong. Clear every ❓ before calling the project "shipped".

| ID | Assumption | Status | How to verify |
|---|---|---|---|
| A-01 | Airflow 3.1.7 + LocalExecutor config works | ✅ | 2026-10-28: api-server, scheduler, dag-processor, LocalExecutor run with the compose env vars outside Docker ; scheduled runs of both DAGs green. Image build itself still to verify on first `docker compose up` |
| A-02 | ~~admin/admin login~~ ❌ was WRONG (option name) → fixed: no-login local mode | ✅ | BUG-005; UI returned 200 with `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True` |
| A-03 | api-server healthcheck path `/api/v2/version` returns 200 | ✅ | 2026-10-28: `{"version":"3.1.7"}` |
| A-04 | `/opt/lake` volume is writable by uid 50000 | ✅ | airflow-init now chowns it as root before anything else starts (dashboard waits for init) |
| A-05 | OpenSky field order (index 5 = lon, 6 = lat …) | ✅ | Checked against official REST docs 2026-10-28; bbox test also guards it |
| A-06 | Germany box = 2 credits; 4,000/day authenticated, 400 anonymous | ✅ | Official docs 2026-10-28 |
| A-07 | Token lifetime 30 min | ✅ | Official docs |
| A-08 | Real daytime traffic in box is 300-900 aircraft per snapshot | ❓ | `row_count` in fct_pipeline_health after day 1 |
| A-09 | X-Rate-Limit-Remaining header is returned on success | ❓ | `credits_remaining` not null in runs |
| A-10 | 2.5 m/s vertical-rate threshold separates climb/descent well | ❓ | Spot-check 20 aircraft against a flight tracker |
| A-11 | Synthetic numbers in README will be replaced | ❓ | README Results says "live" + date |

Open questions
- Q-01 Should missed snapshots during an outage be backfilled using `time=` (authenticated, ≤1 h back)? Currently no.
- Q-02 Move to real Azure (free student credits) or keep Azurite? Real Azure is a stronger CV line.
