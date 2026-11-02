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


def test_airport_flights_path_is_deterministic():
    from datetime import date

    from flightpipe.storage import airport_flights_path

    assert (
        airport_flights_path("EDDF", "arrival", date(2026, 11, 1))
        == "raw/airport_flights/date=2026-11-01/EDDF_arrival.parquet"
    )


def test_bootstrap_written_once_and_only_when_needed(tmp_path):
    from flightpipe.storage import ensure_bootstrap_files

    first = ensure_bootstrap_files(str(tmp_path))
    assert len(first) == 1 and first[0].endswith("_bootstrap.parquet")
    assert ensure_bootstrap_files(str(tmp_path)) == []  # idempotent


def test_bootstrap_skipped_when_real_files_exist(tmp_path):
    from flightpipe.storage import ensure_bootstrap_files

    real = tmp_path / "raw/airport_flights/date=2026-11-01/EDDF_arrival.parquet"
    real.parent.mkdir(parents=True)
    real.write_bytes(b"x")
    assert ensure_bootstrap_files(str(tmp_path)) == []


def test_default_airports_are_frankfurt_and_munich(monkeypatch):
    from flightpipe.config import get_settings

    monkeypatch.delenv("AIRPORTS", raising=False)
    assert get_settings().airports == ("EDDF", "EDDM")
    monkeypatch.setenv("AIRPORTS", " eddf, eddm ,edds")
    assert get_settings().airports == ("EDDF", "EDDM", "EDDS")
