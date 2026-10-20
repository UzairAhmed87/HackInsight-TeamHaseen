from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone

from pipeline import live_sensors


class _FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class LiveSensorTests(unittest.TestCase):
    def setUp(self) -> None:
        live_sensors.clear_cache()
        self.root = live_sensors.ROOT
        self.now = datetime(2026, 10, 20, 17, 30, tzinfo=timezone.utc)
        self._previous_live_flag = os.environ.pop("HACKINSIGHT_DISABLE_LIVE", None)

    def tearDown(self) -> None:
        if self._previous_live_flag is None:
            os.environ.pop("HACKINSIGHT_DISABLE_LIVE", None)
        else:
            os.environ["HACKINSIGHT_DISABLE_LIVE"] = self._previous_live_flag

    def test_fresh_reading_is_labelled_fresh(self) -> None:
        observed = self.now - timedelta(minutes=5)
        payload = {
            "locationId": 162753,
            "locationName": "Asif Gulistan-e-Johar",
            "publicLocationName": "Asif Gulistan-e-Johar",
            "latitude": 24.9,
            "longitude": 67.1,
            "offline": False,
            "pm01": 20.0,
            "pm02": 45.7,
            "pm10": 50.0,
            "pm003Count": 1000,
            "atmp": 33.0,
            "rhum": 40,
            "timestamp": observed.isoformat().replace("+00:00", "Z"),
            "publicContributorName": "The Urban Unit",
            "model": "O-1PST",
        }

        def opener(request, context=None, timeout=None):  # noqa: ANN001
            return _FakeResponse(payload)

        snapshot = live_sensors.fetch_live_snapshot(
            self.root, now=self.now, use_cache=False, opener=opener
        )
        self.assertEqual(snapshot["status"], "ok")
        primary = snapshot["primary_sensor"]
        self.assertEqual(primary["freshness"], "fresh")
        self.assertEqual(primary["pm25_ug_m3"], 45.7)
        self.assertIn("+05:00", primary["observation_time_pkt"] or "")

    def test_stale_reading_is_not_fresh(self) -> None:
        observed = self.now - timedelta(hours=8)
        payload = {
            "locationId": 162753,
            "locationName": "Asif Gulistan-e-Johar",
            "offline": False,
            "pm02": 40.0,
            "timestamp": observed.isoformat().replace("+00:00", "Z"),
        }

        def opener(request, context=None, timeout=None):  # noqa: ANN001
            return _FakeResponse(payload)

        snapshot = live_sensors.fetch_live_snapshot(
            self.root, now=self.now, use_cache=False, opener=opener
        )
        self.assertEqual(snapshot["primary_sensor"]["freshness"], "stale")

    def test_http_error_marks_unavailable_without_crash(self) -> None:
        def opener(request, context=None, timeout=None):  # noqa: ANN001
            raise urllib.error.HTTPError(
                url="https://example.test",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=io.BytesIO(b'{"error":"missing"}'),
            )

        snapshot = live_sensors.fetch_live_snapshot(
            self.root, now=self.now, use_cache=False, opener=opener
        )
        self.assertEqual(snapshot["status"], "unavailable")
        self.assertEqual(snapshot["available_pm25_sensor_count"], 0)
        self.assertTrue(all(row["freshness"] == "unavailable" for row in snapshot["sensors"]))

    def test_null_pm25_is_unavailable_even_if_online(self) -> None:
        payload = {
            "locationId": 162672,
            "locationName": "Aga Khan",
            "offline": False,
            "pm02": None,
            "atmp": 30.0,
            "timestamp": self.now.isoformat().replace("+00:00", "Z"),
        }

        def opener(request, context=None, timeout=None):  # noqa: ANN001
            return _FakeResponse(payload)

        snapshot = live_sensors.fetch_live_snapshot(
            self.root, now=self.now, use_cache=False, opener=opener
        )
        # All configured sensors receive the same mocked payload in this test helper
        # path only when opener ignores URL; freshness should be unavailable without PM2.5.
        self.assertTrue(all(row["freshness"] == "unavailable" for row in snapshot["sensors"]))


if __name__ == "__main__":
    unittest.main()
