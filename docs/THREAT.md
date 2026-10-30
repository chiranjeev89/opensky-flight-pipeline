# THREAT

Who could behave badly, what they can reach, what stops them. Honest gaps included.

| ID | Actor / entry point | Worst realistic abuse | Mitigation in place | Known gap |
|---|---|---|---|---|
| T-01 | **OpenSky API** (third party) returns malformed, hostile or changed data | Huge payload, wrong types, swapped fields, injected strings in callsign → crash or silent wrong numbers | 30 s timeout; fixed Arrow schema (wrong type = task fails loudly); data treated as values, never executed or concatenated into SQL; dbt tests: altitude/speed limits, positions inside bbox, accepted values | No max payload size check (box limits it in practice to < 1 MB) |
| T-02 | **Leaked OpenSky credentials** (committed .env, logs) | Someone drains my daily credits / gets my account banned | `.env` git-ignored; token error messages never include body or secret (unit test `test_token_failure_does_not_leak_secret`); secrets only via env | No automated secret scan → add gitleaks to CI (README "improve") |
| T-03 | **Leaked Azure connection string** | Read/delete/overwrite the whole lake | Only in `.env`/secrets; dashboard container never gets it | Connection string = account key (full access). Better: SAS token scoped to one container, or Managed Identity in Azure |
| T-04 | **Anonymous dashboard visitor** | Trigger expensive queries, modify data, spend API credits | Dashboard has no credentials, read-only volume + read-only DB connection; queries are fixed (no user SQL); 5-min cache | No auth on :8501 → only expose behind a reverse proxy with auth if published; data is public anyway |
| T-05 | **Malicious pull request / compromised GitHub Action** | Steal repo secrets, push code | `permissions: contents: read`; CI uses no secrets at all (synthetic data); only first-party `actions/*` | Actions pinned by tag, not SHA |
| T-06 | **Compromised Python dependency** | Code execution in Airflow with Blob credentials | Few, well-known deps with version ranges (DEPENDENCIES.md); no dbt packages | No hash-pinned lockfile yet |
| T-07 | **Airflow UI user** | Trigger/clear DAGs, read connections | Local only; `SIMPLE_AUTH_MANAGER_ALL_ADMINS=True` means **no login** for dev | MUST switch to real users (`AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS`) or FAB auth before any non-local deploy; never expose :8080 |
| T-08 | **Insider / me by mistake** | Delete Blob container | – | Enable Blob soft delete + versioning on the real storage account |

Privacy note: ADS-B is public broadcast data. We store transponder IDs and callsigns, no personal data. OpenSky terms: non-commercial/research use; attribute OpenSky in the README.
