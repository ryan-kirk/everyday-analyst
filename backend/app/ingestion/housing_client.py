from __future__ import annotations

from datetime import date

from app.ingestion.domain_pipeline import SeriesSpec, ingest_series_specs

HOUSING_SERIES_SPECS = [
    SeriesSpec(
        source="fred",
        source_series_id="CSUSHPISA",
        name="S&P CoreLogic Case-Shiller U.S. National Home Price Index",
        category="housing_prices",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="USSTHPI",
        name="All-Transactions House Price Index for the United States",
        category="housing_prices",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="PERMIT",
        name="New Private Housing Units Authorized by Building Permits",
        category="housing_permits",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="HOUST",
        name="New Privately-Owned Housing Units Started",
        category="housing_starts",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="MORTGAGE30US",
        name="30-Year Fixed Rate Mortgage Average in the United States",
        category="mortgage_rates",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="M0264AUSM500NNBR",
        name="New Home Mortgage Applications for United States",
        category="mortgage_applications",
        optional=True,
    ),
]


def ingest_housing_series(
    start: date | None = None,
    end: date | None = None,
) -> dict:
    return ingest_series_specs(
        HOUSING_SERIES_SPECS,
        domain="housing",
        start=start,
        end=end,
    )
