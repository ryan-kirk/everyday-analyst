from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.ingestion.domain_pipeline import SeriesSpec, ingest_series_specs
from app.models.observation import Observation


class TestDomainPipeline(TestCase):
    def test_ingest_series_specs_merges_metadata_overrides(self) -> None:
        specs = [
            SeriesSpec(
                source="fred",
                source_series_id="SP500",
                name="S&P 500 Index",
                category="equities",
            )
        ]
        metadata = {
            "name": "Raw Name",
            "source": "fred",
            "source_series_id": "SP500",
            "units": "Index",
            "frequency": "D",
            "category": "raw",
        }
        observations = [Observation(series_id=0, observation_date=date(2024, 1, 2), value=4800.5)]

        with patch("app.ingestion.domain_pipeline.fred_client.fetch_series_metadata", return_value=metadata):
            with patch(
                "app.ingestion.domain_pipeline.fred_client.fetch_series_observations",
                return_value=observations,
            ):
                with patch(
                    "app.ingestion.domain_pipeline.store_series_observations",
                    return_value={"fetched": 1, "inserted": 1, "updated": 0, "changed": 1},
                ) as store_mock:
                    result = ingest_series_specs(specs, domain="market")

        self.assertEqual(1, result["summary"]["succeeded"])
        stored_metadata = store_mock.call_args.args[0]
        self.assertEqual("S&P 500 Index", stored_metadata["name"])
        self.assertEqual("equities", stored_metadata["category"])

    def test_ingest_series_specs_skips_optional_failures(self) -> None:
        specs = [
            SeriesSpec(source="fred", source_series_id="UNKNOWN_OPTIONAL", optional=True),
        ]

        with patch(
            "app.ingestion.domain_pipeline.fred_client.fetch_series_metadata",
            side_effect=ValueError("not found"),
        ):
            result = ingest_series_specs(specs, domain="market")

        self.assertEqual(0, result["summary"]["succeeded"])
        self.assertEqual(0, result["summary"]["failed"])
        self.assertEqual(1, result["summary"]["optional_failures"])

    def test_ingest_series_specs_tracks_required_failures(self) -> None:
        specs = [SeriesSpec(source="fred", source_series_id="UNKNOWN_REQUIRED", optional=False)]

        with patch(
            "app.ingestion.domain_pipeline.fred_client.fetch_series_metadata",
            side_effect=ValueError("not found"),
        ):
            result = ingest_series_specs(specs, domain="market")

        self.assertEqual(0, result["summary"]["succeeded"])
        self.assertEqual(1, result["summary"]["failed"])
