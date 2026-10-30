"""Tests for parsing the positional OpenSky array (docs/FAILURE.md F-04)."""

import io
from datetime import UTC, datetime

import pyarrow.parquet as pq

from flightpipe.transform import ARROW_SCHEMA, parse_states, to_parquet_bytes

T = 1761660000
ROW = [
    "3c6444",
    "DLH9LF  ",
    "Germany",
    T - 2,
    T - 1,
    8.57,
    50.03,
    10972.8,
    False,
    231.5,
    87.2,
    -0.3,
    None,
    11010.9,
    "1000",
    False,
    0,
]


def test_maps_fields_by_name():
    rec = parse_states({"time": T, "states": [ROW]})[0]
    assert rec["icao24"] == "3c6444"
    assert rec["longitude"] == 8.57 and rec["latitude"] == 50.03  # index 5 = lon, 6 = lat
    assert rec["baro_altitude"] == 10972.8
    assert rec["snapshot_time"] == T
    assert "sensors" not in rec


def test_null_states_means_empty_sky_not_crash():
    assert parse_states({"time": T, "states": None}) == []


def test_short_row_without_category_is_ok():
    rec = parse_states({"time": T, "states": [ROW[:17]]})[0]
    assert rec["position_source"] == 0


def test_extra_unknown_fields_are_ignored():
    rec = parse_states({"time": T, "states": [ROW + [3, "future-field"]]})[0]
    assert rec["icao24"] == "3c6444"


def test_parquet_schema_is_fixed_even_when_all_null():
    rows = [ROW[:14] + [None, False, 0]]  # squawk null in every row
    data = to_parquet_bytes(parse_states({"time": T, "states": rows}, ingested_at=datetime.now(UTC)))
    table = pq.read_table(io.BytesIO(data))
    assert table.schema.equals(ARROW_SCHEMA, check_metadata=False)
    assert table.num_rows == 1


def test_empty_snapshot_still_writes_valid_parquet():
    table = pq.read_table(io.BytesIO(to_parquet_bytes([])))
    assert table.num_rows == 0 and table.schema.names == ARROW_SCHEMA.names
