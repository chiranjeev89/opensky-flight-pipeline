# DATA

## 1. Raw state vector (OpenSky → bronze Parquet)
- **Shape in API**: positional JSON array, 17-18 values per aircraft (index 0 icao24 … 5 longitude, 6 latitude … 16 position_source, 17 category). Order verified against the official OpenSky REST docs.
- **Shape stored**: named columns, fixed `ARROW_SCHEMA` (18 columns incl. `snapshot_time`, `ingested_at`). Units kept as SI (m, m/s).
- **Why Parquet**: columnar + compressed (~26 KB per 300-aircraft snapshot in testing), schema embedded, DuckDB reads it natively. JSON would be ~5-8x larger and untyped.
- **Why fixed schema**: Parquet infers types per file. A snapshot where every `squawk` is null would become type `null` and break the union across files.
- **Layout**: `raw/states/date=YYYY-MM-DD/hour=HH/states_<unix>.parquet` (Hive partitions → partition pruning; deterministic name → idempotent overwrite).
- **Size**: Germany box ≈ 300-900 aircraft/snapshot by day. 144 snapshots/day ≈ 4-10 MB/day ≈ 1.5-3.5 GB/year. Trivial for Blob (cents/month).
- **Writer**: only `opensky_ingest` DAG. **Readers**: `sync_lake` task.

## 2. Run metrics (`raw/runs/...`)
One row per ingest run: `snapshot_time, run_started_at, api_latency_ms, row_count, parquet_bytes, credits_remaining, status`.
Exists so "measure" numbers come from data, not from reading Airflow logs.

## 3. Warehouse (DuckDB file)
| Model | Grain | Type | Key test |
|---|---|---|---|
| stg_state_vectors | aircraft × snapshot | view | unique (icao24, snapshot_ts) |
| stg_pipeline_runs | run | view | unique snapshot_ts |
| fct_flight_phases | aircraft × snapshot (with position) | table | accepted phase values |
| fct_traffic_hourly | hour | table | unique hour |
| dim_aircraft | transponder | table | unique icao24 |
| fct_country_mix | country | table | unique country |
| fct_pipeline_health | day | table | unique day |
| fct_data_quality | day | table | unique day |

- **Why DuckDB**: single-file, columnar, zero server, reads Parquet directly, free. Trade-off: **one writer at a time** → solved with the serving copy (D-006).
- **Why views for staging, tables for marts**: staging is cheap to recompute and always fresh; marts are what the dashboard reads, so they must be self-contained inside the copied file.

## 4. Flight phase classification (domain logic)
| Phase | Rule |
|---|---|
| ground | `on_ground = true` |
| climb | vertical rate > +2.5 m/s (~500 ft/min) |
| descent | vertical rate < −2.5 m/s |
| cruise | level and altitude ≥ 20,000 ft |
| level_low | level and altitude < 20,000 ft |
| unknown | no altitude |

Trade-off: snapshot-based, not trajectory-based: a single noisy vertical-rate reading can misclassify one point. See "what I'd improve" in README.

## 5. Airport flights (FEATURE-004)
- **Source**: `/flights/arrival` and `/flights/departure` per airport and UTC day (JSON objects, named fields).
- **Stored**: `raw/airport_flights/date=YYYY-MM-DD/<AIRPORT>_<direction>.parquet`, fixed `FLIGHT_SCHEMA` (16 columns: query_airport, direction, flight_date, ingested_at, icao24, first_seen, est_departure_airport, last_seen, est_arrival_airport, callsign, 4 distance columns, 2 candidate counts).
- **Size**: ~400-700 flights per airport per direction per day → ~2,000-3,000 rows/day for FRA+MUC, tens of KB.
- **Writer**: only `airport_flights_daily`. Re-running a day overwrites its 4 files (idempotent).

| Model | Grain | Key test |
|---|---|---|
| stg_airport_flights | airport × direction × flight | unique (airport, direction, icao24, departure_ts) |
| fct_airport_hourly | airport × UTC hour | unique (airport, movement_hour); hours add up to the day |
| fct_airport_daily | airport × day | unique (airport, flight_date); movements = arrivals + departures |
| fct_routes | departure × arrival airport | unique route; each physical flight counted once |
| airports (seed) | ICAO code | unique icao, unique iata |

- **Why count a flight once in routes**: a FRA→MUC flight is in FRA departures AND MUC arrivals. `(icao24, departure_ts)` identifies the physical flight.
- **Local time**: airport profiles use `Europe/Berlin` (people think of FRA's morning peak at 07:00 local), while all stored timestamps stay UTC.
- **Duration caveat**: `duration_min` = lastSeen − firstSeen, i.e. the time receivers saw the aircraft, not block time (FRA→MUC median 33 min live vs ~55 min scheduled). Fine for ranking routes, not for punctuality.
