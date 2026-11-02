"""Turn the raw OpenSky positional array into typed, named records.

WHY this exists: OpenSky returns each aircraft as a *positional list* of 17-18
values. Index-based access is fragile and unreadable, so we name every field
once, here, and everything downstream (Parquet, dbt) uses names.
Field order is from the official OpenSky REST docs (docs/DATA.md).

We deliberately do NOT clean or filter here (no dropping nulls, no unit
conversion). Raw data is landed as-is; cleaning lives in dbt staging where it
is tested and versioned. See docs/DECISIONS.md D-004 (ELT, not ETL).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq

# Index -> name, exactly as documented by OpenSky for /states/all.
STATE_FIELDS: list[str] = [
    "icao24",  # 0  unique ICAO 24-bit transponder address (hex)
    "callsign",  # 1  can be null / padded with spaces
    "origin_country",  # 2  inferred from ICAO address
    "time_position",  # 3  unix s of last position update, nullable
    "last_contact",  # 4  unix s of last message received
    "longitude",  # 5  WGS-84 degrees, nullable
    "latitude",  # 6  WGS-84 degrees, nullable
    "baro_altitude",  # 7  metres, nullable
    "on_ground",  # 8  bool
    "velocity",  # 9  m/s over ground, nullable
    "true_track",  # 10 degrees clockwise from north, nullable
    "vertical_rate",  # 11 m/s, nullable
    "sensors",  # 12 receiver ids, usually null -> dropped (not useful)
    "geo_altitude",  # 13 metres, nullable
    "squawk",  # 14 transponder code, nullable
    "spi",  # 15 special purpose indicator
    "position_source",  # 16 0=ADS-B 1=ASTERIX 2=MLAT 3=FLARM
    "category",  # 17 aircraft category (only with extended=1), optional
]

ARROW_SCHEMA = pa.schema(
    [
        ("snapshot_time", pa.int64()),
        ("ingested_at", pa.timestamp("us", tz="UTC")),
        ("icao24", pa.string()),
        ("callsign", pa.string()),
        ("origin_country", pa.string()),
        ("time_position", pa.int64()),
        ("last_contact", pa.int64()),
        ("longitude", pa.float64()),
        ("latitude", pa.float64()),
        ("baro_altitude", pa.float64()),
        ("on_ground", pa.bool_()),
        ("velocity", pa.float64()),
        ("true_track", pa.float64()),
        ("vertical_rate", pa.float64()),
        ("geo_altitude", pa.float64()),
        ("squawk", pa.string()),
        ("spi", pa.bool_()),
        ("position_source", pa.int64()),
    ]
)


def parse_states(raw: dict, ingested_at: datetime | None = None) -> list[dict]:
    """Map the raw API response to a list of named dicts.

    Handles: states == None (empty sky), short rows (no 'category'), and
    extra unknown trailing fields (forward compatible: ignored).
    """
    ingested_at = ingested_at or datetime.now(UTC)
    snapshot_time = int(raw.get("time") or 0)
    rows = raw.get("states") or []  # API returns null, not [], when empty

    records: list[dict] = []
    for row in rows:
        rec = {name: (row[i] if i < len(row) else None) for i, name in enumerate(STATE_FIELDS)}
        rec.pop("sensors", None)
        rec.pop("category", None)
        rec["snapshot_time"] = snapshot_time
        rec["ingested_at"] = ingested_at
        records.append(rec)
    return records


def to_parquet_bytes(records: list[dict]) -> bytes:
    """Serialize records to Parquet with a fixed schema.

    WHY a fixed schema: Parquet infers types from data; a snapshot where every
    squawk is null would infer 'null' type and break the dbt union later.
    Forcing ARROW_SCHEMA keeps every file identical in shape.
    """
    columns = {name: [r.get(name) for r in records] for name in ARROW_SCHEMA.names}
    table = pa.Table.from_pydict(columns, schema=ARROW_SCHEMA)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


RUN_SCHEMA = pa.schema(
    [
        ("snapshot_time", pa.int64()),
        ("run_started_at", pa.timestamp("us", tz="UTC")),
        ("api_latency_ms", pa.float64()),
        ("row_count", pa.int64()),
        ("parquet_bytes", pa.int64()),
        ("credits_remaining", pa.int64()),
        ("status", pa.string()),
    ]
)


def run_meta_to_parquet(meta: dict) -> bytes:
    """One-row Parquet with metrics about a single ingest run.

    WHY: 'measure' needs numbers we can query later (latency, rows, credits)
    without scraping Airflow logs. dbt builds fct_pipeline_health from these.
    """
    table = pa.Table.from_pydict({n: [meta.get(n)] for n in RUN_SCHEMA.names}, schema=RUN_SCHEMA)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# FEATURE-004: airport arrivals/departures (/flights/arrival, /flights/departure)
# Unlike /states/all these are JSON objects with names, so no index mapping is
# needed. We still force a fixed schema (same reason as ARROW_SCHEMA) and add
# which query produced the row: the same flight can appear in FRA departures
# AND MUC arrivals; dbt dedupes it for route counts.
# ---------------------------------------------------------------------------

FLIGHT_FIELDS = [
    "icao24",
    "firstSeen",
    "estDepartureAirport",
    "lastSeen",
    "estArrivalAirport",
    "callsign",
    "estDepartureAirportHorizDistance",
    "estDepartureAirportVertDistance",
    "estArrivalAirportHorizDistance",
    "estArrivalAirportVertDistance",
    "departureAirportCandidatesCount",
    "arrivalAirportCandidatesCount",
]

FLIGHT_SCHEMA = pa.schema(
    [
        ("query_airport", pa.string()),
        ("direction", pa.string()),
        ("flight_date", pa.date32()),
        ("ingested_at", pa.timestamp("us", tz="UTC")),
        ("icao24", pa.string()),
        ("first_seen", pa.int64()),
        ("est_departure_airport", pa.string()),
        ("last_seen", pa.int64()),
        ("est_arrival_airport", pa.string()),
        ("callsign", pa.string()),
        ("dep_horiz_distance_m", pa.int64()),
        ("dep_vert_distance_m", pa.int64()),
        ("arr_horiz_distance_m", pa.int64()),
        ("arr_vert_distance_m", pa.int64()),
        ("dep_candidates", pa.int64()),
        ("arr_candidates", pa.int64()),
    ]
)

_FLIGHT_RENAME = dict(zip(FLIGHT_FIELDS, FLIGHT_SCHEMA.names[4:], strict=True))


def flights_to_parquet(
    flights: list[dict],
    query_airport: str,
    direction: str,
    flight_date,
    ingested_at: datetime | None = None,
) -> bytes:
    """Serialize one airport/direction/day of flights with FLIGHT_SCHEMA.

    Unknown extra keys are ignored; missing keys become null. Raw values are
    kept as sent (ELT, D-004); cleaning happens in stg_airport_flights.
    """
    ingested_at = ingested_at or datetime.now(UTC)
    rows = []
    for f in flights:
        rec = {new: f.get(old) for old, new in _FLIGHT_RENAME.items()}
        rec.update(
            query_airport=query_airport,
            direction=direction,
            flight_date=flight_date,
            ingested_at=ingested_at,
        )
        rows.append(rec)
    columns = {name: [r.get(name) for r in rows] for name in FLIGHT_SCHEMA.names}
    table = pa.Table.from_pydict(columns, schema=FLIGHT_SCHEMA)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()
