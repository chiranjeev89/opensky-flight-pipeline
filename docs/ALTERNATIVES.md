# ALTERNATIVES

What I turned down, the cost of each, and what would change my mind.

| Decision | Chosen | Rejected | Why rejected | Revisit if |
|---|---|---|---|---|
| Orchestrator | Airflow 3 | Cron + scripts | No retries, no UI, no dependency graph, no backfill concept | – |
| | | Prefect / Dagster | Fine tools, but Airflow appears in far more German job ads (Data Engineer roles) | A team already uses them |
| | | Azure Data Factory | Cost, click-ops, hard to version-control & run locally | Company is all-in on Azure |
| Storage | Azure Blob (Azurite locally) | Local disk only | Not a cloud skill; no separation of storage and compute | – |
| | | AWS S3 | Equivalent; Azure chosen because many German enterprises (and Airbus-side stacks) run on Azure | Target employer uses AWS |
| | | ADLS Gen2 | Better for hierarchical namespace, but Azurite does not emulate it fully | Moving to real Azure → enable HNS |
| File format | Parquet | JSON / CSV | 5-8x bigger, untyped, slow to scan | – |
| | | Delta / Iceberg | ACID + time travel, but overkill for append-only immutable snapshots | Need updates/deletes or schema evolution |
| Transform | dbt | Pandas scripts | No lineage, no tests, no docs, logic hidden in Python | – |
| Warehouse | DuckDB | Postgres | Row store, slower for analytics, another server | Many concurrent writers |
| | | Snowflake / Synapse | Cost; can't run in CI for free | Data > 50 GB, team access |
| Dashboard | Streamlit | Power BI | Licence, Windows, not in git | Business users |
| | | Grafana | Great for time series/ops, weaker for ad-hoc tables | Pure monitoring use case |
| Ingest frequency | 10 min | 1 min | 10x credits (2,880/day, 72% of quota), no room for retries | Trajectory analysis on ≤25 sq° box |
| dbt in Airflow | venv + BashOperator | astronomer-cosmos | Extra dependency, more abstraction to defend | Many models needing per-model retries |
| | | Docker-in-Docker | Mounting docker.sock gives root on host | – |
| Serving | copy + atomic rename | Read warehouse directly | DuckDB lock conflicts; would show untested data | – |
