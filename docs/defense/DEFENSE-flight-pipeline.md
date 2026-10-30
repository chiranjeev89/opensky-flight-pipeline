# DEFENSE: Flight Operations Data Pipeline

> My whiteboard brief. Re-read before every release that changes the system.

**What it does (2 sentences):**
Every 10 minutes it pulls live positions of every aircraft over Germany from the OpenSky Network and stores them as Parquet in Azure Blob. Every hour dbt cleans and tests that data and builds traffic, flight-phase and pipeline-health tables, which a Streamlit dashboard shows.

**How it works (sketch the flow):**
Airflow → OpenSky (OAuth2) → parse array into named columns → Parquet → Blob `date=/hour=` → hourly: sync to local lake → dbt build (models + 25 tests) → only if all pass, copy to serving.duckdb → dashboard reads it read-only.

**Key decisions and why X over Y:**
- Germany box every 10 min: 2 credits × 144 = 288/day, 7% of my quota. Worldwide every 5 min would cost 1,152.
- ELT: raw is never modified, so a cleaning bug is fixed with a dbt rerun. A live API can't be re-fetched.
- DuckDB, not Snowflake: free, runs in CI, same dbt code. Its single-writer limitation is solved by publishing a separate serving copy.
- Deterministic blob names + overwrite, so retries never duplicate.

**Data structures and why:**
Columnar Parquet with a fixed schema, partitioned by date/hour. Analytics reads few columns over many rows, so a columnar format fits. The fixed schema stops all-null columns changing type. Marts each have one clear grain: hour, aircraft, day.

**How a malicious actor could abuse it:**
OpenSky could send garbage, which is caught by the schema plus physical-limit, bbox and accepted-value tests, and then publish is blocked. A leaked secret could drain credits or wipe the lake: .env is git-ignored, errors never print secrets and the dashboard holds no credentials. Gap: the connection string is a full account key; SAS or Managed Identity would be better. A dashboard visitor gets read-only access to fixed queries and has no way to spend credits.

**Where it fails and how we notice:**
- 429: the run is skipped and completeness drops.
- OpenSky down: retries, then lost snapshots (it is a live API).
- Format change: dbt tests fail, publish is blocked and "data as of" goes stale.
- First scaling limit: listing all blobs for sync, then full rescans in staging.
- Gap: no alerting outside the Airflow UI.

**What I would change with more time:**
Incremental dbt models, a sync window of the last N days, a failure webhook, gitleaks in CI, Managed Identity, trajectory-based phases using 1-min polling on a small box around FRA.

---
## Whiteboard drill (answer out loud, no notes; score ≥10/12)
1. What does it do, in 2 sentences?
2. Walk one snapshot from API to dashboard pixel.
3. Why Airflow and not cron? Why DuckDB and not Postgres?
4. Most important data structure, and why does it fit?
5. Worst thing an anonymous dashboard visitor can do?
6. What if my OpenSky secret leaks?
7. OpenSky down for an hour: what exactly happens?
8. First limit as data grows?
9. How do I know it broke before someone tells me?
10. How do I undo a bad dbt change?
11. What did I assume that I never verified? (ASSUMPTIONS.md)
12. What would I change with another week?
