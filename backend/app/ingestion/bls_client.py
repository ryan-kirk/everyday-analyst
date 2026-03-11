from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

from app.ingestion.http_client import request_json_with_retry
from app.ingestion.storage import SeriesMetadata, store_series_observations
from app.models.observation import Observation

logger = logging.getLogger(__name__)

BLS_API_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SOURCE = "bls"

SERIES_METADATA_OVERRIDES: dict[str, dict[str, str | None]] = {
    "LNS14000000": {
        "name": "Unemployment Rate (BLS)",
        "units": "Percent",
        "frequency": "M",
        "category": "labor",
    },
    "CES0000000001": {
        "name": "Total Nonfarm Payrolls (BLS)",
        "units": "Thousands",
        "frequency": "M",
        "category": "labor",
    },
}


def _get_bls_api_key() -> str | None:
    return os.getenv("BLS_API_KEY")


def _bls_post(body: dict[str, Any]) -> dict[str, Any]:
    return request_json_with_retry("POST", BLS_API_BASE_URL, json_body=body)


def fetch_series_metadata(series_id: str) -> SeriesMetadata:
    overrides = SERIES_METADATA_OVERRIDES.get(series_id, {})
    return {
        "name": (overrides.get("name") or series_id),
        "source": BLS_SOURCE,
        "source_series_id": series_id,
        "units": overrides.get("units"),
        "frequency": (overrides.get("frequency") or "M"),
        "category": overrides.get("category"),
    }


def fetch_series_observations(
    series_id: str,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[Observation]:
    today = date.today()
    effective_end_year = end_year or today.year
    effective_start_year = start_year or (effective_end_year - 20)

    request_body: dict[str, Any] = {
        "seriesid": [series_id],
        "startyear": str(effective_start_year),
        "endyear": str(effective_end_year),
    }
    api_key = _get_bls_api_key()
    if api_key:
        request_body["registrationkey"] = api_key

    payload = _bls_post(request_body)
    status = payload.get("status")
    if status != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS request failed for series_id={series_id}: {payload}")

    series_items = payload.get("Results", {}).get("series", [])
    if not series_items:
        raise ValueError(f"BLS observations not found for series_id={series_id}")

    raw_observations = series_items[0].get("data", [])
    normalized: list[Observation] = []

    for item in raw_observations:
        period = item.get("period")
        year_raw = item.get("year")
        value_raw = item.get("value")

        if not period or not year_raw or value_raw in (None, "", "."):
            continue
        if not period.startswith("M") or period == "M13":
            # BLS M13 is annual average and does not map cleanly to a month.
            continue

        try:
            month = int(period[1:])
            obs_date = date(int(year_raw), month, 1)
            obs_value = float(str(value_raw).replace(",", ""))
        except (TypeError, ValueError):
            logger.warning(
                "Skipping malformed BLS observation series=%s year=%s period=%s value=%s",
                series_id,
                year_raw,
                period,
                value_raw,
            )
            continue

        normalized.append(
            Observation(
                series_id=0,
                observation_date=obs_date,
                value=obs_value,
            )
        )

    normalized.sort(key=lambda obs: obs.observation_date)
    logger.info("Fetched BLS observations series=%s count=%s", series_id, len(normalized))
    return normalized


def store_observations(series_id: str, observations: list[Observation]) -> int:
    metadata = fetch_series_metadata(series_id)
    result = store_series_observations(metadata, observations)
    return result["changed"]


def ingest_series(
    series_id: str,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, int]:
    metadata = fetch_series_metadata(series_id)
    observations = fetch_series_observations(
        series_id=series_id,
        start_year=start_year,
        end_year=end_year,
    )
    result = store_series_observations(metadata, observations)
    logger.info(
        "Ingested BLS series=%s fetched=%s changed=%s",
        series_id,
        result["fetched"],
        result["changed"],
    )
    return result

