from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.ingestion import event_client
from app.models.event import Event


class TestEventClient(TestCase):
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

    def test_fetch_release_dates_parses_and_filters(self) -> None:
        payload = {
            "release_dates": [
                {"release_id": 10, "date": "2024-01-12"},
                {"release_id": 10, "date": "bad-date"},
                {"release_id": 10, "date": "2024-02-13"},
                {"release_id": 10, "date": "2024-03-12"},
            ]
        }
        with patch("app.ingestion.event_client._fred_get", return_value=payload):
            dates = event_client.fetch_release_dates(
                release_id=10,
                start=date(2024, 2, 1),
                end=date(2024, 3, 1),
            )
        self.assertEqual([date(2024, 2, 13)], dates)

    def test_fetch_fomc_meeting_dates_parses_calendar_html(self) -> None:
        html = """
        <a id="1">2026 FOMC Meetings</a>
        <div class="row fomc-meeting">
          <div class="fomc-meeting__month"><strong>January</strong></div>
          <div class="fomc-meeting__date">27-28</div>
        </div>
        <div class="row fomc-meeting">
          <div class="fomc-meeting__month"><strong>March</strong></div>
          <div class="fomc-meeting__date">17-18</div>
        </div>
        """
        with patch("app.ingestion.event_client.request_text_with_retry", return_value=html):
            dates = event_client.fetch_fomc_meeting_dates(
                start=date(2026, 2, 1),
                end=date(2026, 12, 31),
            )
        self.assertEqual([date(2026, 3, 17)], dates)

    def test_ingest_events_stores_expected_categories(self) -> None:
        mock_dates = {
            10: [date(2024, 2, 13)],
            50: [date(2024, 2, 2)],
            53: [date(2024, 2, 28)],
        }

        with patch("app.ingestion.event_client._remove_legacy_fomc_events", return_value=0):
            with patch("app.ingestion.event_client.fetch_fomc_meeting_dates", return_value=[date(2024, 1, 31)]):
                with patch(
                    "app.ingestion.event_client.fetch_release_dates",
                    side_effect=lambda release_id, start=None, end=None: mock_dates.get(release_id, []),
                ):
                    result = event_client.ingest_events()

        self.assertEqual(4, result["fetched"])
        self.assertEqual(4, result["inserted"])
        self.assertEqual(0, result["updated"])

        with self.testing_session_local() as db:
            rows = db.scalars(select(Event).order_by(Event.event_date.asc())).all()
            self.assertEqual(4, len(rows))
            categories = {row.category for row in rows}
            self.assertEqual({"fomc", "inflation", "labor", "growth"}, categories)
