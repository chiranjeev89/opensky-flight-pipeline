# PRD: Flight Operations Data Pipeline

Product requirements, written after v1.0 to record what the system is for and how success is judged. Numbers in "Status" are from the live run 30 Oct – 23 Nov 2026.

## 1. Problem
Airports and airlines need reliable, up-to-date traffic data. Public ADS-B data (OpenSky Network) is free but raw: unlabelled arrays, missing values, transponder glitches, late or incomplete batches, and a daily API budget. Nobody can build a report on it without a pipeline that collects it continuously and proves it is trustworthy.

## 2. Users and their questions

| User | Question | Where it is answered |
|---|---|---|
| **Airport / airline operations analyst** | How busy are Frankfurt and Munich per hour and per day? Which routes are busiest? | Dashboard "Airports" section; `fct_airport_hourly`, `fct_airport_daily`, `fct_routes` |
| **Network / traffic analyst** | How much traffic is over Germany each hour? What share is climbing, cruising, descending? Which countries' aircraft fly here? | Dashboard top section; `fct_traffic_hourly`, `fct_phase_mix`, `fct_country_mix` |
| **Data engineer operating the pipeline** | Did every run land? Is the data fresh and clean? What broke and why? | Airflow UI; dashboard "Pipeline health", "Data quality", "Data freshness"; docs/OPERATIONS.md |
| **Recruiter / reviewer** | Can this person build, test and run a real pipeline? | README, live demo, CI badge, docs/ |

## 3. Functional requirements

| ID | Requirement | Status |
|---|---|---|
| FR-1 | Collect all aircraft state vectors over a German bounding box every 10 minutes | ✅ 1,540 runs, 468,417 positions |
| FR-2 | Collect arrivals and departures for EDDF and EDDM for every completed day, and fill missed days automatically | ✅ 24/24 days, catch-up + 3-day re-fetch |
| FR-3 | Land raw data unchanged in Azure Blob Storage as partitioned Parquet | ✅ (Azure SDK on Azurite emulator) |
| FR-4 | Build cleaned, deduplicated staging and business marts with dbt | ✅ 3 staging, 10 marts, 1 seed |
| FR-5 | Flights per airport per hour and per day; busiest routes with each flight counted once | ✅ `fct_airport_hourly`, `fct_airport_daily`, `fct_routes` |
| FR-6 | Data-quality tests: not-null, unique keys, value ranges, freshness, volume/completeness | ✅ 49 dbt tests |
| FR-7 | Publish to the dashboard only data that passed every blocking test | ✅ atomic `serving.duckdb` swap |
| FR-8 | Dashboard: traffic by hour, airport activity, busiest routes, data freshness, pipeline health | ✅ |
| FR-9 | CI on every push; images published on every release | ✅ ci.yml, release.yml |
| FR-10 | One-click start and stop on Windows | ✅ start.bat / stop.bat |

## 4. Non-functional requirements

| ID | Requirement | Target | Status |
|---|---|---|---|
| NFR-1 Cost | No paid services | €0 | ✅ OpenSky free tier, Azurite, GitHub free tier |
| NFR-2 API budget | Stay well inside OpenSky's daily credits | < 25% of 4,000 /states credits | ✅ 288/day (7%); /flights ~360/day of its own 4,000 |
| NFR-3 Correctness | No duplicate rows after retries or re-runs | 0 | ✅ 0 duplicates removed in 468k rows |
| NFR-4 Trust | A single bad source row must not freeze the dashboard; a broken feed must | — | ✅ BUG-009 quarantine + systemic test |
| NFR-5 Freshness | Dashboard data at most ~1 hour old while running | ≤ 65 min | ✅ hourly publish |
| NFR-6 Recoverability | Survive restarts, power loss and gaps without manual data repair | — | ✅ tested by real events (README §4) |
| NFR-7 Security | No secrets in git; dashboard read-only with no credentials | — | ✅ THREAT.md |
| NFR-8 Portability | Same code on a laptop, in CI and on real Azure | config-only switch | ✅ |
| NFR-9 Explainability | Every decision and bug documented | — | ✅ 16 decisions (D-001..D-016), 10 bug reports |

## 5. Success metrics

| Metric | Target | Result |
|---|---|---|
| Schedule completeness on days the laptop was on all day | ≥ 95% | 100% (1, 2, 6 Nov) |
| Ingest failure rate | < 1% | 0.06% (1 of 1,541) |
| Blocking data tests passing on published builds | 100% | 100% (281 published builds) |
| Complete airport days | 100% | 100% after BUG-010 repair (24/24) |
| Rows quarantined as implausible | < 0.5% | 0.023% |

## 6. Out of scope (v1.0)
- Punctuality and delays (needs schedule data, not ADS-B).
- Official airport statistics (counts are flights seen by OpenSky's receivers).
- Real-time alerting to email/Slack (failures visible in Airflow and on the dashboard).
- Running 24/7 on cloud infrastructure (laptop-based; real Azure is a config change).
- Airports beyond FRA and MUC (configurable via `AIRPORTS`, credits scale linearly).

## 7. Risks
| Risk | Mitigation |
|---|---|
| OpenSky changes format or limits | Fixed schemas fail loudly; physical-limit and systemic tests block publishing |
| OpenSky publishes late/incomplete airport data | 3-day re-fetch + completeness flag (BUG-010) |
| Laptop-based collection has gaps | Completeness measured and reported honestly; airport data re-fetchable |
