from __future__ import annotations

from unittest import TestCase

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.models.series import Series


class TestWorkspaceAPI(TestCase):
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
                    Series(
                        name="2-Year Treasury Yield",
                        source="fred",
                        source_series_id="DGS2",
                        units="Percent",
                        frequency="D",
                        category="rates",
                    ),
                    Series(
                        name="Unemployment Rate",
                        source="fred",
                        source_series_id="UNRATE",
                        units="Percent",
                        frequency="M",
                        category="labor",
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

    def test_workspace_flow_save_bookmark_notes_and_share(self) -> None:
        create_user_response = self.client.post(
            "/workspace/users",
            json={
                "username": "analyst_one",
                "password": "StrongPass123",
                "name": "Analyst One",
                "email": "analyst1@example.com",
            },
        )
        self.assertEqual(201, create_user_response.status_code)
        user_payload = create_user_response.json()
        user_id = user_payload["id"]

        login_response = self.client.post(
            "/workspace/auth/login",
            json={"username": "analyst_one", "password": "StrongPass123"},
        )
        self.assertEqual(200, login_response.status_code)
        self.assertEqual(user_id, login_response.json()["id"])

        create_saved_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses",
            json={
                "title": "Rates vs Labor",
                "description": "Track labor context against short rates.",
                "series_a_id": 1,
                "series_b_id": 2,
                "start_date": "2025-01-01",
                "end_date": "2026-01-01",
                "event_category_filter": "labor,fomc",
                "is_bookmarked": True,
                "share_include_notes": False,
            },
        )
        self.assertEqual(201, create_saved_response.status_code)
        saved_payload = create_saved_response.json()
        analysis_id = saved_payload["id"]
        share_token = saved_payload["share_token"]
        self.assertTrue(saved_payload["is_bookmarked"])
        self.assertFalse(saved_payload["share_include_notes"])
        self.assertEqual(
            f"/workspace/shared/{share_token}",
            saved_payload["share_path"],
        )
        self.assertEqual("2-Year Treasury Yield", saved_payload["series_a"]["name"])
        self.assertEqual("Unemployment Rate", saved_payload["series_b"]["name"])

        list_saved_response = self.client.get(f"/workspace/users/{user_id}/saved-analyses")
        self.assertEqual(200, list_saved_response.status_code)
        listed = list_saved_response.json()
        self.assertEqual(1, len(listed))

        bookmark_update_response = self.client.patch(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/bookmark",
            json={"is_bookmarked": False},
        )
        self.assertEqual(200, bookmark_update_response.status_code)
        self.assertFalse(bookmark_update_response.json()["is_bookmarked"])

        bookmarked_only_response = self.client.get(
            f"/workspace/users/{user_id}/saved-analyses",
            params={"bookmarked_only": "true"},
        )
        self.assertEqual(200, bookmarked_only_response.status_code)
        self.assertEqual([], bookmarked_only_response.json())

        create_note_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes",
            json={"note_text": "Labor releases were close to recent turning points."},
        )
        self.assertEqual(201, create_note_response.status_code)
        note_payload = create_note_response.json()
        self.assertEqual(analysis_id, note_payload["saved_analysis_id"])

        list_notes_response = self.client.get(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes"
        )
        self.assertEqual(200, list_notes_response.status_code)
        notes_payload = list_notes_response.json()
        self.assertEqual(1, len(notes_payload))
        self.assertIn("turning points", notes_payload[0]["note_text"])

        shared_response = self.client.get(f"/workspace/shared/{share_token}")
        self.assertEqual(200, shared_response.status_code)
        shared_payload = shared_response.json()
        self.assertEqual(analysis_id, shared_payload["saved_analysis"]["id"])
        self.assertFalse(shared_payload["notes_shared"])
        self.assertEqual([], shared_payload["notes"])

        enable_note_sharing_response = self.client.patch(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/share-settings",
            json={"share_include_notes": True},
        )
        self.assertEqual(200, enable_note_sharing_response.status_code)
        self.assertTrue(enable_note_sharing_response.json()["share_include_notes"])

        shared_with_notes_response = self.client.get(f"/workspace/shared/{share_token}")
        self.assertEqual(200, shared_with_notes_response.status_code)
        shared_with_notes_payload = shared_with_notes_response.json()
        self.assertTrue(shared_with_notes_payload["notes_shared"])
        self.assertEqual(1, len(shared_with_notes_payload["notes"]))

        delete_note_response = self.client.delete(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes/{note_payload['id']}"
        )
        self.assertEqual(204, delete_note_response.status_code)

        notes_after_delete_response = self.client.get(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes"
        )
        self.assertEqual(200, notes_after_delete_response.status_code)
        self.assertEqual([], notes_after_delete_response.json())

        shared_after_delete_response = self.client.get(f"/workspace/shared/{share_token}")
        self.assertEqual(200, shared_after_delete_response.status_code)
        self.assertTrue(shared_after_delete_response.json()["notes_shared"])
        self.assertEqual(0, len(shared_after_delete_response.json()["notes"]))

    def test_saved_analysis_requires_valid_series_and_dates(self) -> None:
        create_user_response = self.client.post(
            "/workspace/users",
            json={
                "username": "analyst_two",
                "password": "StrongPass123",
                "name": "Analyst Two",
                "email": "analyst2@example.com",
            },
        )
        self.assertEqual(201, create_user_response.status_code)
        user_id = create_user_response.json()["id"]

        bad_date_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses",
            json={
                "title": "Invalid range",
                "series_a_id": 1,
                "series_b_id": 2,
                "start_date": "2026-01-01",
                "end_date": "2025-01-01",
            },
        )
        self.assertEqual(400, bad_date_response.status_code)
        self.assertEqual("start_date must be <= end_date", bad_date_response.json()["detail"])

        missing_series_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses",
            json={
                "title": "Missing series",
                "series_a_id": 999,
                "series_b_id": 2,
            },
        )
        self.assertEqual(404, missing_series_response.status_code)
        self.assertEqual(
            "series not found for series_a_id=999",
            missing_series_response.json()["detail"],
        )

    def test_shared_analysis_not_found(self) -> None:
        response = self.client.get("/workspace/shared/does-not-exist")
        self.assertEqual(404, response.status_code)
        self.assertEqual("shared analysis not found", response.json()["detail"])

    def test_login_requires_valid_credentials(self) -> None:
        self.client.post(
            "/workspace/users",
            json={
                "username": "login_user",
                "password": "StrongPass123",
                "name": "Login User",
            },
        )

        bad_password_response = self.client.post(
            "/workspace/auth/login",
            json={"username": "login_user", "password": "wrong-password"},
        )
        self.assertEqual(401, bad_password_response.status_code)
        self.assertEqual(
            "invalid username or password",
            bad_password_response.json()["detail"],
        )

    def test_saving_same_title_updates_existing_analysis_and_keeps_notes(self) -> None:
        create_user_response = self.client.post(
            "/workspace/users",
            json={
                "username": "dedupe_user",
                "password": "StrongPass123",
                "name": "Dedupe User",
            },
        )
        self.assertEqual(201, create_user_response.status_code)
        user_id = create_user_response.json()["id"]

        first_save_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses",
            json={
                "title": "Rates Notebook",
                "description": "first",
                "series_a_id": 1,
                "series_b_id": 2,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "event_category_filter": "fomc",
            },
        )
        self.assertEqual(201, first_save_response.status_code)
        first_saved = first_save_response.json()
        analysis_id = first_saved["id"]

        note_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes",
            json={"note_text": "Keep this note after view update."},
        )
        self.assertEqual(201, note_response.status_code)

        second_save_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses",
            json={
                "title": "rates notebook",
                "description": "updated",
                "series_a_id": 2,
                "series_b_id": 1,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "event_category_filter": "labor",
                "is_bookmarked": True,
            },
        )
        self.assertEqual(201, second_save_response.status_code)
        second_saved = second_save_response.json()

        self.assertEqual(analysis_id, second_saved["id"])
        self.assertEqual("rates notebook", second_saved["title"])
        self.assertTrue(second_saved["is_bookmarked"])
        self.assertEqual(2, second_saved["series_a_id"])
        self.assertEqual(1, second_saved["series_b_id"])
        self.assertEqual("labor", second_saved["event_category_filter"])

        list_saved_response = self.client.get(f"/workspace/users/{user_id}/saved-analyses")
        self.assertEqual(200, list_saved_response.status_code)
        listed = list_saved_response.json()
        self.assertEqual(1, len(listed))
        self.assertEqual(analysis_id, listed[0]["id"])

        list_notes_response = self.client.get(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes"
        )
        self.assertEqual(200, list_notes_response.status_code)
        notes = list_notes_response.json()
        self.assertEqual(1, len(notes))
        self.assertIn("Keep this note", notes[0]["note_text"])

    def test_delete_saved_analysis_removes_view_and_associated_notes(self) -> None:
        create_user_response = self.client.post(
            "/workspace/users",
            json={
                "username": "delete_view_user",
                "password": "StrongPass123",
                "name": "Delete View User",
            },
        )
        self.assertEqual(201, create_user_response.status_code)
        user_id = create_user_response.json()["id"]

        save_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses",
            json={
                "title": "Delete Me",
                "series_a_id": 1,
                "series_b_id": 2,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
            },
        )
        self.assertEqual(201, save_response.status_code)
        analysis_id = save_response.json()["id"]

        note_response = self.client.post(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes",
            json={"note_text": "This note should be deleted with the analysis."},
        )
        self.assertEqual(201, note_response.status_code)

        delete_response = self.client.delete(f"/workspace/users/{user_id}/saved-analyses/{analysis_id}")
        self.assertEqual(204, delete_response.status_code)

        list_saved_response = self.client.get(f"/workspace/users/{user_id}/saved-analyses")
        self.assertEqual(200, list_saved_response.status_code)
        self.assertEqual([], list_saved_response.json())

        notes_response = self.client.get(
            f"/workspace/users/{user_id}/saved-analyses/{analysis_id}/notes"
        )
        self.assertEqual(404, notes_response.status_code)
