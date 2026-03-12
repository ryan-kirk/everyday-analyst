from __future__ import annotations

import os
from datetime import date

from app.ingestion.domain_pipeline import SeriesSpec, ingest_series_specs

DEFAULT_POPULATION_SERIES_SPECS = [
    SeriesSpec(
        source="fred",
        source_series_id="POPTHM",
        name="Civilian Noninstitutional Population",
        category="population",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="NETMIGNACS006037",
        name="Net County-to-County Migration Flow (Los Angeles County, CA)",
        category="population_migration",
        optional=True,
    ),
    SeriesSpec(
        source="fred",
        source_series_id="BPPRIV006037",
        name="Private Housing Units Authorized by Building Permits (Los Angeles County, CA)",
        category="county_housing_permits",
        optional=True,
    ),
    SeriesSpec(
        source="bls",
        source_series_id="LAUCN060370000000005",
        name="Unemployment Rate (Los Angeles County, CA)",
        category="local_employment",
        optional=True,
    ),
]


def _env_series_specs() -> list[SeriesSpec]:
    """Load optional domain series IDs from environment variables."""
    specs: list[SeriesSpec] = []

    for source_series_id in _split_env("POPULATION_MIGRATION_SERIES_IDS"):
        specs.append(
            SeriesSpec(
                source="fred",
                source_series_id=source_series_id,
                category="population_migration",
            )
        )

    for source_series_id in _split_env("COUNTY_HOUSING_PERMIT_SERIES_IDS"):
        specs.append(
            SeriesSpec(
                source="fred",
                source_series_id=source_series_id,
                category="county_housing_permits",
            )
        )

    for source_series_id in _split_env("LOCAL_EMPLOYMENT_BLS_SERIES_IDS"):
        specs.append(
            SeriesSpec(
                source="bls",
                source_series_id=source_series_id,
                category="local_employment",
            )
        )

    return specs


def _split_env(name: str) -> list[str]:
    value = os.getenv(name, "")
    result: list[str] = []
    seen: set[str] = set()
    for item in value.split(","):
        normalized = item.strip()
        if not normalized:
            continue
        normalized = normalized.upper()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def get_population_series_specs() -> list[SeriesSpec]:
    extra_specs = _env_series_specs()
    if not extra_specs:
        return DEFAULT_POPULATION_SERIES_SPECS

    existing = {(spec.source, spec.source_series_id) for spec in DEFAULT_POPULATION_SERIES_SPECS}
    merged = list(DEFAULT_POPULATION_SERIES_SPECS)
    for spec in extra_specs:
        key = (spec.source, spec.source_series_id)
        if key in existing:
            continue
        merged.append(spec)
    return merged


def ingest_population_series(
    start: date | None = None,
    end: date | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict:
    return ingest_series_specs(
        get_population_series_specs(),
        domain="population",
        start=start,
        end=end,
        start_year=start_year,
        end_year=end_year,
    )
