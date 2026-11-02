# FEATURE-004: Frankfurt & Munich traffic and busiest routes
Goal: answer the airport questions from the project brief: flights per airport per hour, trustworthy daily airport tables, busiest routes, and data freshness for airport data.
Why a second data source: `/states/all` snapshots say where aircraft ARE, not where they came from or go to. OpenSky's `/flights/arrival` and `/flights/departure` return, per airport, each flight with estimated departure and arrival airport and times.
Scope: EDDF (Frankfurt) and EDDM (Munich), configurable via `AIRPORTS`. Out of scope: punctuality/delays (needs schedule data).
Design:
- `OpenSkyClient.fetch_airport_flights()` reuses the shared retry/credit policy (`_get`); 404 = no flights.
- DAG `airport_flights_daily`, 06:15 UTC, fetches the last COMPLETE UTC day (nightly batch at OpenSky), `catchup=True` so missed days fill in.
- Raw: `raw/airport_flights/date=YYYY-MM-DD/<AIRPORT>_<direction>.parquet`, fixed `FLIGHT_SCHEMA`.
- dbt: `stg_airport_flights` (clean, dedupe, plausibility flag, local time) → `fct_airport_hourly`, `fct_airport_daily`, `fct_routes` (+ seed `airports.csv` for readable names).
- Bootstrap: a 0-row local file lets dbt build before the first airport file exists.
- Dashboard: airport picker, KPIs, typical-day profile by local hour, busiest routes, movements per day, data-freshness table.
Tests: 11 new unit tests; dbt: unique keys on every new table, accepted values, airport in scope, daily = arrivals + departures = sum of hours, systemic-error test, freshness warning, seed uniqueness.
Status: built and verified on synthetic data + end-to-end against Azurite and a fake OpenSky API. Live run pending on the laptop.
Open questions: A-12 (credit cost of /flights), A-13 (batch timing), A-14 (share of unknown origins in real data).

## Log
- 2026-11-02 Built. Verified: pytest 28 passed; dbt 58/58; DAG run against fakes fetched 2026-11-01 for both airports (one 404 → empty file); upgrade path without airport files: ERROR without bootstrap, 58/58 with it.
- 2026-11-02 08:09 UTC first live run on the laptop (catchup 30 Oct - 1 Nov), all green after the image rebuild:
  30 Oct FRA 586 arr / 596 dep, MUC 443 / 444; 31 Oct FRA 556 / 542, MUC 395 / 392; 1 Nov FRA 577 / 506, MUC 429 / 389.
  One attempt failed with ImportError because it ran on the old image before start.bat rebuilt it; the automatic retry succeeded (DAG files are mounted live, src/ is baked into the image).

