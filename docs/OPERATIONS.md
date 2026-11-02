# OPERATIONS

How to run, pause, resume and find the data.

## Start / resume
1. Open **Docker Desktop**, wait for **Engine running**.
2. Double-click **start.bat**. It starts all containers, runs one ingest + one transform immediately, and opens:
   - Airflow: http://localhost:8080
   - Dashboard: http://localhost:8501

After the first build, a restart takes 1-3 minutes. From then on the pipeline runs by itself:
ingest every 10 minutes, transform at :05 past every hour, airport arrivals/departures once a day at 06:15 UTC (07:15 German winter time). If the laptop was off at 06:15, the missed days are fetched automatically on the next start (catchup).

## Pause / stop
- Double-click **stop.bat** (runs `docker compose down`). All data is kept.
- Quitting Docker Desktop, shutting down or sleeping the PC also pauses collection. Nothing breaks; the gap just lowers `completeness_pct` for that day.
- Missed snapshots cannot be fetched later (the API only serves live data).

## How long to collect
| Goal | Run for |
|---|---|
| Hourly chart shows a curve | 2+ hours |
| Day/night traffic pattern | 24-48 hours |
| README "Results" numbers | 7 days (can be paused in between) |

## Where the data lives
| Data | Location | Survives stop.bat? |
|---|---|---|
| Raw Parquet snapshots ("Blob storage") | Docker volume `opensky-flight-pipeline_azurite-data` (Azurite) | yes |
| Lake cache + `warehouse.duckdb` + `serving.duckdb` | Docker volume `opensky-flight-pipeline_lake` | yes |
| Airflow metadata (runs, history) | Docker volume `opensky-flight-pipeline_pg-data` | yes |
| Airflow task logs | `airflow/logs/` in this folder | yes |
| Docker volumes on disk | inside Docker's disk image (Docker Desktop → Settings → Resources → Advanced → Disk image location) | yes |

Browse the volumes in Docker Desktop → **Volumes**. Browse the raw blobs with Azure Storage Explorer → Local emulator → `flight-lake`.

**Data is deleted only by:** `docker compose down -v`, deleting the volumes in Docker Desktop, or "Clean / Purge data" in Docker Desktop troubleshooting.

## Copy the results database to this folder
```
docker compose cp dashboard:/opt/lake/serving.duckdb data/lake/serving.duckdb
python scripts/measure_pipeline.py --db data/lake/serving.duckdb
```

## Troubleshooting
| Symptom | Check |
|---|---|
| start.bat stops | read the red text; full output is in `start.log` |
| A container won't start | `docker compose logs <service> --tail 80` |
| Runs stay "queued" | DAG paused? Toggle it on in the Airflow UI (BUG-006) |
| `CreditsExhausted` / runs skipped | daily OpenSky credits used up; add API client keys to `.env` |

## After changing code in src/
DAG and dbt files are read live, but `src/flightpipe` is built into the Airflow image. After any change in `src/`, run **start.bat** (it rebuilds) or the DAGs will import the old code (seen 2026-11-02: one ImportError, fixed by the rebuild + retry).

