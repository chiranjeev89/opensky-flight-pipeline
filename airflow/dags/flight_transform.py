"""DAG 2/3: flight_transform - hourly: sync Blob -> run dbt build -> publish.

Flow (docs/FLOW.md steps 3-5):
    sync_lake      download new Parquet from Blob to the shared /opt/lake volume
    dbt_build      dbt deps-free build: run models + run all tests
    publish        atomically copy warehouse.duckdb -> serving.duckdb

WHY a separate serving copy: DuckDB allows one writer. If the dashboard read
warehouse.duckdb directly, every dbt run would hit a lock conflict. Copy +
os.replace means the dashboard always sees a complete, tested database
(docs/DECISIONS.md D-006, docs/FAILURE.md F-05).

WHY publish only after dbt_build succeeds: if any dbt test fails, the task
fails, publish never runs, and the dashboard keeps the last good data.
Bad data never reaches the screen.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

DBT_DIR = "/opt/airflow/dbt"
DBT_BIN = "/opt/dbt-venv/bin/dbt"  # isolated venv: dbt and Airflow pin conflicting deps (D-007)


@dag(
    dag_id="flight_transform",
    schedule="5 * * * *",  # :05 past the hour so the :00 ingest has landed
    start_date=datetime(2026, 10, 1, tzinfo=UTC),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "chiranjeev", "retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["dbt", "transform"],
)
def flight_transform():
    @task
    def sync_lake() -> int:
        from flightpipe.config import get_settings
        from flightpipe.storage import ensure_bootstrap_files, get_container, sync_to_local

        s = get_settings()
        n = sync_to_local(get_container(s.azure_conn_str, s.azure_container), s.local_lake_dir)
        # FEATURE-004: datasets that arrive daily need a 0-row stand-in until their first file
        ensure_bootstrap_files(s.local_lake_dir)
        return n

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {DBT_DIR} && {DBT_BIN} build --profiles-dir . --target docker",
        env={"LOCAL_LAKE_DIR": "/opt/lake", "DBT_DUCKDB_PATH": "/opt/lake/warehouse.duckdb"},
        append_env=True,
    )

    @task
    def publish() -> str:
        import os
        import shutil

        src = "/opt/lake/warehouse.duckdb"
        tmp = "/opt/lake/serving.duckdb.tmp"
        dst = "/opt/lake/serving.duckdb"
        shutil.copyfile(src, tmp)
        os.replace(tmp, dst)  # atomic rename on the same filesystem
        return dst

    sync_lake() >> dbt_build >> publish()


flight_transform()
