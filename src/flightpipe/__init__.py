"""flightpipe: OpenSky -> Azure Blob ingestion library used by the Airflow DAGs.

Kept as a plain Python package (no Airflow imports) so every function can be
unit tested without a running Airflow. See docs/ARCHITECTURE.md.
"""

__version__ = "0.1.0"
