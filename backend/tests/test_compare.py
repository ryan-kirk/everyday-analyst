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


class TestCompareEndpoint(TestCase):
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
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 2), value=1.2),
                    Observation(series_id=series_a.id, observation_date=date(2024, 1, 3), value=1.3),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 1), value=2.0),
                    Observation(series_id=series_b.id, observation_date=date(2024, 1, 3), value=2.3),
                ]
            )
            db.add_all(
                [
                    Event(
                        event_date=date(2024, 1, 1),
                        title="FOMC Meeting",
                        summary="Scheduled FOMC meeting",
                        category="fomc",
                        source="federal_reserve_fomc_calendar",
                        importance_score=0.95,
                    ),
                    Event(
                        event_date=date(2024, 1, 2),
                        title="Nonfarm Payroll Release",
                        summary="Employment Situation release",
                        category="labor",
                        source="fred_release_calendar",
                        importance_score=0.92,
                    ),
                    Event(
                        event_date=date(2024, 1, 3),
                        title="CPI Release",
                        summary="Consumer price index release",
                        category="inflation",
                        source="fred_release_calendar",
                        importance_score=0.9,
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

    def test_compare_aligns_using_union_of_dates(self) -> None:
        response = self.client.get(
            "/compare",
            params={
                "series_a": 1,
                "series_b": 2,
                "start": "2024-01-01",
                "end": "2024-01-03",
            },
        )
        self.assertEqual(200, response.status_code)

        payload = response.json()
        self.assertEqual(1, payload["series_a"]["id"])
        self.assertEqual(2, payload["series_b"]["id"])
        self.assertEqual(
            [
                {"date": "2024-01-01", "value_a": 1.0, "value_b": 2.0},
                {"date": "2024-01-02", "value_a": 1.2, "value_b": None},
                {"date": "2024-01-03", "value_a": 1.3, "value_b": 2.3},
            ],
            payload["observations"],
        )
        self.assertEqual(3, len(payload["events"]))
        self.assertEqual("FOMC Meeting", payload["events"][0]["title"])
        self.assertEqual("2024-01-01", payload["events"][0]["event_date"])

    def test_compare_returns_points_when_only_one_series_has_values(self) -> None:
        response = self.client.get(
            "/compare",
            params={
                "series_a": 1,
                "series_b": 2,
                "start": "2024-01-02",
                "end": "2024-01-02",
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [{"date": "2024-01-02", "value_a": 1.2, "value_b": None}],
            response.json()["observations"],
        )

    def test_compare_returns_404_for_unknown_series(self) -> None:
        response = self.client.get("/compare", params={"series_a": 999, "series_b": 2})
        self.assertEqual(404, response.status_code)
        self.assertEqual("Series not found for series_a=999", response.json()["detail"])

    def test_compare_filters_events_by_category(self) -> None:
        response = self.client.get(
            "/compare",
            params={
                "series_a": 1,
                "series_b": 2,
                "start": "2024-01-01",
                "end": "2024-01-03",
                "event_category": "labor",
            },
        )
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, len(payload["events"]))
        self.assertEqual("labor", payload["events"][0]["category"])
