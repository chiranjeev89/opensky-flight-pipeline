# BUG-009: One transponder glitch blocked every publish
Found: 2026-10-31, first real night of live data.
Symptom: `flight_transform.dbt_build` failed every hour from 2026-10-30 evening. Dashboard frozen on old data.
Log: `[ERROR] in test assert_speed_physically_possible ... Got 2 results, configured to fail if != 0`. PASS=17, ERROR=1, SKIP=15.
Root cause: real ADS-B data contains occasional transponder glitches (2 aircraft reported ground speed > 750 kt). The physical-limit tests ran on staging, so ONE bad aircraft stopped the whole publish. Synthetic CI data never had glitches, so CI could not catch this.
Fix (design change, D-012):
- `stg_state_vectors` adds `is_plausible` (speed, altitude, bbox limits). Raw data is still untouched.
- Marts (`fct_flight_phases`, `dim_aircraft`) use plausible rows only.
- `fct_data_quality.implausible_rows` counts the glitches every day (measured, not hidden).
- Physical-limit tests now check the marts (what the dashboard shows).
- New test `assert_no_systemic_glitches`: fails if > 20% of any snapshot is implausible -> real bugs (swapped fields, wrong units) still block publishing.
Verification: 2 injected glitches -> PASS=34, implausible_rows=2. Injected bad snapshot -> FAIL assert_no_systemic_glitches, 18 SKIP. Clean -> PASS=34. pytest 17 passed.
Lesson: a quality gate must tell "one noisy sensor" apart from "the whole feed is broken". Test on real data before trusting thresholds.
