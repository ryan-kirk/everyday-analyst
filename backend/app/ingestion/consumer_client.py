from __future__ import annotations

from datetime import date

from app.ingestion.domain_pipeline import SeriesSpec, ingest_series_specs

CONSUMER_SERIES_SPECS = [
    SeriesSpec(
        source="fred",
        source_series_id="RSAFS",
        name="Retail and Food Services Sales",
        category="retail_sales",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="RRSFS",
        name="Real Retail and Food Services Sales",
        category="retail_sales",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="UMCSENT",
        name="University of Michigan: Consumer Sentiment",
        category="consumer_sentiment",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="REVOLSL",
        name="Revolving Consumer Credit Owned and Securitized",
        category="consumer_credit",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="CCLACBW027SBOG",
        name="Consumer Credit Card Spending Proxy",
        category="credit_card_spending",
        optional=True,
    ),
]


def ingest_consumer_series(
    start: date | None = None,
    end: date | None = None,
) -> dict:
    return ingest_series_specs(
        CONSUMER_SERIES_SPECS,
        domain="consumer",
        start=start,
        end=end,
    )
