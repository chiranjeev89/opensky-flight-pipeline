# BUG-010: Some airport days were almost empty, and the pipeline accepted them
Found: 2026-11-23, reviewing three weeks of live airport runs.
Symptom: most days had ~1,000-1,100 Frankfurt and ~750-800 Munich movements, but four did not:

| Day | FRA arrivals / departures | MUC arrivals / departures |
|---|---|---|
| 8 Nov | 1 / 61 | 8 / 37 |
| 10 Nov | 1 / 49 | 0 / 20 |
| 11 Nov | 0 / 53 | 1 / 21 |
| 12 Nov | 112 / 96 | 38 / 58 |

Every run was green, so nothing looked wrong in Airflow. Averages and the "typical day" chart were pulled down without warning.
Root cause: OpenSky's nightly flight batch was late or incomplete on those days. Not a timing bug on our side: 11 Nov was fetched at 12:18 UTC the next day and was still nearly empty. The pipeline fetched each day exactly once and had no check for "suspiciously small day".
Fix (D-015):
1. Self-healing: every daily run fetches yesterday AND re-fetches the 2 days before it (`AIRPORT_LOOKBACK_DAYS=3`). Same file names -> overwrite, no duplicates. Cost ~360 of 4,000 daily /flights credits.
2. Detection: `fct_airport_daily.is_complete_day` is false when arrivals OR departures are below half of that airport's median day (`min_complete_day_share`). Checked per direction because a day can lose only one side.
3. Visibility without blocking: dbt test `assert_airport_days_complete` WARNS (live publishing continues); the dashboard shows a warning listing the days and leaves them out of averages and the hourly profile; the results script reports how many days were excluded.
4. Repair of the old days: clear their `airport_flights_daily` runs in Airflow (docs/OPERATIONS.md).
Verification: synthetic lake with one day cut to 2 arrivals -> flagged, WARN=1, PASS=59, publish continues; dashboard warning shown; old serving DB without the new columns still renders. DAG run against Azurite + fake OpenSky: 12 calls for 20/21/22 Nov, success. pytest 31 passed. Real repair: pending (user clears 4 runs).
Lesson: "the task succeeded" is not "the data is complete". Volume checks against a baseline belong next to schema and value checks.

## Log
- 2026-11-23 Live repair: cleared the 9 Nov and 13 Nov runs (each re-fetches 3 days). All 24 airport days (30 Oct - 22 Nov) now complete: 8 Nov FRA 1/61 -> 545/556, 10 Nov 1/49 -> 514/503, 11 Nov 0/53 -> 528/534, 12 Nov 112/96 -> 545/541.
- Bonus finding: days that had looked fine were also partly late. 6 Nov FRA departures 481 -> 560 and 7 Nov 444 -> 518 after re-fetch. Late data is not only "empty days", which is why the rolling 3-day re-fetch matters more than the 50% check alone.
