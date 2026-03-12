from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.ingestion import stooq_client
from app.models.observation import Observation
from app.models.series import Series


class TestStooqClient(TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.testing_session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            class_=Session,
        )
        Base.metadata.create_all(self.engine)
        self.session_patcher = patch("app.ingestion.storage.SessionLocal", self.testing_session_local)
        self.session_patcher.start()

    def tearDown(self) -> None:
        self.session_patcher.stop()
        self.engine.dispose()

    def test_fetch_series_observations_parses_daily_close_values(self) -> None:
        csv_body = """Date,Open,High,Low,Close,Volume
2024-01-02,95.1,95.8,94.9,95.6,100000
2024-01-03,95.6,96.4,95.2,96.1,110000
2024-01-04,96.1,96.3,95.7,N/D,90000
"""

        with patch("app.ingestion.stooq_client.request_text_with_retry", return_value=csv_body):
            observations = stooq_client.fetch_series_observations(
                symbol="IEF",
                start=date(2024, 1, 2),
                end=date(2024, 1, 3),
            )

        self.assertEqual(2, len(observations))
        self.assertTrue(all(isinstance(obs, Observation) for obs in observations))
        self.assertEqual(date(2024, 1, 2), observations[0].observation_date)
        self.assertEqual(95.6, observations[0].value)
        self.assertEqual(date(2024, 1, 3), observations[1].observation_date)
        self.assertEqual(96.1, observations[1].value)

    def test_ingest_series_stores_metadata_and_observations(self) -> None:
        csv_body = """Date,Open,High,Low,Close,Volume
2024-01-02,95.1,95.8,94.9,95.6,100000
2024-01-03,95.6,96.4,95.2,96.1,110000
"""

        with patch("app.ingestion.stooq_client.request_text_with_retry", return_value=csv_body):
            result = stooq_client.ingest_series("IEF")

        self.assertEqual(2, result["fetched"])
        self.assertEqual(2, result["inserted"])
        self.assertEqual(0, result["updated"])

        with self.testing_session_local() as db:
            series = db.scalar(
                select(Series).where(
                    Series.source == "stooq",
                    Series.source_series_id == "IEF",
                )
            )
            self.assertIsNotNone(series)
            self.assertEqual("treasury_etf", series.category)

            rows = db.scalars(
                select(Observation)
                .where(Observation.series_id == series.id)
                .order_by(Observation.observation_date.asc())
            ).all()
            self.assertEqual(2, len(rows))
            self.assertEqual(96.1, rows[1].value)
