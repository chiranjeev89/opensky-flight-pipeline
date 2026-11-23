"""Which UTC days the daily airport job fetches (BUG-010).

OpenSky builds arrivals/departures in a nightly batch, and on some days that
batch is late or incomplete (8-12 Nov 2026: Frankfurt had 1 arrival instead of
~540). Re-fetching the last few completed days on every run lets late data fill
in by itself. Re-fetching is safe: each day overwrites its own files (D-005).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def days_to_fetch(interval_end: datetime, lookback_days: int = 3) -> list[date]:
    """Completed UTC days to (re)fetch, oldest first, ending with the day before interval_end.

    interval_end 2026-11-23 06:15 UTC, lookback 3 -> [20 Nov, 21 Nov, 22 Nov]
    """
    if lookback_days < 1:
        raise ValueError("lookback_days must be at least 1")
    last = (interval_end - timedelta(days=1)).date()
    return [last - timedelta(days=n) for n in range(lookback_days - 1, -1, -1)]
