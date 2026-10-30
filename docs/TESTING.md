# TESTING

Real commands and what a pass looks like. Paste real output, never "tests pass".

| # | Command | Pass looks like |
|---|---|---|
| 1 | `ruff check . && ruff format --check .` | `All checks passed!` |
| 2 | `pytest -q` | `16 passed, 1 skipped` (DAG import test skips without Airflow; it runs in CI docker job) |
| 3 | `make sample` | `Wrote 433 synthetic snapshots to data/lake` |
| 4 | `make dbt` | `Done. PASS=33 WARN=0 ERROR=0 SKIP=0` |
| 5 | **Negative test**: `python scripts/inject_bad_snapshot.py` then `make dbt` (undo with `--remove`) | `FAIL 1 assert_altitude_physically_possible`, `FAIL 1 assert_speed_physically_possible`, `FAIL 1 assert_positions_inside_bbox`, `SKIP=15` (marts not built → nothing published) |
| 6 | `make measure` | Markdown results table |
| 7 | `docker compose up -d --build` then open http://localhost:8080 | Both DAGs listed, unpaused, `opensky_ingest` green within 10 min |
| 8 | Azurite check: `az storage blob list --connection-string "$AZURITE" -c flight-lake -o table` (or Azure Storage Explorer) | `raw/states/date=.../states_*.parquet` files |
| 9 | After :05 past the hour → http://localhost:8501 | KPIs filled, "Data as of" < 1 h old |

## What the unit tests cover
- Field mapping by name, lon/lat order (index 5 vs 6), null `states`, short rows, extra fields, all-null columns, empty Parquet.
- Client: bearer header + bbox params, token caching, 429 no-retry, 5xx retry then success, 5xx give up, 401 refresh once, secret not leaked in errors.
- Storage: deterministic partition paths, credit-tier guard on the bbox.

## Manual customer path (do before every release)
Open dashboard → KPIs non-zero → chart has the last 24 h → map shows dots over Germany → pipeline health table shows today.

## Last verified run (2026-10-28, local, synthetic 72 h)
```
ruff: All checks passed!
pytest: 16 passed, 1 skipped in 0.82s
dbt build: Done. PASS=33 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=33
negative test: 3 FAIL, 15 SKIP (publish blocked)
dashboard AppTest: no exceptions; metrics rendered
```
