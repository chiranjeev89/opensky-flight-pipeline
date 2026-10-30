# FEATURE-003: Dashboard, Docker, CI
Goal: one command to run everything; every push proven by CI.
Steps:
- [x] Streamlit reading serving.duckdb read-only
- [x] docker-compose: postgres, azurite, airflow (init, api-server, scheduler, dag-processor), dashboard
- [x] GitHub Actions: lint+test → dbt build on synthetic → docker build + DagBag
- [ ] first green CI run on GitHub
- [ ] screenshot of dashboard in README
