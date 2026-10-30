# DECISIONS

One entry per meaningful decision. Rejected options live in [ALTERNATIVES.md](ALTERNATIVES.md).

## D-001: Lightweight lakehouse (Blob + dbt + DuckDB) instead of a cloud warehouse
Date: 2026-10-28
Context: Student budget, must run on a laptop and in CI, but use industry tools recruiters look for.
Options: 1) Azure Synapse / Snowflake  2) Postgres  3) Blob + dbt-duckdb
Chosen: 3
Why: Same dbt skills and Blob storage as production stacks, €0 compute, runs in CI in seconds.
Trade-off: DuckDB is single-writer and single-node.
Revisit if: data > ~50 GB or several people need to query at once → move marts to Synapse/Snowflake/MotherDuck; dbt models move almost unchanged.

## D-002: Germany bounding box, every 10 minutes
Date: 2026-10-28
Context: /states/all costs 1/2/3/4 credits for ≤25 / 25-100 / 100-400 / >400 sq°. Authenticated users get 4,000 credits/day, anonymous 400.
Options: 1) worldwide every 5 min (4 × 288 = 1,152/day)  2) Germany every 10 min (2 × 144 = 288/day)  3) Germany every 1 min (2,880/day)
Chosen: 2
Why: Germany box = 7.79° × 9.17° ≈ 71 sq° → 2 credits. 288/day is 7% of the authenticated budget and still fits the anonymous quota, so the pipeline runs even without credentials. 10 min is enough for hourly traffic metrics. Aviation relevance: covers FRA/MUC, the busiest airspace near me.
Trade-off: 10 min snapshots cannot reconstruct full trajectories.
Revisit if: I need trajectory-level analytics → 1-min polling on a smaller box (≤25 sq° = 1 credit).
Guarded by: tests/test_storage.py::test_germany_box_stays_in_2_credit_tier.

## D-003: Sync Blob to a local cache before dbt, instead of DuckDB reading Blob directly
Date: 2026-10-28
Context: DuckDB's azure extension works against real Azure but is fragile against Azurite (local emulator).
Options: 1) duckdb azure extension (`az://`)  2) azure SDK download to shared volume  3) mount Blob with blobfuse
Chosen: 2
Why: Same SDK code path for Azurite and real Azure; incremental (skip existing); atomic writes. Blob stays the source of truth.
Trade-off: Duplicate copy on disk; sync time grows with file count.
Revisit if: running only against real Azure → switch sources to `az://` and drop sync_lake.

## D-004: ELT, not ETL (land raw, clean in dbt)
Date: 2026-10-28
Why: Raw data is never lost; cleaning rules are versioned SQL with tests; a bug in cleaning is fixed by re-running dbt, not re-ingesting (which is impossible for a live API).
Trade-off: Bad rows are stored in bronze.

## D-005: Deterministic blob names + overwrite=True (idempotency)
Date: 2026-10-28
Why: Airflow retries a task after partial success. Same snapshot_time → same path → overwrite, so a retry can never duplicate data. Staging also dedupes on (icao24, snapshot_ts) as a second line of defence.

## D-006: Publish a separate serving.duckdb after tests pass
Date: 2026-10-28
Context: DuckDB allows one writer; dashboard reading the same file during dbt build → lock errors. Also, a failing test must not show bad data.
Options: 1) dashboard reads warehouse directly  2) copy + atomic rename after dbt build  3) export marts to Postgres
Chosen: 2
Why: Zero extra services; dashboard always sees a complete, tested snapshot; failed tests = old data stays up.
Trade-off: Up to 1 h staleness; DB file copied every hour (small: tens of MB).

## D-007: dbt in its own virtualenv inside the Airflow image
Why: dbt-core and apache-airflow pin conflicting dependency versions. A separate venv invoked via BashOperator avoids dependency hell. Rejected: Cosmos (extra dependency, more magic to defend), separate dbt container (needs docker socket = security risk).

## D-008: No dbt packages (hand-written unique-combination test)
Why: One 6-line macro vs a package dependency; zero network in `dbt build`; fewer supply-chain risks.

## D-009: Streamlit instead of Power BI / Grafana / Superset
Why: Python, runs in Docker, free, version-controlled code, anyone can open it. Power BI needs Windows/licence for sharing; Superset is heavy for one dashboard.
Revisit if: business users need self-serve slicing → Superset or Power BI on the marts.

## D-010: Airflow LocalExecutor (no Celery/Redis)
Why: 2 DAGs, a few tasks per hour. Celery adds Redis + workers + flower with no benefit at this scale.
Revisit if: > ~20 concurrent tasks or tasks need separate machines.

## D-011: Synthetic data in CI instead of live API
Why: CI must be deterministic, free and credential-free. Synthetic data goes through the real `parse_states` + `to_parquet_bytes`, so serializer bugs still fail CI. All synthetic callsigns start with `SIM`.
Trade-off: CI cannot catch OpenSky changing its format → covered by dbt tests on live data in Airflow.
