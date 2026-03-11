from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

from app.ingestion.http_client import request_json_with_retry
from app.ingestion.storage import SeriesMetadata, store_series_observations
from app.models.observation import Observation

logger = logging.getLogger(__name__)

FRED_API_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_SOURCE = "fred"

SERIES_CATEGORY_OVERRIDES = {
    "DGS2": "treasury_rates",
    "DGS10": "treasury_rates",
    "T10Y2Y": "treasury_spread",
    "UNRATE": "labor",
    "PAYEMS": "labor",
    "CPIAUCSL": "inflation",
    "PCEPI": "inflation",
    "INDPRO": "production",
    "MORTGAGE30US": "housing",
    "CSUSHPISA": "housing",
    "HOUST": "housing",
}


def _get_fred_api_key() -> str:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not set. Add it to your environment before ingestion.")
    return api_key


def _fred_get(endpoint: str, **params: Any) -> dict[str, Any]:
    query_params = {
        "api_key": _get_fred_api_key(),
        "file_type": "json",
        **params,
    }
    return request_json_with_retry("GET", f"{FRED_API_BASE_URL}{endpoint}", params=query_params)


def fetch_series_metadata(series_id: str) -> SeriesMetadata:
    payload = _fred_get("/series", series_id=series_id)
    series_items = payload.get("seriess", [])
    if not series_items:
        raise ValueError(f"FRED metadata not found for series_id={series_id}")

    item = series_items[0]
    return {
        "name": item.get("title", series_id),
        "source": FRED_SOURCE,
        "source_series_id": series_id,
        "units": item.get("units_short") or item.get("units"),
        "frequency": item.get("frequency_short") or item.get("frequency"),
        "category": SERIES_CATEGORY_OVERRIDES.get(series_id),
    }


def fetch_series_observations(
    series_id: str,
    start: date | None = None,
    end: date | None = None,
) -> list[Observation]:
    params: dict[str, str] = {
        "series_id": series_id,
        "sort_order": "asc",
    }
    if start is not None:
        params["observation_start"] = start.isoformat()
    if end is not None:
        params["observation_end"] = end.isoformat()

    payload = _fred_get("/series/observations", **params)
    raw_observations = payload.get("observations", [])

    normalized: list[Observation] = []
    for item in raw_observations:
        value_raw = item.get("value")
        observation_date_raw = item.get("date")
        if value_raw in (None, ".", "") or not observation_date_raw:
            continue

        try:
            normalized.append(
                Observation(
                    series_id=0,
                    observation_date=date.fromisoformat(observation_date_raw),
                    value=float(value_raw),
                )
            )
        except (TypeError, ValueError):
            logger.warning(
                "Skipping malformed FRED observation series=%s date=%s value=%s",
                series_id,
                observation_date_raw,
                value_raw,
            )
            continue

    logger.info("Fetched FRED observations series=%s count=%s", series_id, len(normalized))
    return normalized


def store_observations(series_id: str, observations: list[Observation]) -> int:
    metadata = fetch_series_metadata(series_id)
    result = store_series_observations(metadata, observations)
    return result["changed"]


def ingest_series(
    series_id: str,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, int]:
    metadata = fetch_series_metadata(series_id)
    observations = fetch_series_observations(series_id=series_id, start=start, end=end)
    result = store_series_observations(metadata, observations)
    logger.info(
        "Ingested FRED series=%s fetched=%s changed=%s",
        series_id,
        result["fetched"],
        result["changed"],
    )
    return result

