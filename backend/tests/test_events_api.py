from __future__ import annotations

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


class TestEventsEndpoint(TestCase):
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
            db.add_all(
                [
                    Event(
                        event_date=date(2024, 1, 31),
                        title="FOMC Meeting",
                        summary="FOMC release",
                        category="fomc",
                        source="fred_release_calendar",
                        importance_score=0.95,
                    ),
                    Event(
                        event_date=date(2024, 2, 2),
                        title="Nonfarm Payroll Release",
                        summary="Employment Situation",
                        category="labor",
                        source="fred_release_calendar",
                        importance_score=0.92,
                    ),
                    Event(
                        event_date=date(2024, 2, 13),
                        title="CPI Release",
                        summary="CPI release",
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

    def test_events_endpoint_filters_by_date_range(self) -> None:
        response = self.client.get("/events", params={"start": "2024-02-01", "end": "2024-02-10"})
        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual(1, len(payload))
        self.assertEqual("Nonfarm Payroll Release", payload[0]["title"])
        self.assertEqual("2024-02-02", payload[0]["event_date"])

