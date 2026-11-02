"""DAG 3/3: airport_flights_daily - yesterday's arrivals + departures for FRA and MUC.

Flow (docs/FLOW.md path 5, FEATURE-004):
    for each airport in AIRPORTS (default EDDF, EDDM) and each direction:
        /flights/arrival|departure?airport=..&begin=<day 00:00>&end=<day 23:59:59>
        -> Parquet -> raw/airport_flights/date=<day>/<AIRPORT>_<direction>.parquet

WHY daily, for YESTERDAY (D-013): OpenSky builds flight records (which airport a
flight left from / landed at) in a nightly batch. Asking for today returns an
incomplete day. 06:15 UTC gives the batch time to finish.

WHY catchup=True: unlike live state vectors, flight history CAN be fetched
later, so missed days (laptop off) are filled in automatically, and the first
start fills in every day since start_date.

Credits: 2 airports x 2 directions = 4 calls/day, from the separate /flights
credit bucket (it does not touch the /states budget).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from airflow.exceptions import AirflowSkipException
from airflow.sdk import dag, get_current_context, task


@dag(
    dag_id="airport_flights_daily",
    schedule="15 6 * * *",
    start_date=datetime(2026, 10, 31, 6, 15, tzinfo=UTC),  # first run fetches 30 Oct = first live day
    catchup=True,
    max_active_runs=1,
    default_args={
        "owner": "chiranjeev",
        "retries": 3,
        "retry_delay": timedelta(minutes=30),  # batch may be late: retry later, not immediately
        "execution_timeout": timedelta(minutes=10),
    },
    tags=["opensky", "ingest", "airports"],
)
def airport_flights_daily():
    @task
    def fetch_and_land_day() -> dict:
        from flightpipe.config import get_settings
        from flightpipe.opensky_client import CreditsExhausted, OpenSkyClient
        from flightpipe.storage import airport_flights_path, get_container, upload_snapshot
        from flightpipe.transform import flights_to_parquet

        ctx = get_current_context()
        # The run at 2026-11-02 06:15 fetches 2026-11-01 (the last complete UTC day).
        day = (ctx["data_interval_end"] - timedelta(days=1)).date()
        begin = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())
        end = begin + 86400 - 1

        settings = get_settings()
        client = OpenSkyClient(settings)
        container = get_container(settings.azure_conn_str, settings.azure_container)
        started = datetime.now(UTC)

        counts: dict[str, int] = {}
        for airport in settings.airports:
            for direction in ("arrival", "departure"):
                try:
                    flights = client.fetch_airport_flights(airport, direction, begin, end)
                except CreditsExhausted as exc:
                    raise AirflowSkipException(str(exc)) from exc
                data = flights_to_parquet(flights, airport, direction, day, ingested_at=started)
                upload_snapshot(container, begin, data, path=airport_flights_path(airport, direction, day))
                counts[f"{airport}_{direction}"] = len(flights)
        return {"day": day.isoformat(), **counts}

    fetch_and_land_day()


airport_flights_daily()
