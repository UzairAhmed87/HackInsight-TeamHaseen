from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from pipeline import urban_unit

REAL_CONFIG = Path(__file__).resolve().parents[1] / "config" / "openaq_urban_unit_karachi.json"


def _hour(start: datetime, value: float | None, coverage: float = 100.0) -> dict:
    return {
        "value": value,
        "flagInfo": {"hasFlags": False},
        "parameter": {"name": "pm25", "units": "µg/m³"},
        "period": {
            "interval": "01:00:00",
            "datetimeFrom": {"utc": start.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "datetimeTo": {"utc": (start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")},
        },
        "coverage": {"percentCoverage": coverage},
    }


class UrbanUnitSourceTests(unittest.TestCase):
    """Synthetic software fixtures only; never emitted as project data."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        config = json.loads(REAL_CONFIG.read_text(encoding="utf-8"))
        config["window_start_utc"] = "2026-01-01T00:00:00Z"
        config["locations"] = config["locations"][:1]
        (self.root / "config").mkdir()
        (self.root / "config" / REAL_CONFIG.name).write_text(json.dumps(config), encoding="utf-8")
        self.sensor_dir = self.root / "data" / "raw" / config["source_id"] / f"sensor_{config['locations'][0]['sensor_id']}"
        self.sensor_dir.mkdir(parents=True)
        start = datetime(2026, 1, 1, 19, tzinfo=timezone.utc)  # 2026-01-02 00:00 local
        hours = [_hour(start + timedelta(hours=h), 40.0 + h) for h in range(18)]
        hours += [_hour(start + timedelta(hours=18 + h), 77.0) for h in range(6)]  # frozen for 6 hours
        hours += [_hour(start + timedelta(hours=30), 55.0, coverage=40.0)]
        hours += [_hour(start + timedelta(hours=31), 700.0)]
        self._write("2026-01.json", hours)
        self._write("2026-02.partial.json", [_hour(datetime(2026, 2, 1, 5, tzinfo=timezone.utc), 33.0)], partial=True)
        self.now = datetime(2026, 2, 1, 7, 30, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, name: str, records: list[dict], partial: bool = False) -> None:
        body = json.dumps({"pages": [], "results": records}).encode("utf-8")
        (self.sensor_dir / name).write_bytes(body)
        (self.sensor_dir / name.replace(".json", ".provenance.json")).write_text(
            json.dumps({"sha256": hashlib.sha256(body).hexdigest(), "record_count": len(records),
                        "request_url": "fixture", "fetched_at_utc": "2026-02-01T07:00:00Z", "partial_month": partial}),
            encoding="utf-8",
        )

    def _run(self) -> tuple[int, dict]:
        with patch.dict(os.environ, {"OPENAQ_API_KEY": ""}):
            return urban_unit.run_source_pipeline(self.root, run_id="fixture", now=self.now)

    def test_flags_stuck_low_coverage_and_extreme_values(self) -> None:
        code, report = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(
            report["quality_flag_counts"],
            {"extreme_value_review": 1, "low_hour_coverage": 1, "ok": 19, "stuck_value_review": 6},
        )
        self.assertEqual(report["counts"]["fills_applied"], 0)

    def test_daily_mean_excludes_stuck_and_low_coverage_hours(self) -> None:
        self._run()
        with (self.root / "data" / "processed" / "gold_urban_unit_karachi_sensor_daily.csv").open(encoding="utf-8") as f:
            daily = {row["local_date"]: row for row in csv.DictReader(f)}
        day = daily["2026-01-02"]
        self.assertEqual(day["valid_hours"], "18")
        self.assertAlmostEqual(float(day["pm25_daily_mean_ug_m3"]), sum(40.0 + h for h in range(18)) / 18, places=2)
        self.assertEqual(daily["2026-01-03"]["quality_flag"], "insufficient_valid_hours")

    def test_freshness_uses_latest_hour_from_partial_month(self) -> None:
        _, report = self._run()
        self.assertEqual(report["last_observation_utc"], "2026-02-01T06:00:00Z")
        self.assertEqual(report["latest_age_hours"], 1.5)
        self.assertEqual(report["checks"]["freshness"]["status"], "pass")

    def test_completed_month_is_never_overwritten_when_tampered(self) -> None:
        path = self.sensor_dir / "2026-01.json"
        path.write_bytes(path.read_bytes() + b" ")
        code, report = self._run()
        self.assertEqual(code, 1)
        self.assertIn("SHA-256", report["errors"][0])


if __name__ == "__main__":
    unittest.main()
