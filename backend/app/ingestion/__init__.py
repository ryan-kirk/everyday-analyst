"""Data ingestion connectors and normalization adapters."""

from app.ingestion.fred_client import (
    fetch_series_metadata,
    fetch_series_observations,
    store_observations,
)

__all__ = [
    "fetch_series_metadata",
    "fetch_series_observations",
    "store_observations",
]
