# FAILURE

Dependency by dependency: slow, down, wrong, empty. Plus the first limits.

| ID | Dependency / condition | What happens | How I notice | Recovery |
|---|---|---|---|---|
| F-01 | OpenSky **credits exhausted** (HTTP 429) | `CreditsExhausted` → task **skipped** (not failed, not retried) | Skipped tasks in Airflow grid; `completeness_pct` drops; `min_credits_remaining` in fct_pipeline_health | Credits reset daily. Lower frequency or box size |
| F-02 | OpenSky **down / slow / 5xx** | 3 attempts, backoff 2/4/8 s, 30 s timeout each; then Airflow retries 2× after 2 min; `execution_timeout` 5 min | Failed task; completeness drop; `p95_api_latency_ms` rise | Automatic. Missed snapshots are lost (live API, ≤1 h history) |
| F-03 | **Token expired / revoked** (401) | Refresh once, retry; still 401 → fail | Failed task, log "Token request failed with HTTP 4xx" | Rotate API client in OpenSky account, update .env |
| F-04 | **OpenSky changes the array format** | Extra fields ignored; reordered fields → wrong columns → dbt physical-limit/bbox tests fail → **publish blocked** | `flight_transform` fails at dbt_build; dashboard shows "data as of" getting old | Fix `STATE_FIELDS`, rebuild (raw data intact, D-004) |
| F-05 | **DuckDB lock** (two writers) | Prevented by design: `max_active_runs=1`, dashboard reads serving copy | dbt error "Could not set lock" | Wait / rerun |
| F-06 | **Azure Blob / Azurite down** | Upload fails → Airflow retry; sync fails → no new data, dashboard keeps last good copy | Failed task | Automatic when storage returns |
| F-07 | **Empty sky** (`states: null`, e.g. night or tiny box) | Handled: 0-row Parquet with correct schema | `row_count = 0` in runs | None needed |
| F-08 | **A dbt test fails** | publish never runs; dashboard keeps last good data | Failed dbt_build, `dbt build` log names the test | Investigate → BUG file |
| F-09 | **Stale data** (> 3 h) | `assert_data_is_fresh` **warns** | Warning in dbt log; dashboard "Data as of" | Check ingest DAG |
| F-10 | **Disk full on lake volume** | Sync/dbt fail | Failed task | Prune old partitions (Blob keeps the original) |

| F-11 | **Airport batch late / empty** (OpenSky nightly job) | 404 → empty day; low counts are kept as-is | `fct_airport_daily` shows an unusually low day; freshness warning after 3 days | Re-run that day's DAG run (Clear) → file is overwritten |
| F-12 | **No airport file yet** (fresh install/upgrade) | 0-row bootstrap file keeps dbt green (D-014) | Dashboard: "No airport data yet" | Automatic at next 06:15 UTC run |

## First limits I expect to hit
1. **Sync time**: `list_blobs` walks every file. At 144 files/day → ~52k files/year; listing gets slow after a few months. Fix: sync only last N date partitions.
2. **dbt full rebuild**: staging is a view over *all* Parquet → each run rescans everything. Fix: incremental mart models (by snapshot_hour).
3. **Credits**: only if I widen the box or poll faster (see D-002 maths).
4. **DuckDB single-writer**: fine until more than one pipeline writes.

## Gap: alerting
No email/Slack alert yet; failures are only visible in Airflow UI. → Airflow `on_failure_callback` to a webhook (README "improve").
