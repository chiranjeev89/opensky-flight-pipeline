"""DAG files must parse. Skipped when Airflow is not installed (runs in Docker CI job)."""

from pathlib import Path

import pytest

DAG_DIR = Path(__file__).resolve().parents[1] / "airflow" / "dags"


def test_dags_have_no_import_errors():
    # importorskip on the submodule: the repo's airflow/ folder is importable as a
    # namespace package, so importing just "airflow" would falsely succeed.
    pytest.importorskip("airflow.models")
    from airflow.models import DagBag

    bag = DagBag(dag_folder=str(DAG_DIR), include_examples=False)
    assert bag.import_errors == {}
    assert {"opensky_ingest", "flight_transform"} <= set(bag.dag_ids)
