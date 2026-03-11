from unittest import TestCase

from app.main import app
from fastapi.testclient import TestClient


class TestHealth(TestCase):
    def test_health(self) -> None:
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ok"}, response.json())
