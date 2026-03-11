from datetime import date
from unittest import TestCase

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.models.event import Event
from app.models.observation import Observation
from app.models.series import Series


class TestInsightsEndpoint(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.testing_session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
            class_=Session,
        )

        def override_get_db():
            db = cls.testing_session_local()
            try:
                yield db
            finally:
                db.close()

        Base.metadata.create_all(bind=cls.engine)

        with cls.testing_session_local() as db:
            series_a = Series(
                name="Series A",
                source="fred",
                source_series_id="A_SERIES",
                units="%",
                frequency="D",
                category="test",
            )
            series_b = Series(
                name="Series B",
                source="fred",
                source_series_id="B_SERIES",
                units="%",
                frequency="D",
                category="test",
            )
            db.add_all([series_a, series_b])
            db.flush()

            db.add_all(
                [
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 1), value=1.0),
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 2), value=1.4),
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 3), value=1.1),
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 4), value=1.6),
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 5), value=1.55),
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 6), value=1.8),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 1), value=2.0),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 2), value=2.5),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 3), value=2.2),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 4), value=2.7),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 5), value=2.6),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 6), value=2.9),
                ]
            )
            db.add_all(
                [
                    Event(
                        event_date=date(2024, 1, 3),
                        title="Nonfarm Payroll Release",
                        summary="Employment Situation release",
                        category="labor",
                        source="fred_release_calendar",
                        importance_score=0.92,
                    ),
                    Event(
                        event_date=date(2024, 1, 4),
                        title="CPI Release",
                        summary="Inflation release",
                        category="inflation",
                        source="fred_release_calendar",
                        importance_score=0.9,
                    ),
                    Event(
                        event_date=date(2024, 1, 6),
                        title="FOMC Meeting",
                        summary="Scheduled meeting",
                        category="fomc",
                        source="federal_reserve_fomc_calendar",
                        importance_score=0.95,
                    ),
                ]
            )
            db.commit()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def test_insights_returns_analysis_payload(self) -> None:
        response = self.client.get(
            "/insights",
            params={
                "series_a": 1,
                "series_b": 2,
                "start": "2024-01-01",
                "end": "2024-01-06",
            },
        )
        self.assertEqual(200, response.status_code)

        payload = response.json()
        self.assertEqual(6, payload["aligned_points"])
        self.assertEqual(6, payload["series_a_points"])
        self.assertEqual(6, payload["series_b_points"])
        self.assertEqual(6, payload["overlap_points"])
        self.assertIsNotNone(payload["correlation"])
        self.assertGreater(len(payload["inflection_points"]), 0)
        self.assertGreater(len(payload["major_movements"]), 0)
        self.assertIn("largest one-step move", payload["narrative_summary"])

        has_event_association = any(
            movement["nearby_events"] for movement in payload["major_movements"]
        )
        self.assertTrue(has_event_association)

    def test_insights_returns_404_for_unknown_series(self) -> None:
        response = self.client.get("/insights", params={"series_a": 999, "series_b": 2})
        self.assertEqual(404, response.status_code)
        self.assertEqual("Series not found for series_a=999", response.json()["detail"])
