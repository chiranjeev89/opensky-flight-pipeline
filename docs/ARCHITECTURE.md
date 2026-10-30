# ARCHITECTURE

One page. The shape of the system, not the implementation. Deeper detail: [FLOW.md](FLOW.md), [DATA.md](DATA.md).

```
 TRUST BOUNDARY (outside input enters here)
 ─────────────────────────────────────────────────────────────────────────────
  OpenSky Network REST API  (third party, untrusted JSON)
        │ HTTPS + OAuth2 bearer token
 ─────────────────────────────────────────────────────────────────────────────
        ▼
  ┌──────────────── Docker Compose ─────────────────────────────────────────┐
  │                                                                          │
  │  Airflow 3 (api-server, scheduler, dag-processor, LocalExecutor)         │
  │    DAG opensky_ingest   every 10 min ──► Azure Blob  raw/states/…parquet │
  │                                                      raw/runs/…parquet   │
  │    DAG flight_transform hourly :05                                       │
  │       sync_lake ──► /opt/lake (cache) ──► dbt build ──► publish          │
  │                                         warehouse.duckdb   serving.duckdb│
  │                                                                │ (ro)    │
  │  Streamlit dashboard :8501  ◄────────────────────────────────────┘        │
  │  Postgres (Airflow metadata only)    Azurite (local Azure Blob emulator) │
  └──────────────────────────────────────────────────────────────────────────┘
  GitHub Actions: lint + pytest → dbt build on synthetic data → docker build + DAG import
```

| Module | Owns | Writes | Reads |
|---|---|---|---|
| `src/flightpipe/opensky_client.py` | OAuth2 token, HTTP calls, retries | – | OpenSky API |
| `src/flightpipe/transform.py` | Positional array → named, typed Parquet | bytes in memory | raw JSON |
| `src/flightpipe/storage.py` | Blob layout, upload, sync to cache | Blob, /opt/lake/raw | Blob |
| `airflow/dags/*` | Schedule, ordering, retries (no logic) | – | – |
| `dbt/` | Cleaning, business logic, data tests | warehouse.duckdb | /opt/lake/raw |
| `dashboard/app.py` | Presentation only | nothing | serving.duckdb (read-only mount) |

**Trust boundaries**
1. OpenSky → our code: untrusted data. Defended by fixed Parquet schema + dbt tests (physical limits, bbox, accepted values).
2. Secrets → containers: only via `.env` / CI secrets, never in images or git.
3. Dashboard → data: read-only volume mount, read-only DuckDB connection, no credentials in that container.

**Bronze / Silver / Gold**: raw Parquet in Blob (bronze) → `stg_*` views (silver) → `fct_*`/`dim_*` tables (gold).
