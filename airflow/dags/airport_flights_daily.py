"""DAG 3/3: airport_flights_daily - arrivals + departures for FRA and MUC (last 3 complete days).

Flow (docs/FLOW.md path 5, FEATURE-004):
    for each of the last 3 completed UTC days, each airport in AIRPORTS (default
    EDDF, EDDM) and each direction:
        /flights/arrival|departure?airport=..&begin=<day 00:00>&end=<day 23:59:59>
        -> Parquet -> raw/airport_flights/date=<day>/<AIRPORT>_<direction>.parquet

WHY daily, for completed days (D-013, BUG-010): each run fetches yesterday and
re-fetches the 2 days before it (AIRPORT_LOOKBACK_DAYS=3), because OpenSky's
batch is sometimes late or incomplete; the re-fetch overwrites the same files.
OpenSky builds flight records (which airport a flight left from / landed at) in
a nightly batch, so today is never asked for. 06:15 UTC gives the batch time.

WHY catchup=True: unlike live state vectors, flight history CAN be fetched
later, so missed days (laptop off) are filled in automatically, and the first
start fills in every day since start_date.

Credits: 3 days x 2 airports x 2 directions = 12 calls/day (~30 credits each,
~360/day) from the separate /flights bucket (it does not touch the /states budget).
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
        from flightpipe.dates import days_to_fetch
        from flightpipe.opensky_client import CreditsExhausted, OpenSkyClient
        from flightpipe.storage import airport_flights_path, get_container, upload_snapshot
        from flightpipe.transform import flights_to_parquet

        ctx = get_current_context()
        settings = get_settings()
        # The run at 2026-11-23 06:15 fetches 22 Nov (new) and re-fetches 20-21 Nov
        # in case OpenSky's nightly batch was late (BUG-010). Overwrite = no duplicates.
        days = days_to_fetch(ctx["data_interval_end"], settings.airport_lookback_days)

        client = OpenSkyClient(settings)
        container = get_container(settings.azure_conn_str, settings.azure_container)
        started = datetime.now(UTC)

        counts: dict[str, int] = {}
        for day in days:
            begin = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())
            end = begin + 86400 - 1
            for airport in settings.airports:
                for direction in ("arrival", "departure"):
                    try:
                        flights = client.fetch_airport_flights(airport, direction, begin, end)
                    except CreditsExhausted as exc:
                        raise AirflowSkipException(str(exc)) from exc
                    data = flights_to_parquet(flights, airport, direction, day, ingested_at=started)
                    path = airport_flights_path(airport, direction, day)
                    upload_snapshot(container, begin, data, path=path)
                    counts[f"{day:%m-%d}_{airport}_{direction}"] = len(flights)
        return counts

    fetch_and_land_day()


airport_flights_daily()
