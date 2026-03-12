"""Scheduled ingestion jobs."""

from app.jobs.ingestion_jobs import (
    DEFAULT_FRED_SERIES_IDS,
    DEFAULT_BLS_SERIES_IDS,
    run_bls_ingestion_job,
    run_consumer_ingestion_job,
    run_event_ingestion_job,
    run_fred_ingestion_job,
    run_full_ingestion_job,
    run_housing_ingestion_job,
    run_market_ingestion_job,
    run_population_ingestion_job,
)

__all__ = [
    "DEFAULT_FRED_SERIES_IDS",
    "DEFAULT_BLS_SERIES_IDS",
    "run_fred_ingestion_job",
    "run_bls_ingestion_job",
    "run_market_ingestion_job",
    "run_housing_ingestion_job",
    "run_consumer_ingestion_job",
    "run_population_ingestion_job",
    "run_event_ingestion_job",
    "run_full_ingestion_job",
]
