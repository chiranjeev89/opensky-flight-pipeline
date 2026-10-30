# CONSTRAINTS

Hard rules for anyone changing this repo. **Stop and ask** before breaking any of them.

- **C-01** NEVER call the live OpenSky API from tests or CI. Use `responses` mocks or synthetic data.
- **C-02** NEVER change the bounding box or schedule without recomputing credits in DECISIONS.md D-002. `test_germany_box_stays_in_2_credit_tier` enforces it.
- **C-03** NEVER put secrets in code, Dockerfiles, compose files, dbt profiles or logs. Only `.env` (git-ignored) and GitHub/Azure secrets. The only key in code is Azurite's public dev key.
- **C-04** NEVER delete, skip or loosen a dbt test or pytest to make a build pass. Fix the data or the code, or write a BUG file explaining why the test changed.
- **C-05** ALWAYS keep raw (bronze) data immutable. No transformation before landing. Cleaning only in dbt.
- **C-06** ALWAYS keep the dashboard read-only (ro volume + `read_only=True`). It must never hold credentials.
- **C-07** ALWAYS keep DAG files thin: scheduling and wiring only. Logic goes in `src/flightpipe` with tests.
- **C-08** NO new dependency without a line in DEPENDENCIES.md (why, who maintains it, pinned range).
- **C-09** ALWAYS keep `ARROW_SCHEMA` backward compatible. Adding a nullable column is fine; renaming or retyping is a breaking change → FEATURE file + full rebuild plan.
- **C-10** Protected areas, pause and read: `storage.py` (data layout), `profiles.yml`, `docker-compose.yml`, `.github/workflows/`.
