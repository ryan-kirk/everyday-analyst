from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.ingestion import consumer_client


class TestConsumerClient(TestCase):
    def test_consumer_specs_include_expected_series(self) -> None:
        ids = {spec.source_series_id for spec in consumer_client.CONSUMER_SERIES_SPECS}
        self.assertIn("RSAFS", ids)
        self.assertIn("RRSFS", ids)
        self.assertIn("UMCSENT", ids)
        self.assertIn("REVOLSL", ids)
        self.assertIn("CCLACBW027SBOG", ids)

        optional_ids = {
            spec.source_series_id for spec in consumer_client.CONSUMER_SERIES_SPECS if spec.optional
        }
        self.assertIn("CCLACBW027SBOG", optional_ids)

    def test_ingest_consumer_series_dispatches_to_domain_pipeline(self) -> None:
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)

        with patch(
            "app.ingestion.consumer_client.ingest_series_specs",
            return_value={"domain": "consumer", "summary": {"series_count": 5}},
        ) as ingest_mock:
            result = consumer_client.ingest_consumer_series(start=start, end=end)

        self.assertEqual("consumer", result["domain"])
        self.assertEqual(5, result["summary"]["series_count"])
        self.assertEqual("consumer", ingest_mock.call_args.kwargs["domain"])
        self.assertEqual(start, ingest_mock.call_args.kwargs["start"])
        self.assertEqual(end, ingest_mock.call_args.kwargs["end"])
