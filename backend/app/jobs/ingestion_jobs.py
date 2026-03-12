from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.ingestion import (
    bls_client,
    consumer_client,
    event_client,
    fred_client,
    housing_client,
    market_client,
    population_client,
)

logger = logging.getLogger(__name__)

DEFAULT_FRED_SERIES_IDS = [
    "DGS2",
    "DGS10",
    "T10Y2Y",
    "UNRATE",
    "PAYEMS",
    "CPIAUCSL",
    "PCEPI",
    "INDPRO",
    "MORTGAGE30US",
    "CSUSHPISA",
    "HOUST",
]

# Optional BLS baseline. These can be overridden at runtime.
DEFAULT_BLS_SERIES_IDS = [
    "LNS14000000",  # Unemployment Rate
    "CES0000000001",  # Total Nonfarm Payrolls
]


def _summarize(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "series_count": len(results),
        "fetched": sum(item.get("fetched", 0) for item in results),
        "inserted": sum(item.get("inserted", 0) for item in results),
        "updated": sum(item.get("updated", 0) for item in results),
        "changed": sum(item.get("changed", 0) for item in results),
    }


def run_fred_ingestion_job(
    series_ids: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    target_series = series_ids or DEFAULT_FRED_SERIES_IDS
    logger.info("Starting FRED ingestion job series_count=%s", len(target_series))

    results: list[dict[str, Any]] = []
    for series_id in target_series:
        try:
            result = fred_client.ingest_series(series_id=series_id, start=start, end=end)
            results.append({"series_id": series_id, **result})
        except Exception:
            logger.exception("FRED ingestion failed for series_id=%s", series_id)

    summary = _summarize(results)
    logger.info("Finished FRED ingestion job summary=%s", summary)
    return {"source": "fred", "results": results, "summary": summary}


def run_bls_ingestion_job(
    series_ids: list[str] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, Any]:
    target_series = series_ids or DEFAULT_BLS_SERIES_IDS
    logger.info("Starting BLS ingestion job series_count=%s", len(target_series))

    results: list[dict[str, Any]] = []
    for series_id in target_series:
        try:
            result = bls_client.ingest_series(
                series_id=series_id,
                start_year=start_year,
                end_year=end_year,
            )
            results.append({"series_id": series_id, **result})
        except Exception:
            logger.exception("BLS ingestion failed for series_id=%s", series_id)

    summary = _summarize(results)
    logger.info("Finished BLS ingestion job summary=%s", summary)
    return {"source": "bls", "results": results, "summary": summary}


def run_market_ingestion_job(
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    logger.info("Starting market ingestion job")
    return market_client.ingest_market_series(start=start, end=end)


def run_housing_ingestion_job(
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    logger.info("Starting housing ingestion job")
    return housing_client.ingest_housing_series(start=start, end=end)


def run_consumer_ingestion_job(
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    logger.info("Starting consumer ingestion job")
    return consumer_client.ingest_consumer_series(start=start, end=end)


def run_population_ingestion_job(
    start: date | None = None,
    end: date | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, Any]:
    logger.info("Starting population ingestion job")
    return population_client.ingest_population_series(
        start=start,
        end=end,
        start_year=start_year,
        end_year=end_year,
    )


def run_full_ingestion_job(
    fred_series_ids: list[str] | None = None,
    bls_series_ids: list[str] | None = None,
    fred_start: date | None = None,
    fred_end: date | None = None,
    bls_start_year: int | None = None,
    bls_end_year: int | None = None,
    event_start: date | None = None,
    event_end: date | None = None,
) -> dict[str, Any]:
    fred_result = run_fred_ingestion_job(series_ids=fred_series_ids, start=fred_start, end=fred_end)
    bls_result = run_bls_ingestion_job(
        series_ids=bls_series_ids,
        start_year=bls_start_year,
        end_year=bls_end_year,
    )
    market_result = run_market_ingestion_job(start=fred_start, end=fred_end)
    housing_result = run_housing_ingestion_job(start=fred_start, end=fred_end)
    consumer_result = run_consumer_ingestion_job(start=fred_start, end=fred_end)
    population_result = run_population_ingestion_job(
        start=fred_start,
        end=fred_end,
        start_year=bls_start_year,
        end_year=bls_end_year,
    )
    event_result = run_event_ingestion_job(start=event_start, end=event_end)
    return {
        "fred": fred_result,
        "bls": bls_result,
        "market": market_result,
        "housing": housing_result,
        "consumer": consumer_result,
        "population": population_result,
        "events": event_result,
    }


def run_event_ingestion_job(
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    logger.info("Starting event ingestion job")
    try:
        result = event_client.ingest_events(start=start, end=end)
    except Exception:
        logger.exception("Event ingestion failed")
        result = {"fetched": 0, "inserted": 0, "updated": 0, "changed": 0}
    logger.info("Finished event ingestion job summary=%s", result)
    return {"source": "events", "summary": result}
