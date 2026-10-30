# ROLLBACK

## Before any risky change
1. `git tag last-good-$(date +%Y%m%d)` on the current main.
2. Note the tag in HANDOVER.md "In progress".

## Code change broke the pipeline
```
git revert <commit>            # preferred: keeps history
# or redeploy the tag
git checkout last-good-YYYYMMDD && docker compose up -d --build
```
Re-check: TESTING.md rows 1-4, then Airflow both DAGs green.

## dbt model change produced wrong numbers
Raw data is untouched (D-004), so: revert the model, `dbt build`, publish. Dashboard already kept the last good `serving.duckdb` if tests failed.
Emergency switch-off without deploy: pause `flight_transform` in the Airflow UI → dashboard freezes on the last good data.

## Bad data landed in Blob
Delete the affected `date=`/`hour=` prefix (or single `states_<t>.parquet`), delete the same files in `/opt/lake/raw`, rerun `flight_transform`.
On real Azure: enable soft delete + versioning so deletes are reversible.

## Schema change (ARROW_SCHEMA)
Only additive nullable columns (C-09). `union_by_name = true` in sources means old files simply get NULL. Rollback = revert code; old and new files both remain readable.

## Full reset (local only)
`docker compose down -v` deletes Postgres, Azurite and the lake volume. Never on real Azure.
