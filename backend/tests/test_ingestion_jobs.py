from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.jobs import ingestion_jobs


class TestIngestionJobs(TestCase):
    def test_run_domain_ingestion_jobs_dispatch_to_connectors(self) -> None:
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)

        with patch(
            "app.jobs.ingestion_jobs.market_client.ingest_market_series",
            return_value={"domain": "market"},
        ) as market_mock:
            market_result = ingestion_jobs.run_market_ingestion_job(start=start, end=end)
        self.assertEqual("market", market_result["domain"])
        market_mock.assert_called_once_with(start=start, end=end)

        with patch(
            "app.jobs.ingestion_jobs.housing_client.ingest_housing_series",
            return_value={"domain": "housing"},
        ) as housing_mock:
            housing_result = ingestion_jobs.run_housing_ingestion_job(start=start, end=end)
        self.assertEqual("housing", housing_result["domain"])
        housing_mock.assert_called_once_with(start=start, end=end)

        with patch(
            "app.jobs.ingestion_jobs.consumer_client.ingest_consumer_series",
            return_value={"domain": "consumer"},
        ) as consumer_mock:
            consumer_result = ingestion_jobs.run_consumer_ingestion_job(start=start, end=end)
        self.assertEqual("consumer", consumer_result["domain"])
        consumer_mock.assert_called_once_with(start=start, end=end)

        with patch(
            "app.jobs.ingestion_jobs.population_client.ingest_population_series",
            return_value={"domain": "population"},
        ) as population_mock:
            population_result = ingestion_jobs.run_population_ingestion_job(
                start=start,
                end=end,
                start_year=2024,
                end_year=2025,
            )
        self.assertEqual("population", population_result["domain"])
        population_mock.assert_called_once_with(
            start=start,
            end=end,
            start_year=2024,
            end_year=2025,
        )

    def test_run_full_ingestion_job_includes_all_domains(self) -> None:
        with patch("app.jobs.ingestion_jobs.run_fred_ingestion_job", return_value={"source": "fred"}) as fred_mock:
            with patch("app.jobs.ingestion_jobs.run_bls_ingestion_job", return_value={"source": "bls"}) as bls_mock:
                with patch(
                    "app.jobs.ingestion_jobs.run_market_ingestion_job",
                    return_value={"domain": "market"},
                ) as market_mock:
                    with patch(
                        "app.jobs.ingestion_jobs.run_housing_ingestion_job",
                        return_value={"domain": "housing"},
                    ) as housing_mock:
                        with patch(
                            "app.jobs.ingestion_jobs.run_consumer_ingestion_job",
                            return_value={"domain": "consumer"},
                        ) as consumer_mock:
                            with patch(
                                "app.jobs.ingestion_jobs.run_population_ingestion_job",
                                return_value={"domain": "population"},
                            ) as population_mock:
                                with patch(
                                    "app.jobs.ingestion_jobs.run_event_ingestion_job",
                                    return_value={"source": "events"},
                                ) as events_mock:
                                    result = ingestion_jobs.run_full_ingestion_job(
                                        fred_start=date(2025, 1, 1),
                                        fred_end=date(2025, 12, 31),
                                        bls_start_year=2024,
                                        bls_end_year=2025,
                                        event_start=date(2025, 1, 1),
                                        event_end=date(2025, 12, 31),
                                    )

        self.assertEqual(
            {"fred", "bls", "market", "housing", "consumer", "population", "events"},
            set(result.keys()),
        )
        fred_mock.assert_called_once()
        bls_mock.assert_called_once()
        market_mock.assert_called_once()
        housing_mock.assert_called_once()
        consumer_mock.assert_called_once()
        population_mock.assert_called_once()
        events_mock.assert_called_once()
