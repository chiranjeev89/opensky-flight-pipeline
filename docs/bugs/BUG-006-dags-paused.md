# BUG-006 (test setup, not product): runs stuck in "queued"
Symptom: triggered runs stayed queued while the scheduler was running.
Root cause: DAGs were first registered by `airflow dags test` without `DAGS_ARE_PAUSED_AT_CREATION=false`, so they were paused. Paused DAGs don't run even when triggered manually.
Fix: `airflow dags unpause ...`. In Docker the env var is set from the start, and `start.ps1` also unpauses explicitly.
Lesson: if runs sit in queued, check the pause toggle first.
