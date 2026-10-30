.PHONY: up down sample dbt test lint measure
up:        ## start full stack
	docker compose up -d --build
down:
	docker compose down
sample:    ## 72h of synthetic data into data/lake (no API needed)
	python scripts/generate_sample_data.py --out data/lake --hours 72
dbt:       ## dbt build against local lake
	cd dbt && LOCAL_LAKE_DIR=../data/lake DBT_DUCKDB_PATH=../data/lake/warehouse.duckdb dbt build --profiles-dir . --target dev
	cp data/lake/warehouse.duckdb data/lake/serving.duckdb
test:
	pytest -q
lint:
	ruff check . && ruff format --check .
measure:   ## print README results table
	python scripts/measure_pipeline.py --db data/lake/serving.duckdb
