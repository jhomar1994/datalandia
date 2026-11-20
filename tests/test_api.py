"""Contrato HTTP: validación antes de consultar y errores sin datos inventados."""
import unittest

from fastapi.testclient import TestClient

from api.app.main import create_app
from api.app.repository import DataUnavailable


class FakeRepository:
    def __init__(self):
        self.calls = 0

    def metrics(self, *args):
        self.calls += 1
        return {"zone_id": args[0], "mobility": {"trips": 3}}

    def zones(self):
        return [{"zone_id": "DL-132"}]

    def quality(self):
        raise DataUnavailable("Los indicadores no están disponibles temporalmente")

    def event(self, event_id):
        if event_id == "conflict":
            return {"variants": 2, "event": {"value": 1}}
        return {"variants": 0, "event": None}


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepository()
        self.client = TestClient(create_app(repository=self.repo))

    def test_valid_metrics_and_static_consumer(self):
        self.assertEqual(self.client.get("/api/metrics").json()["mobility"]["trips"], 3)
        self.assertIn("Monitoreo operativo", self.client.get("/").text)
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.repo.calls, 1)

    def test_invalid_parameters_never_reach_bigquery(self):
        for params in [
            {"zone": "DL-132' OR true"}, {"zone": "DL-999"}, {"limit": "201"},
            {"start": "2024-01-01T00:00:00"},
            {"start": "2024-02-01T00:00:00Z", "end": "2024-01-01T00:00:00Z"},
            {"start": "2024-01-01T00:00:00Z", "end": "2024-03-01T00:00:00Z"},
        ]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/api/metrics", params=params).status_code, 422)
        self.assertEqual(self.repo.calls, 0)

    def test_missing_conflicting_and_unavailable_are_explicit(self):
        self.assertEqual(self.client.get("/api/events/missing").status_code, 404)
        self.assertEqual(self.client.get("/api/events/conflict").status_code, 409)
        self.assertEqual(self.client.get("/api/events/bad.id").status_code, 422)
        self.assertEqual(self.client.get("/api/quality").status_code, 503)


if __name__ == "__main__":
    unittest.main()
