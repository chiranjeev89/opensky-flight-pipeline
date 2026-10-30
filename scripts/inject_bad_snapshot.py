"""Negative test: write one physically impossible snapshot, prove dbt blocks it.

Usage:
    python scripts/inject_bad_snapshot.py --out data/lake      # inject
    make dbt                                                   # expect 3 FAIL, marts SKIP
    python scripts/inject_bad_snapshot.py --out data/lake --remove

The row has altitude 30,000 m (~98,000 ft), speed 900 m/s and lat/lon swapped
(the classic index bug). Each one must trip a different dbt test.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flightpipe.storage import blob_path_for  # noqa: E402
from flightpipe.transform import parse_states, to_parquet_bytes  # noqa: E402

T = 1700000000  # 2023-11-14, far from real data so it is easy to remove


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/lake")
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()
    target = Path(args.out) / blob_path_for(T)
    if args.remove:
        shutil.rmtree(target.parents[1], ignore_errors=True)
        print(f"Removed {target.parents[1]}")
        return
    row = [
        "bad001",
        "BAD1",
        "Germany",
        T,
        T,
        50.1,
        8.6,
        30000.0,
        False,
        900.0,
        90.0,
        0.0,
        None,
        30000.0,
        "7700",
        False,
        0,
    ]  # lon=50.1, lat=8.6: swapped on purpose
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(to_parquet_bytes(parse_states({"time": T, "states": [row]})))
    print(f"Injected {target}")


if __name__ == "__main__":
    main()
