from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.ingestion import market_client


class TestMarketClient(TestCase):
    def test_market_specs_include_expected_series(self) -> None:
        ids = {spec.source_series_id for spec in market_client.MARKET_SERIES_SPECS}
        self.assertIn("SP500", ids)
        self.assertIn("VIXCLS", ids)
        self.assertIn("NASDAQCOM", ids)
        self.assertIn("IEF", ids)
        self.assertIn("TLT", ids)
        self.assertIn("DCOILWTICO", ids)
        self.assertIn("PCOPPUSDM", ids)
        self.assertNotIn("GOLDAMGBD228NLBM", ids)

        sources = {spec.source for spec in market_client.MARKET_SERIES_SPECS}
        self.assertIn("fred", sources)
        self.assertIn("stooq", sources)

    def test_ingest_market_series_dispatches_to_domain_pipeline(self) -> None:
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)

        with patch(
            "app.ingestion.market_client.ingest_series_specs",
            return_value={"domain": "market", "summary": {"series_count": 7}},
        ) as ingest_mock:
            result = market_client.ingest_market_series(start=start, end=end)

        self.assertEqual("market", result["domain"])
        self.assertEqual(7, result["summary"]["series_count"])
        self.assertEqual("market", ingest_mock.call_args.kwargs["domain"])
        self.assertEqual(start, ingest_mock.call_args.kwargs["start"])
        self.assertEqual(end, ingest_mock.call_args.kwargs["end"])
