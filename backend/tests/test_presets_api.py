from unittest import TestCase

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.database import get_db
from app.main import app


class TestPresetsEndpoint(TestCase):
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
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def test_presets_endpoint_returns_default_templates(self) -> None:
        response = self.client.get("/presets")
        self.assertEqual(200, response.status_code)
        payload = response.json()

        self.assertGreaterEqual(len(payload), 5)
        names = {item["name"] for item in payload}
        self.assertIn("Fed Watch", names)
        self.assertIn("Inflation vs Rates", names)
        self.assertIn("Housing vs Mortgage Rates", names)
        self.assertIn("Labor Market vs Rates", names)

        first = payload[0]
        self.assertIn("series_a", first)
        self.assertIn("series_b", first)
        self.assertIn("recommended_date_range", first)
        self.assertIn("description", first)
