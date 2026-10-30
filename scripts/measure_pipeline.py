"""Print the README 'Results' numbers straight from the serving database.

WHY a script: results in the README must be reproducible, not typed by hand.
Run it after the pipeline has collected data, paste the output into
README.md -> Results, and commit with the date.

Usage: python scripts/measure_pipeline.py --db data/lake/serving.duckdb
"""

from __future__ import annotations

import argparse

import duckdb


def q1(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).fetchone()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/lake/serving.duckdb")
    args = ap.parse_args()
    con = duckdb.connect(args.db, read_only=True)
    con.execute("SET TimeZone = 'UTC'")

    days, runs, rows, mb, avg_lat, p95_lat = q1(
        con,
        """select count(*), sum(runs_landed), sum(total_rows), sum(total_mb),
                  round(avg(avg_api_latency_ms)), max(p95_api_latency_ms)
           from fct_pipeline_health""",
    )
    completeness = q1(
        con,
        # exclude first and last (partial) day when there are 3+ days
        """select round(avg(completeness_pct),1) from (
             select *, row_number() over (order by run_date) rn,
                    count(*) over () n from fct_pipeline_health)
           where n < 3 or (rn > 1 and rn < n)""",
    )[0]
    aircraft = q1(con, "select count(*) from dim_aircraft")[0]
    peak = q1(
        con,
        """select snapshot_hour, airborne_aircraft from fct_traffic_hourly
           order by airborne_aircraft desc limit 1""",
    )
    dq = q1(
        con,
        """select round(avg(pct_missing_position),2), round(avg(pct_missing_callsign),2),
                  sum(duplicates_removed) from fct_data_quality""",
    )
    phases = con.execute(
        """select flight_phase, round(100.0*count(*)/sum(count(*)) over (),1)
           from fct_flight_phases group by 1 order by 2 desc"""
    ).fetchall()

    print("| Metric | Value |\n|---|---|")
    print(f"| Days collected | {days} |")
    print(f"| Ingest runs landed | {runs:,} |")
    print(f"| Schedule completeness (full days) | {completeness}% |")
    print(f"| State vectors stored | {rows:,} |")
    print(f"| Storage used | {mb} MB Parquet |")
    print(f"| API latency avg / p95 | {avg_lat:.0f} ms / {p95_lat:.0f} ms |")
    print(f"| Unique aircraft seen | {aircraft:,} |")
    print(f"| Peak airborne aircraft in one hour | {peak[1]} at {peak[0]:%Y-%m-%d %H:00} UTC |")
    print(f"| Rows missing position | {dq[0]}% |")
    print(f"| Rows missing callsign | {dq[1]}% |")
    print(f"| Duplicate rows removed by staging | {dq[2]:,} |")
    print("| Flight phase mix | " + ", ".join(f"{p} {v}%" for p, v in phases) + " |")


if __name__ == "__main__":
    main()
