from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

import app.ingestion.bls_client as bls_client
import app.ingestion.fred_client as fred_client
import app.ingestion.stooq_client as stooq_client
from app.ingestion.storage import SeriesMetadata, store_series_observations

logger = logging.getLogger(__name__)

SeriesSource = Literal["fred", "bls", "stooq"]


@dataclass(frozen=True)
class SeriesSpec:
    source: SeriesSource
    source_series_id: str
    name: str | None = None
    units: str | None = None
    frequency: str | None = None
    category: str | None = None
    optional: bool = False


def ingest_series_specs(
    specs: list[SeriesSpec],
    *,
    domain: str,
    start: date | None = None,
    end: date | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, Any]:
    """Ingest a domain-specific list of series specs into normalized storage."""
    results: list[dict[str, Any]] = []
    optional_failures = 0
    failed = 0

    for spec in specs:
        try:
            result = _ingest_single_spec(
                spec,
                start=start,
                end=end,
                start_year=start_year,
                end_year=end_year,
            )
            results.append(
                {
                    "source": spec.source,
                    "source_series_id": spec.source_series_id,
                    "optional": spec.optional,
                    "status": "ok",
                    **result,
                }
            )
        except Exception as exc:
            if spec.optional:
                optional_failures += 1
                logger.warning(
                    "Optional series ingestion failed domain=%s source=%s series=%s error=%s",
                    domain,
                    spec.source,
                    spec.source_series_id,
                    exc,
                )
                continue

            failed += 1
            logger.exception(
                "Series ingestion failed domain=%s source=%s series=%s",
                domain,
                spec.source,
                spec.source_series_id,
            )
            results.append(
                {
                    "source": spec.source,
                    "source_series_id": spec.source_series_id,
                    "optional": spec.optional,
                    "status": "failed",
                }
            )

    summary = {
        "series_count": len(specs),
        "attempted": len(specs) - optional_failures,
        "succeeded": sum(1 for row in results if row.get("status") == "ok"),
        "failed": failed,
        "optional_failures": optional_failures,
        "fetched": sum(row.get("fetched", 0) for row in results if row.get("status") == "ok"),
        "inserted": sum(row.get("inserted", 0) for row in results if row.get("status") == "ok"),
        "updated": sum(row.get("updated", 0) for row in results if row.get("status") == "ok"),
        "changed": sum(row.get("changed", 0) for row in results if row.get("status") == "ok"),
    }

    logger.info("Finished domain ingestion domain=%s summary=%s", domain, summary)
    return {"domain": domain, "results": results, "summary": summary}


def _ingest_single_spec(
    spec: SeriesSpec,
    *,
    start: date | None = None,
    end: date | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, int]:
    if spec.source == "fred":
        metadata = fred_client.fetch_series_metadata(spec.source_series_id)
        observations = fred_client.fetch_series_observations(
            series_id=spec.source_series_id,
            start=start,
            end=end,
        )
    elif spec.source == "bls":
        effective_start_year = start_year or (start.year if start else None)
        effective_end_year = end_year or (end.year if end else None)
        metadata = bls_client.fetch_series_metadata(spec.source_series_id)
        observations = bls_client.fetch_series_observations(
            series_id=spec.source_series_id,
            start_year=effective_start_year,
            end_year=effective_end_year,
        )
    elif spec.source == "stooq":
        metadata = stooq_client.fetch_series_metadata(spec.source_series_id)
        observations = stooq_client.fetch_series_observations(
            symbol=spec.source_series_id,
            start=start,
            end=end,
        )
    else:  # pragma: no cover - guarded by SeriesSource typing.
        raise ValueError(f"Unsupported source={spec.source}")

    merged_metadata = _merge_metadata(metadata, spec)
    return store_series_observations(merged_metadata, observations)


def _merge_metadata(metadata: SeriesMetadata, spec: SeriesSpec) -> SeriesMetadata:
    return {
        "name": spec.name or metadata["name"],
        "source": metadata["source"],
        "source_series_id": metadata["source_series_id"],
        "units": spec.units or metadata["units"],
        "frequency": spec.frequency or metadata["frequency"],
        "category": spec.category or metadata["category"],
    }
