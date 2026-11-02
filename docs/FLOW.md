# FLOW

How execution actually travels. Entry point → output, file by file.

## Path 1: ingest (every 10 minutes)
```
Airflow scheduler (cron */10)
 └─ airflow/dags/opensky_ingest.py :: fetch_and_land()
     ├─ flightpipe/config.py :: get_settings()             env vars → Settings (bbox, creds, conn str)
     ├─ flightpipe/opensky_client.py :: OpenSkyClient.fetch_states()
     │    ├─ TokenManager.get_token()                      cached; refresh 60 s before 30-min expiry
     │    └─ GET /states/all?lamin&lomin&lamax&lomax       429 → CreditsExhausted → task SKIPPED
     │                                                      5xx → backoff 2,4,8 s → retry ×3
     │                                                      401 → refresh token once
     ├─ flightpipe/transform.py :: parse_states()          index → name; states=null → []
     ├─ flightpipe/transform.py :: to_parquet_bytes()      fixed ARROW_SCHEMA
     ├─ flightpipe/storage.py :: upload_snapshot()         raw/states/date=/hour=/states_<t>.parquet (overwrite)
     └─ flightpipe/storage.py :: upload_snapshot(path=run_meta_path_for) raw/runs/... (latency, rows, credits)
```

## Path 2: transform + publish (hourly at :05)
```
airflow/dags/flight_transform.py
 ├─ sync_lake()        storage.sync_to_local(): list raw/ → download missing → .part → os.replace
 ├─ dbt_build          /opt/dbt-venv/bin/dbt build --target docker
 │    sources.yml      read_parquet('/opt/lake/raw/states/**/*.parquet', hive_partitioning)
 │    stg_state_vectors   trim, unit convert, dedupe (icao24, snapshot_ts)
 │    stg_pipeline_runs
 │    fct_flight_phases → fct_traffic_hourly, dim_aircraft → fct_country_mix
 │    fct_pipeline_health, fct_data_quality
 │    tests: 20 generic + 5 singular (25 total). ANY failure → task fails → publish never runs
 └─ publish()          copy warehouse.duckdb → serving.duckdb.tmp → os.replace → serving.duckdb
```

## Path 3: a visitor opens the dashboard
```
browser :8501 → dashboard/app.py → duckdb.connect(serving.duckdb, read_only=True)
  → st.cache_data(ttl=300) → mart tables only (never stg views: they point at raw paths)
```

## Path 4: CI (every push / PR)
```
ruff → pytest (HTTP mocked) → generate_sample_data.py (same serializer) → dbt build → measure_pipeline.py → job summary
docker compose build → DagBag import check inside real Airflow image
```

## Path 5: airport flights (daily at 06:15 UTC, FEATURE-004)
```
airflow/dags/airport_flights_daily.py :: fetch_and_land_day()
 ├─ day = data_interval_end - 1 day                  (last complete UTC day; catchup fills missed days)
 ├─ for airport in AIRPORTS (EDDF, EDDM), direction in (arrival, departure):
 │    ├─ opensky_client.py :: fetch_airport_flights() -> _get('/flights/<direction>')   404 -> []
 │    ├─ transform.py :: flights_to_parquet()         fixed FLIGHT_SCHEMA
 │    └─ storage.py :: upload_snapshot(path=airport_flights_path())
 └─ hourly flight_transform picks the files up: sync_lake -> ensure_bootstrap_files -> dbt build
      stg_airport_flights -> fct_airport_hourly, fct_airport_daily, fct_routes (+ seed airports)
```
