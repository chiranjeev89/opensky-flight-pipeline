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
def query(sql: str) -> pd.DataFrame:
    with duckdb.connect(DB_PATH, read_only=True) as con:
        con.execute("SET TimeZone = 'UTC'")  # BUG-004: show UTC whatever the host timezone is
        return con.execute(sql).df()


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

st.subheader("Pipeline health (the 'measure' numbers)")
st.dataframe(health, width="stretch", hide_index=True)
st.subheader("Data quality")
dq = query("select * from fct_data_quality order by run_date")
st.dataframe(dq, width="stretch", hide_index=True)
