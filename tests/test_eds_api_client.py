"""Meaningful guard-rail tests for the P2.1 API client."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import requests

from src.eds_api_client import (
    ApiResponseError,
    BoundedEnergiDataClient,
    RequestSpec,
    ScopeViolation,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/research_config.yaml"


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.content = json.dumps(self._payload).encode()
        self.url = "https://api.energidataservice.dk/fake"

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.headers = {}
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return next(self.responses)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.client = BoundedEnergiDataClient(CONFIG)

    def test_rejects_holdout_before_network(self):
        spec = RequestSpec(
            "Elspotprices",
            "2024-06-30",
            "2024-07-02",
            {"PriceArea": ["DK1"]},
        )
        with self.assertRaisesRegex(ScopeViolation, "locked holdout"):
            self.client.validate_spec(spec)

    def test_rejects_non_dk1_filter(self):
        spec = RequestSpec(
            "Elspotprices",
            "2024-06-01",
            "2024-06-02",
            {"PriceArea": ["DK2"]},
        )
        with self.assertRaisesRegex(ScopeViolation, "DK1"):
            self.client.validate_spec(spec)

    def test_rejects_missing_area_filter(self):
        spec = RequestSpec("Forecasts_Hour", "2024-06-01", "2024-06-02")
        with self.assertRaisesRegex(ScopeViolation, "explicitly filter"):
            self.client.validate_spec(spec)

    def test_accepts_development_boundary(self):
        spec = RequestSpec(
            "Elspotprices",
            "2022-01-01",
            "2024-07-01",
            {"PriceArea": ["DK1"]},
        )
        self.client.validate_spec(spec)


class FailureHandlingTests(unittest.TestCase):
    def test_retries_429_then_succeeds(self):
        payload = {
            "total": 1,
            "records": [
                {
                    "HourUTC": "2024-06-14T22:00:00",
                    "HourDK": "2024-06-15T00:00:00",
                    "PriceArea": "DK1",
                }
            ],
        }
        session = FakeSession(
            [
                FakeResponse(429, headers={"Retry-After": "1"}),
                FakeResponse(200, payload),
            ]
        )
        waits = []
        client = BoundedEnergiDataClient(
            CONFIG,
            session=session,
            sleep=waits.append,
            max_attempts=2,
        )
        result = client.fetch(
            RequestSpec(
                "Elspotprices",
                "2024-06-15",
                "2024-06-16",
                {"PriceArea": ["DK1"]},
            )
        )
        self.assertEqual(result.attempts, 2)
        self.assertEqual(session.calls, 2)
        self.assertEqual(waits, [1.0])

    def test_rejects_truncated_payload(self):
        payload = {"total": 2, "records": [{"HourUTC": "2024-06-14T22:00:00"}]}
        session = FakeSession([FakeResponse(200, payload)])
        client = BoundedEnergiDataClient(CONFIG, session=session)
        with self.assertRaisesRegex(ApiResponseError, "total does not match"):
            client.fetch(
                RequestSpec(
                    "Elspotprices",
                    "2024-06-15",
                    "2024-06-16",
                    {"PriceArea": ["DK1"]},
                )
            )


if __name__ == "__main__":
    unittest.main()
