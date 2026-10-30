# BUG-003: Empty .env value overrode the Azurite default
Symptom (found in pre-boot review, before first Docker run): with `AZURE_STORAGE_CONNECTION_STRING=` left empty in `.env`, the ingest would fail with an invalid connection string instead of using local Azurite.
Root cause: compose `env_file` passes empty values as `""`; `os.getenv(name, default)` only uses the default when the variable is *absent*.
Fix: `_env()` helper in config.py treats empty as unset; used for every string setting.
Verification: `test_empty_env_value_falls_back_to_default`; `pytest` → 17 passed, 1 skipped.

## Log
- 2026-10-28 found while preparing the first Docker boot.
