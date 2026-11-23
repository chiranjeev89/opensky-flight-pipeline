# FEATURE-005: Live demo and continuous delivery
Goal: let anyone see the result without Docker or OpenSky keys, and ship versioned images on every release, at zero cost (D-016).
Design:
- `scripts/make_demo_db.py` builds `demo/serving_demo.duckdb` from the real `serving.duckdb`: all mart tables, only the latest snapshot of `fct_flight_phases` (map), `fct_phase_mix` added if missing. 3.4 MB, committed.
- `dashboard/app.py`: if `SERVING_DB_PATH` does not exist, open the demo file read-only and show a "frozen snapshot" banner.
- `dashboard/requirements.txt` + `.streamlit/config.toml` so Streamlit Community Cloud runs `dashboard/app.py` as is.
- `.github/workflows/release.yml`: on a `v*` tag, build both Dockerfiles and push `ghcr.io/<owner>/opensky-flight-pipeline-airflow|dashboard` with semver and `latest` tags.
Tests: Streamlit AppTest in live and demo mode (no exceptions); ruff; demo DB opened read-only.
Status: built 2026-11-23. Deploy and first release are user steps (README §7).

## Log
- 2026-11-23 Built; demo DB from the live DB (30 Oct - 23 Nov). Size 29 MB -> 3.4 MB after trimming the map table.
