"""Data ingestion connectors and normalization adapters."""

from app.ingestion.bls_client import (
    fetch_series_metadata as fetch_bls_series_metadata,
    fetch_series_observations as fetch_bls_series_observations,
    ingest_series as ingest_bls_series,
    store_observations as store_bls_observations,
)
from app.ingestion.consumer_client import ingest_consumer_series
from app.ingestion.housing_client import ingest_housing_series
from app.ingestion.market_client import ingest_market_series
from app.ingestion.population_client import ingest_population_series
from app.ingestion.event_client import ingest_events
from app.ingestion.fred_client import (
    fetch_series_metadata as fetch_fred_series_metadata,
    fetch_series_observations as fetch_fred_series_observations,
    ingest_series as ingest_fred_series,
    store_observations as store_fred_observations,
)
from app.ingestion.stooq_client import (
    fetch_series_metadata as fetch_stooq_series_metadata,
    fetch_series_observations as fetch_stooq_series_observations,
    ingest_series as ingest_stooq_series,
    store_observations as store_stooq_observations,
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
    "fetch_stooq_series_metadata",
    "fetch_stooq_series_observations",
    "store_stooq_observations",
    "ingest_stooq_series",
    "ingest_events",
    "ingest_market_series",
    "ingest_housing_series",
    "ingest_consumer_series",
    "ingest_population_series",
]
