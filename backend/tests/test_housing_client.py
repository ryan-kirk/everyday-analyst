from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.ingestion import housing_client


class TestHousingClient(TestCase):
    def test_housing_specs_include_expected_series(self) -> None:
        ids = {spec.source_series_id for spec in housing_client.HOUSING_SERIES_SPECS}
        self.assertIn("CSUSHPISA", ids)
        self.assertIn("USSTHPI", ids)
        self.assertIn("PERMIT", ids)
        self.assertIn("HOUST", ids)
        self.assertIn("MORTGAGE30US", ids)
        self.assertIn("M0264AUSM500NNBR", ids)
        self.assertNotIn("MBAAIMS", ids)

        optional_ids = {
            spec.source_series_id for spec in housing_client.HOUSING_SERIES_SPECS if spec.optional
        }
        self.assertIn("M0264AUSM500NNBR", optional_ids)

    def test_ingest_housing_series_dispatches_to_domain_pipeline(self) -> None:
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)

        with patch(
            "app.ingestion.housing_client.ingest_series_specs",
            return_value={"domain": "housing", "summary": {"series_count": 6}},
        ) as ingest_mock:
            result = housing_client.ingest_housing_series(start=start, end=end)

        self.assertEqual("housing", result["domain"])
        self.assertEqual(6, result["summary"]["series_count"])
        self.assertEqual("housing", ingest_mock.call_args.kwargs["domain"])
        self.assertEqual(start, ingest_mock.call_args.kwargs["start"])
        self.assertEqual(end, ingest_mock.call_args.kwargs["end"])
