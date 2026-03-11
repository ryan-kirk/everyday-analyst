from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.ingestion import bls_client
from app.ingestion.storage import store_series_observations
from app.models.observation import Observation
from app.models.series import Series


class TestBlsClient(TestCase):
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

    def test_fetch_series_observations_normalizes_monthly_data(self) -> None:
        payload = {
            "status": "REQUEST_SUCCEEDED",
            "Results": {
                "series": [
                    {
                        "seriesID": "LNS14000000",
                        "data": [
                            {"year": "2024", "period": "M03", "value": "3.9"},
                            {"year": "2024", "period": "M02", "value": "3.7"},
                            {"year": "2024", "period": "M13", "value": "3.8"},
                            {"year": "2024", "period": "M01", "value": "bad"},
                        ],
                    }
                ]
            },
        }

        with patch("app.ingestion.bls_client._bls_post", return_value=payload):
            observations = bls_client.fetch_series_observations("LNS14000000", 2024, 2024)

        self.assertEqual(2, len(observations))
        self.assertTrue(all(isinstance(obs, Observation) for obs in observations))
        self.assertEqual(date(2024, 2, 1), observations[0].observation_date)
        self.assertEqual(3.7, observations[0].value)
        self.assertEqual(date(2024, 3, 1), observations[1].observation_date)
        self.assertEqual(3.9, observations[1].value)

    def test_store_series_observations_for_bls(self) -> None:
        metadata = bls_client.fetch_series_metadata("LNS14000000")
        observations = [
            Observation(series_id=0, observation_date=date(2024, 1, 1), value=3.7),
            Observation(series_id=0, observation_date=date(2024, 2, 1), value=3.9),
        ]
        result = store_series_observations(metadata, observations)

        self.assertEqual(2, result["inserted"])
        self.assertEqual(0, result["updated"])

        with self.testing_session_local() as db:
            series = db.scalar(
                select(Series).where(
                    Series.source == "bls",
                    Series.source_series_id == "LNS14000000",
                )
            )
            self.assertIsNotNone(series)
            rows = db.scalars(
                select(Observation)
                .where(Observation.series_id == series.id)
                .order_by(Observation.observation_date.asc())
            ).all()
            self.assertEqual(2, len(rows))
            self.assertEqual(3.9, rows[1].value)

