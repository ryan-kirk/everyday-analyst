from __future__ import annotations

from datetime import date

from app.ingestion.domain_pipeline import SeriesSpec, ingest_series_specs

MARKET_SERIES_SPECS = [
    SeriesSpec(
        source="fred",
        source_series_id="SP500",
        name="S&P 500 Index",
        category="equities",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="VIXCLS",
        name="CBOE Volatility Index: VIX",
        category="volatility",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="NASDAQCOM",
        name="NASDAQ Composite Index",
        category="equities",
    ),
    SeriesSpec(
        source="stooq",
        source_series_id="IEF",
        name="iShares 7-10 Year Treasury Bond ETF",
        category="treasury_etf",
    ),
    SeriesSpec(
        source="stooq",
        source_series_id="TLT",
        name="iShares 20+ Year Treasury Bond ETF",
        category="treasury_etf",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="DCOILWTICO",
        name="Crude Oil Prices: West Texas Intermediate (WTI)",
        category="commodities",
    ),
    SeriesSpec(
        source="fred",
        source_series_id="PCOPPUSDM",
        name="Global Price of Copper",
        category="commodities",
    ),
]


def ingest_market_series(
    start: date | None = None,
    end: date | None = None,
) -> dict:
    return ingest_series_specs(
        MARKET_SERIES_SPECS,
        domain="market",
        start=start,
        end=end,
    )
