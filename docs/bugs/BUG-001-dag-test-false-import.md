# BUG-001: DAG import test errored instead of skipping without Airflow
Symptom: `pytest` → `ModuleNotFoundError: airflow.models` although test uses `pytest.importorskip("airflow")`.
Repro: run `pytest` in an env without Airflow from the repo root.
Root cause: the repo has a folder `airflow/` (holds `dags/`). With the repo root on `sys.path`, Python imports it as a **namespace package**, so `importorskip("airflow")` succeeded and the next import failed.
Fix: `pytest.importorskip("airflow.models")`, with a WHY comment.
Verification: `16 passed, 1 skipped`. The real DAG import check runs inside the Airflow image in CI (`docker-build` job).
Lesson: folder names can shadow packages. Alternative would be renaming `airflow/` → `orchestration/`.

## Log
- 2026-10-28 found and fixed during first test run.
