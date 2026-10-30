# BUG-008: airflow-init failed: "No module named 'airflow'"
Symptom (first Windows run, 2026-10-30): `service "airflow-init" didn't complete successfully: exit 1`. Container log:
`File "/home/airflow/.local/bin/airflow" ... ModuleNotFoundError: No module named 'airflow'`.
Root cause: airflow-init ran as root (user 0:0) to chown the lake volume, then called `airflow db migrate`. In the official image, Airflow is installed into the *airflow user's* site-packages (/home/airflow/.local); root's Python does not look there.
Fix: split into `lake-init` (root, only chown) and `airflow-init` (default airflow user, `db migrate` through the image entrypoint). Dashboard now waits for lake-init.
Verification: pending re-run on Windows.
Lesson: in the Airflow image, only do file-permission work as root; run every `airflow` command as the airflow user. Tests that ran Airflow outside Docker could not catch this (assumption A-01 was only partly verified).
