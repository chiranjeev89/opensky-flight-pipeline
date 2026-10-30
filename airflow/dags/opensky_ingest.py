"""DAG 1/2: opensky_ingest - pull one snapshot every 10 minutes into Azure Blob.

Flow (docs/FLOW.md): fetch /states/all -> parse -> Parquet -> upload to
raw/states/... and a run-metrics row to raw/runs/...

Schedule maths (docs/DECISIONS.md D-002):
    144 runs/day x 2 credits (Germany box, 25-100 sq deg) = 288 credits/day
    vs 4,000/day authenticated (7% of budget) - even fits the 400/day anonymous quota.

All business logic is in src/flightpipe so it is unit-tested; this file only
wires tasks together (keep DAG files thin, docs/CONSTRAINTS.md C-07).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from airflow.exceptions import AirflowSkipException
from airflow.sdk import dag, task

DEFAULT_ARGS = {
    "owner": "chiranjeev",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=5),  # a stuck call must not block the next run
}


@dag(
    dag_id="opensky_ingest",
    schedule="*/10 * * * *",
    start_date=datetime(2026, 10, 1, tzinfo=UTC),
    catchup=False,  # live API: history only reachable 1h back (authenticated), so no backfill
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["opensky", "ingest"],
)
def opensky_ingest():
    @task
    def fetch_and_land() -> dict:
        # Imports inside the task keep DAG parsing fast (dag-processor parses often).
        from flightpipe.config import get_settings
        from flightpipe.opensky_client import CreditsExhausted, OpenSkyClient
        from flightpipe.storage import get_container, run_meta_path_for, upload_snapshot
        from flightpipe.transform import parse_states, run_meta_to_parquet, to_parquet_bytes

        settings = get_settings()
        client = OpenSkyClient(settings)
        started = datetime.now(UTC)

        t0 = time.perf_counter()
        try:
            raw = client.fetch_states()
        except CreditsExhausted as exc:
            # Skipped, not failed: retrying cannot help until credits reset.
            raise AirflowSkipException(str(exc)) from exc
        latency_ms = (time.perf_counter() - t0) * 1000

        records = parse_states(raw, ingested_at=started)
        snapshot_time = int(raw.get("time") or started.timestamp())
        data = to_parquet_bytes(records)

        container = get_container(settings.azure_conn_str, settings.azure_container)
        path = upload_snapshot(container, snapshot_time, data)

        meta = {
            "snapshot_time": snapshot_time,
            "run_started_at": started,
            "api_latency_ms": round(latency_ms, 1),
            "row_count": len(records),
            "parquet_bytes": len(data),
            "credits_remaining": client.last_credits_remaining,
            "status": "success",
        }
        upload_snapshot(
            container, snapshot_time, run_meta_to_parquet(meta), path=run_meta_path_for(snapshot_time)
        )
        # Only small metadata goes to XCom, never the data itself.
        return {"path": path, "rows": len(records), "latency_ms": meta["api_latency_ms"]}

    fetch_and_land()


opensky_ingest()
