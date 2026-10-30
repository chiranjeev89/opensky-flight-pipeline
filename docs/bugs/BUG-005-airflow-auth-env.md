# BUG-005: Wrong env var names for Airflow's simple auth manager
Symptom (found by checking `airflow config list --defaults`): compose used `AIRFLOW__SIMPLE_AUTH_MANAGER__USERS`, but the option lives in `[core]` as `simple_auth_manager_users`. Login admin/admin would not have worked (Airflow would have generated a random password instead).
Fix: `AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True` (no login, local only; THREAT T-07).
Verification: api-server UI returned HTTP 200 with that setting.
Lesson: verify config names against the installed version (`airflow config list --defaults`), not memory. Assumption A-02 was wrong.
