"""Flight Operations dashboard (Streamlit).

Reads ONLY serving.duckdb in read-only mode: the copy published after dbt
tests pass. It never touches the warehouse dbt is writing to (D-006), and it
never calls OpenSky or Azure, so a dashboard visitor cannot spend API
credits or reach storage (docs/THREAT.md T-04).
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = os.getenv("SERVING_DB_PATH", "/opt/lake/serving.duckdb")

st.set_page_config(page_title="Flight Ops over Germany", layout="wide")


@st.cache_data(ttl=300)  # 5 min cache: data only changes hourly, protects the DB from refresh spam
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    # Values always go in as bound parameters (?), never pasted into the SQL text (THREAT T-04).
    with duckdb.connect(DB_PATH, read_only=True) as con:
        con.execute("SET TimeZone = 'UTC'")  # BUG-004: show UTC whatever the host timezone is
        return con.execute(sql, list(params)).df()


st.title("✈️ Flight Operations over Germany")
st.caption("Live ADS-B data from the OpenSky Network · Airflow → Azure Blob → dbt → DuckDB")

if not Path(DB_PATH).exists():
    st.warning("No data published yet. The first dbt run publishes serving.duckdb at :05 past the hour.")
    st.stop()

health = query("select * from fct_pipeline_health order by run_date")
traffic = query("select * from fct_traffic_hourly order by snapshot_hour")
newest = query("select max(snapshot_ts) as newest from fct_flight_phases")["newest"].iloc[0]

c1, c2, c3, c4 = st.columns(4)
n_aircraft = int(query("select count(*) as n from dim_aircraft")["n"].iloc[0])
c1.metric("Unique aircraft (all time)", f"{n_aircraft:,}")
c2.metric("Airborne, latest hour", int(traffic["airborne_aircraft"].iloc[-1]) if len(traffic) else 0)
p95 = f"{health['p95_api_latency_ms'].iloc[-1]:.0f} ms" if len(health) else "–"
c3.metric("p95 API latency (today)", p95)
c4.metric("Data as of (UTC)", f"{pd.Timestamp(newest):%Y-%m-%d %H:%M}")

st.subheader("Airborne aircraft per hour")
st.line_chart(traffic.set_index("snapshot_hour")[["airborne_aircraft", "unique_aircraft"]])

left, right = st.columns(2)
with left:
    st.subheader("Flight phase mix")
    phases = query(
        "select flight_phase, count(*) as observations from fct_flight_phases group by 1 order by 2 desc"
    )
    st.bar_chart(phases.set_index("flight_phase"))
with right:
    st.subheader("Top registration countries")
    st.bar_chart(
        query(
            "select origin_country, unique_aircraft from fct_country_mix order by 2 desc limit 10"
        ).set_index("origin_country")
    )

st.subheader("Latest snapshot positions")
latest = query(
    # Reads a mart TABLE, not the staging view: views point at raw Parquet paths,
    # tables are self-contained inside serving.duckdb.
    """select latitude as lat, longitude as lon
       from fct_flight_phases
       where snapshot_ts = (select max(snapshot_ts) from fct_flight_phases)"""
)
st.map(latest, size=800)

# ---------------------------------------------------------------------------
# FEATURE-004: Frankfurt & Munich - flights per airport per hour, busiest routes
# ---------------------------------------------------------------------------
AIRPORT_NAMES = {"EDDF": "Frankfurt (FRA)", "EDDM": "Munich (MUC)"}

st.header("Airports: Frankfurt & Munich")
try:
    daily = query("select * from fct_airport_daily order by airport, flight_date")
except duckdb.CatalogException:
    daily = pd.DataFrame()  # serving DB published before the airport models existed
if not daily.empty and "is_complete_day" not in daily.columns:
    daily["is_complete_day"] = True  # serving DB published before BUG-010

if daily.empty:
    st.info(
        "No airport data yet. The airport_flights_daily DAG fetches yesterday's arrivals and "
        "departures every morning at 06:15 UTC (OpenSky publishes them in a nightly batch)."
    )
else:
    airports = [a for a in AIRPORT_NAMES if a in set(daily["airport"])] or sorted(set(daily["airport"]))
    choice = st.radio(
        "Airport", airports, format_func=lambda a: AIRPORT_NAMES.get(a, a), horizontal=True, key="airport"
    )
    d = daily[daily["airport"] == choice]
    complete = d[d["is_complete_day"]]  # BUG-010: incomplete days never feed averages
    last = complete.iloc[-1] if not complete.empty else d.iloc[-1]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(f"Movements on {last['flight_date']:%d %b}", f"{int(last['movements']):,}")
    k2.metric("Arrivals / departures", f"{int(last['arrivals'])} / {int(last['departures'])}")
    k3.metric(
        f"Avg movements per day ({len(complete)} complete days)", f"{complete['movements'].mean():,.0f}"
    )
    k4.metric("Unknown origin (arrivals)", f"{last['pct_unknown_origin']:.1f}%")
    bad = d[~d["is_complete_day"]]
    if not bad.empty:
        days = ", ".join(f"{x:%d %b}" for x in bad["flight_date"])
        st.warning(
            f"Incomplete days in OpenSky's airport data (left out of averages): {days}. "
            "The daily job re-fetches the last 3 days; older days can be repaired by clearing their "
            "airport_flights_daily run in Airflow."
        )

    a1, a2 = st.columns(2)
    with a1:
        st.subheader("Typical day: movements by local hour")
        profile_sql = """select hour_of_day_local as hour,
                   round(avg(arrivals), 1) as arrivals, round(avg(departures), 1) as departures
            from fct_airport_hourly where airport = ? {extra}
            group by 1 order by 1"""
        try:
            prof = query(profile_sql.format(extra="and is_complete_day"), (choice,))
        except duckdb.BinderException:  # serving DB published before BUG-010
            prof = query(profile_sql.format(extra=""), (choice,))
        st.bar_chart(prof.set_index("hour"), stack=False)
        st.caption("Average over complete days only. Hours in Europe/Berlin time.")
    with a2:
        st.subheader("Busiest routes")
        routes = query(
            """select route, route_cities as cities, flights, median_duration_min as median_min
                from fct_routes
                where departure_airport = ? or arrival_airport = ?
                order by flights desc limit 15""",
            (choice, choice),
        )
        st.dataframe(routes, width="stretch", hide_index=True)
        st.caption("median_min = time OpenSky's receivers saw the flight, not gate-to-gate block time.")

    st.subheader(f"Movements per day: {AIRPORT_NAMES.get(choice, choice)}")
    per_day = d.assign(
        day=d["flight_date"].astype(str),  # text labels -> full-width bars
        status=d["is_complete_day"].map({True: "complete", False: "incomplete (OpenSky gap)"}),
    )
    st.bar_chart(per_day, x="day", y="movements", color="status")

st.subheader("Data freshness")
fresh = [
    {"dataset": "Live positions (every 10 min)", "newest": f"{pd.Timestamp(newest):%Y-%m-%d %H:%M} UTC"},
    {
        "dataset": "Airport arrivals/departures (daily)",
        "newest": (
            f"{daily.loc[daily['is_complete_day'], 'flight_date'].max():%Y-%m-%d} (newest complete day)"
            if not daily.empty and daily["is_complete_day"].any()
            else "none yet"
        ),
    },
]
st.dataframe(pd.DataFrame(fresh), width="stretch", hide_index=True)

st.subheader("Pipeline health (the 'measure' numbers)")
st.dataframe(health, width="stretch", hide_index=True)
st.subheader("Data quality")
dq = query("select * from fct_data_quality order by run_date")
st.dataframe(dq, width="stretch", hide_index=True)
