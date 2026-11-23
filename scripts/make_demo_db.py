"""Build the small public demo database from a live serving.duckdb.

Copies every mart table, but only the LATEST snapshot of fct_flight_phases
(the map and "data as of" need just that; the phase chart uses fct_phase_mix).
Staging views are not copied: they point at raw files that the demo does not have.

Usage: python scripts/make_demo_db.py --src data/lake/serving.duckdb --out demo/serving_demo.duckdb
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/lake/serving.duckdb")
    ap.add_argument("--out", default="demo/serving_demo.duckdb")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    src = Path(args.src).resolve().as_posix()

    con = duckdb.connect(str(out))
    con.execute(f"attach '{src}' as live (read_only)")
    tables = [
        r[0]
        for r in con.execute(
            """select table_name from duckdb_tables()
               where database_name = 'live' and schema_name = 'main'"""
        ).fetchall()
    ]
    for t in tables:
        # Table names can't be bound as parameters; they come from our own catalog,
        # and are checked to be plain identifiers before use.
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", t):
            raise ValueError(f"unexpected table name {t!r}")
        if t == "fct_flight_phases":
            con.execute(
                f"""create table {t} as select * from live.main.{t}
                    where snapshot_ts = (select max(snapshot_ts) from live.main.{t})"""  # noqa: S608
            )
        else:
            con.execute(f"create table {t} as select * from live.main.{t}")  # noqa: S608
    # Databases published before 2026-11-23 lack fct_phase_mix and the capped completeness;
    # apply the same logic as the current dbt models so the demo matches the README.
    if "fct_phase_mix" not in tables:
        con.execute(
            """create table fct_phase_mix as
               select flight_phase, count(*) as observations,
                      round(100.0 * count(*) / sum(count(*)) over (), 1) as pct_of_observations
               from live.main.fct_flight_phases group by 1"""
        )
    con.execute("update fct_pipeline_health set completeness_pct = least(completeness_pct, 100.0)")
    con.execute("detach live")
    con.execute("checkpoint")
    con.close()
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB) with {len(tables)} tables")


if __name__ == "__main__":
    main()
