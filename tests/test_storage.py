from flightpipe.config import BoundingBox
from flightpipe.storage import blob_path_for, run_meta_path_for


def test_blob_path_is_deterministic_and_partitioned():
    p = blob_path_for(1761660000)  # 2025-10-28 14:00 UTC
    assert p == "raw/states/date=2025-10-28/hour=14/states_1761660000.parquet"
    assert blob_path_for(1761660000) == p  # idempotent re-runs overwrite, not duplicate


def test_run_meta_path():
    assert run_meta_path_for(1761660000) == "raw/runs/date=2025-10-28/run_1761660000.parquet"


def test_germany_box_stays_in_2_credit_tier():
    # 25-100 sq deg = 2 credits. If someone widens the box past 100, this fails
    # and forces them to update the credit budget in docs/DECISIONS.md D-002.
    assert 25 < BoundingBox().area_sq_deg <= 100


def test_empty_env_value_falls_back_to_default(monkeypatch):
    # BUG-003: compose passes "KEY=" from .env as an empty string
    from flightpipe.config import AZURITE_CONN_STR, get_settings

    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    assert get_settings().azure_conn_str == AZURITE_CONN_STR
