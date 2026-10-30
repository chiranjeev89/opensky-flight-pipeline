"""Azure Blob Storage: write raw snapshots, sync them to a local lake cache.

Layout in the container (Hive-style partitions, docs/DATA.md):
    raw/states/date=YYYY-MM-DD/hour=HH/states_<snapshot_time>.parquet

WHY Hive partitions: dbt/DuckDB can prune by date/hour, and a human can find
any snapshot by browsing. WHY the snapshot time in the file name: re-running
the same Airflow interval overwrites the same blob -> idempotent, no
duplicates (docs/DECISIONS.md D-005).

WHY sync to a local cache before dbt: DuckDB's azure extension is unreliable
against the Azurite emulator, and the SDK works identically for Azurite and
real Azure. Blob stays the source of truth; the cache is disposable
(docs/DECISIONS.md D-003, revisit condition noted there).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContainerClient

log = logging.getLogger(__name__)

RAW_PREFIX = "raw/states/"
RUNS_PREFIX = "raw/runs/"
SYNC_PREFIX = "raw/"  # sync both states and run metrics


def blob_path_for(snapshot_time: int) -> str:
    """Deterministic blob name for a snapshot (same input -> same path)."""
    ts = datetime.fromtimestamp(snapshot_time, tz=UTC)
    return f"{RAW_PREFIX}date={ts:%Y-%m-%d}/hour={ts:%H}/states_{snapshot_time}.parquet"


def run_meta_path_for(snapshot_time: int) -> str:
    ts = datetime.fromtimestamp(snapshot_time, tz=UTC)
    return f"{RUNS_PREFIX}date={ts:%Y-%m-%d}/run_{snapshot_time}.parquet"


def get_container(conn_str: str, container: str) -> ContainerClient:
    service = BlobServiceClient.from_connection_string(conn_str)
    client = service.get_container_client(container)
    try:
        client.create_container()
        log.info("Created container %s", container)
    except ResourceExistsError:
        pass
    return client


def upload_snapshot(
    container: ContainerClient, snapshot_time: int, data: bytes, path: str | None = None
) -> str:
    path = path or blob_path_for(snapshot_time)
    # overwrite=True is what makes retries/backfills idempotent
    container.upload_blob(name=path, data=data, overwrite=True)
    log.info("Uploaded %s (%d bytes)", path, len(data))
    return path


def sync_to_local(container: ContainerClient, local_dir: str) -> int:
    """Download blobs that are missing locally. Returns number downloaded.

    Incremental by name: files are immutable per snapshot_time, so 'exists
    locally with same size' means 'already synced'.
    """
    root = Path(local_dir)
    downloaded = 0
    for blob in container.list_blobs(name_starts_with=SYNC_PREFIX):
        target = root / blob.name
        if target.exists() and target.stat().st_size == blob.size:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".part")
        with open(tmp, "wb") as fh:
            container.download_blob(blob.name).readinto(fh)
        os.replace(tmp, target)  # atomic: dbt never sees a half-written file
        downloaded += 1
    log.info("Synced %d new blobs to %s", downloaded, local_dir)
    return downloaded
