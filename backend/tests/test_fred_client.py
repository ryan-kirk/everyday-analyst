from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.ingestion import fred_client
from app.models.observation import Observation
from app.models.series import Series


class TestFredClient(TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.testing_session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            class_=Session,
        )
        Base.metadata.create_all(self.engine)

        self.original_session_local = fred_client.SessionLocal
        fred_client.SessionLocal = self.testing_session_local

    def tearDown(self) -> None:
        fred_client.SessionLocal = self.original_session_local
        self.engine.dispose()

    def test_fetch_series_observations_normalizes_valid_points(self) -> None:
        payload = {
            "observations": [
                {"date": "2024-01-02", "value": "4.27"},
                {"date": "2024-01-03", "value": "."},
                {"date": "2024-01-04", "value": "bad-value"},
                {"date": "2024-01-05", "value": "4.30"},
            ]
        }

        with patch("app.ingestion.fred_client._fred_get", return_value=payload):
            observations = fred_client.fetch_series_observations("DGS2")

        self.assertEqual(2, len(observations))
        self.assertTrue(all(isinstance(obs, Observation) for obs in observations))
        self.assertEqual(date(2024, 1, 2), observations[0].observation_date)
        self.assertEqual(4.27, observations[0].value)
        self.assertEqual(date(2024, 1, 5), observations[1].observation_date)
        self.assertEqual(4.30, observations[1].value)

    def test_store_observations_upserts_rows(self) -> None:
        metadata = {
            "name": "2-Year Treasury Constant Maturity Rate",
            "source": "fred",
            "source_series_id": "DGS2",
            "units": "Percent",
            "frequency": "Daily",
            "category": "treasury_rates",
        }
        initial = [
            Observation(series_id=0, observation_date=date(2024, 1, 2), value=4.27),
            Observation(series_id=0, observation_date=date(2024, 1, 3), value=4.31),
        ]

        with patch("app.ingestion.fred_client.fetch_series_metadata", return_value=metadata):
            changed_count = fred_client.store_observations("DGS2", initial)
        self.assertEqual(2, changed_count)

        with self.testing_session_local() as db:
            series = db.scalar(select(Series).where(Series.source_series_id == "DGS2"))
            self.assertIsNotNone(series)
            rows = db.scalars(
                select(Observation)
                .where(Observation.series_id == series.id)
                .order_by(Observation.observation_date.asc())
            ).all()
            self.assertEqual(2, len(rows))
            self.assertEqual(4.27, rows[0].value)
            self.assertEqual(4.31, rows[1].value)

        updated = [
            Observation(series_id=0, observation_date=date(2024, 1, 3), value=4.35),
            Observation(series_id=0, observation_date=date(2024, 1, 4), value=4.40),
        ]
        with patch("app.ingestion.fred_client.fetch_series_metadata", return_value=metadata):
            changed_count = fred_client.store_observations("DGS2", updated)
        self.assertEqual(2, changed_count)

        with self.testing_session_local() as db:
            series = db.scalar(select(Series).where(Series.source_series_id == "DGS2"))
            rows = db.scalars(
                select(Observation)
                .where(Observation.series_id == series.id)
                .order_by(Observation.observation_date.asc())
            ).all()
            self.assertEqual(3, len(rows))
            self.assertEqual(4.35, rows[1].value)
            self.assertEqual(4.40, rows[2].value)

