"""Data ingestion connectors and normalization adapters."""

from app.ingestion.bls_client import (
    fetch_series_metadata as fetch_bls_series_metadata,
    fetch_series_observations as fetch_bls_series_observations,
    ingest_series as ingest_bls_series,
    store_observations as store_bls_observations,
)
from app.ingestion.event_client import ingest_events
from app.ingestion.fred_client import (
    fetch_series_metadata as fetch_fred_series_metadata,
    fetch_series_observations as fetch_fred_series_observations,
    ingest_series as ingest_fred_series,
    store_observations as store_fred_observations,
)

__all__ = [
    "fetch_fred_series_metadata",
    "fetch_fred_series_observations",
    "store_fred_observations",
    "ingest_fred_series",
    "fetch_bls_series_metadata",
    "fetch_bls_series_observations",
    "store_bls_observations",
    "ingest_bls_series",
    "ingest_events",
]
