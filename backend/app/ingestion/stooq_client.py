from __future__ import annotations

import io
import logging
from datetime import date

import pandas as pd

from app.ingestion.http_client import request_text_with_retry
from app.ingestion.storage import SeriesMetadata, store_series_observations
from app.models.observation import Observation

logger = logging.getLogger(__name__)

STOOQ_SYMBOL_MAP = {
    "IEF": "ief.us",
    "TLT": "tlt.us",
}
STOOQ_SOURCE = "stooq"
STOOQ_DAILY_HISTORY_URL = "https://stooq.com/q/d/l/"

STOOQ_METADATA_OVERRIDES: dict[str, dict[str, str | None]] = {
    "IEF": {
        "name": "iShares 7-10 Year Treasury Bond ETF",
        "units": "USD",
        "frequency": "D",
        "category": "treasury_etf",
    },
    "TLT": {
        "name": "iShares 20+ Year Treasury Bond ETF",
        "units": "USD",
        "frequency": "D",
        "category": "treasury_etf",
    },
}


def fetch_series_metadata(symbol: str) -> SeriesMetadata:
    normalized = symbol.strip().upper()
    overrides = STOOQ_METADATA_OVERRIDES.get(normalized, {})
    return {
        "name": overrides.get("name") or normalized,
        "source": STOOQ_SOURCE,
        "source_series_id": normalized,
        "units": overrides.get("units") or "USD",
        "frequency": overrides.get("frequency") or "D",
        "category": overrides.get("category"),
    }


def fetch_series_observations(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
) -> list[Observation]:
    normalized = symbol.strip().upper()
    stooq_symbol = STOOQ_SYMBOL_MAP.get(normalized, f"{normalized.lower()}.us")
    text = request_text_with_retry(
        "GET",
        STOOQ_DAILY_HISTORY_URL,
        params={"s": stooq_symbol, "i": "d"},
    )

    if "no data" in text.lower():
        raise ValueError(f"Stooq has no data for symbol={normalized}")

    frame = pd.read_csv(io.StringIO(text))
    if frame.empty or "Date" not in frame.columns or "Close" not in frame.columns:
        raise ValueError(f"Unexpected Stooq response for symbol={normalized}")

    normalized_rows: list[Observation] = []
    for row in frame.itertuples(index=False):
        raw_date = getattr(row, "Date", None)
        raw_close = getattr(row, "Close", None)
        if raw_date is None or pd.isna(raw_close):
            continue

        try:
            observation_date = date.fromisoformat(str(raw_date))
            value = float(raw_close)
        except (TypeError, ValueError):
            logger.warning(
                "Skipping malformed Stooq observation symbol=%s date=%s close=%s",
                normalized,
                raw_date,
                raw_close,
            )
            continue

        if start is not None and observation_date < start:
            continue
        if end is not None and observation_date > end:
            continue

        normalized_rows.append(
            Observation(
                series_id=0,
                observation_date=observation_date,
                value=value,
            )
        )

    normalized_rows.sort(key=lambda obs: obs.observation_date)
    logger.info("Fetched Stooq observations symbol=%s count=%s", normalized, len(normalized_rows))
    return normalized_rows


def store_observations(symbol: str, observations: list[Observation]) -> int:
    metadata = fetch_series_metadata(symbol)
    result = store_series_observations(metadata, observations)
    return result["changed"]


def ingest_series(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, int]:
    metadata = fetch_series_metadata(symbol)
    observations = fetch_series_observations(symbol=symbol, start=start, end=end)
    result = store_series_observations(metadata, observations)
    logger.info(
        "Ingested Stooq series symbol=%s fetched=%s changed=%s",
        symbol,
        result["fetched"],
        result["changed"],
    )
    return result
