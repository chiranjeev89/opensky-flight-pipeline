"""Generate synthetic OpenSky-shaped snapshots into a local lake folder.

Used by: GitHub Actions (so dbt can run without credentials or network) and
by anyone who wants to see the dashboard before the live pipeline has run.

It goes through the REAL code path (parse_states -> to_parquet_bytes ->
blob_path_for), so CI exercises the same serializer production uses.
Synthetic data is clearly marked: every callsign starts with "SIM".

Usage: python scripts/generate_sample_data.py --out data/lake --hours 24
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flightpipe.storage import blob_path_for, run_meta_path_for  # noqa: E402
from flightpipe.transform import parse_states, run_meta_to_parquet, to_parquet_bytes  # noqa: E402

COUNTRIES = ["Germany", "United Kingdom", "France", "Netherlands", "Ireland", "Poland", "Switzerland"]


def make_fleet(n: int, rng: random.Random) -> list[dict]:
    return [
        {
            "icao24": f"{rng.randrange(0x300000, 0x4FFFFF):06x}",
            "callsign": f"SIM{rng.randrange(100, 9999):<5}",  # padded like the real API
            "country": rng.choices(COUNTRIES, weights=[45, 12, 10, 9, 8, 8, 8])[0],
            "lat": rng.uniform(47.5, 54.8),
            "lon": rng.uniform(6.0, 14.8),
            "alt": rng.choice([0, rng.uniform(500, 3000), rng.uniform(9000, 12000)]),
        }
        for _ in range(n)
    ]


def snapshot(fleet: list[dict], t: int, rng: random.Random, hour: int) -> dict:
    # Fewer aircraft at night (00-05 UTC), like real European traffic.
    active_share = 0.25 if hour < 5 else 0.9
    states = []
    for ac in fleet:
        if rng.random() > active_share:
            continue
        on_ground = ac["alt"] == 0
        vr = 0.0 if on_ground else rng.choice([0.0, 0.0, 0.3, -0.4, 8.0, -6.5])
        ac["lat"] = min(54.9, max(47.4, ac["lat"] + rng.uniform(-0.15, 0.15)))
        ac["lon"] = min(14.9, max(5.95, ac["lon"] + rng.uniform(-0.2, 0.2)))
        states.append(
            [
                ac["icao24"],
                ac["callsign"],
                ac["country"],
                t - rng.randint(0, 5),
                t - rng.randint(0, 3),
                None if rng.random() < 0.02 else ac["lon"],  # ~2% missing position, like real feed
                ac["lat"],
                None if on_ground else ac["alt"],
                on_ground,
                rng.uniform(0, 15) if on_ground else rng.uniform(120, 260),
                rng.uniform(0, 360),
                vr,
                None,
                None if on_ground else ac["alt"] + rng.uniform(-60, 60),
                f"{rng.randint(1000, 7777)}",
                False,
                0,
            ]
        )
    return {"time": t, "states": states}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/lake")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--fleet", type=int, default=400)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    fleet = make_fleet(args.fleet, rng)
    end = datetime.now(UTC).replace(second=0, microsecond=0)
    start = end - timedelta(hours=args.hours)
    out = Path(args.out)

    t = start
    files = 0
    while t <= end:
        ts = int(t.timestamp())
        raw = snapshot(fleet, ts, rng, t.hour)
        records = parse_states(raw, ingested_at=t)
        data = to_parquet_bytes(records)
        p = out / blob_path_for(ts)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        meta = {
            "snapshot_time": ts,
            "run_started_at": t,
            "api_latency_ms": round(rng.lognormvariate(6.2, 0.35), 1),
            "row_count": len(records),
            "parquet_bytes": len(data),
            "credits_remaining": None,
            "status": "success",
        }
        m = out / run_meta_path_for(ts)
        m.parent.mkdir(parents=True, exist_ok=True)
        m.write_bytes(run_meta_to_parquet(meta))
        files += 1
        t += timedelta(minutes=10)
    print(f"Wrote {files} synthetic snapshots to {out}")


if __name__ == "__main__":
    main()
