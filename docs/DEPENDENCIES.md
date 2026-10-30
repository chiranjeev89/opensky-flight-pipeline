# DEPENDENCY & SECRETS LOG

## Python / images
| Package | Why | Maintainer | Pinned |
|---|---|---|---|
| apache/airflow image | Orchestration | Apache Software Foundation | `3.1.7-python3.12` |
| requests | HTTP to OpenSky | PSF | `>=2.32,<3` |
| pyarrow | Parquet with fixed schema | Apache Arrow | `>=17,<27` |
| azure-storage-blob | Blob upload/list/download | Microsoft | `>=12.20,<13` |
| dbt-duckdb (+dbt-core) | Transform + tests | dbt Labs / DuckDB community | `==1.11.1` (own venv) |
| duckdb | Warehouse engine, dashboard reads | DuckDB Labs | `>=1.1,<3` |
| streamlit, pandas | Dashboard | Snowflake / NumFOCUS | ranges in requirements-dashboard.txt |
| pytest, responses, ruff | Dev only | PyTest / getsentry / Astral | requirements-dev.txt |
| postgres:16, azurite | Airflow metadata / Blob emulator | PostgreSQL / Microsoft | `16` / `latest` (TODO pin) |

No dbt packages (D-008).

## Secrets
| Secret | Where it lives | Who reads it | Rotation |
|---|---|---|---|
| OPENSKY_CLIENT_ID / SECRET | `.env` (git-ignored) | Airflow containers | Delete + recreate API client on opensky-network.org |
| AZURE_STORAGE_CONNECTION_STRING | `.env` | Airflow containers only (NOT dashboard) | Rotate key in Azure portal; prefer SAS / Managed Identity |
| AIRFLOW_JWT_SECRET | `.env` | Airflow | Change any time, restart |
| Azurite dev key | in `config.py` | – | Public Microsoft dev key, not a secret |

Before every commit: `git diff --cached | grep -iE "secret|key|token|password"` and check nothing from `.env` appears.
