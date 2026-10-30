# Airflow image + our library + dbt in an ISOLATED venv.
# WHY the separate venv: dbt and Airflow pin conflicting versions of shared
# libraries; installing both into one env breaks one of them (D-007).
FROM apache/airflow:3.1.7-python3.12

USER root
RUN python -m venv /opt/dbt-venv && /opt/dbt-venv/bin/pip install --no-cache-dir "dbt-duckdb==1.11.1" \
    && mkdir -p /opt/lake && chown -R airflow:0 /opt/lake /opt/dbt-venv
USER airflow

COPY requirements-pipeline.txt /tmp/requirements-pipeline.txt
# Official constraints file = the exact versions Airflow 3.1.7 is tested with (same as verified locally)
RUN pip install --no-cache-dir "apache-airflow==3.1.7" -r /tmp/requirements-pipeline.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.1.7/constraints-3.12.txt"

COPY --chown=airflow:0 src /opt/airflow/src
ENV PYTHONPATH=/opt/airflow/src
