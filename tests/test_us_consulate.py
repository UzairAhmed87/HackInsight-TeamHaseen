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

from pipeline import us_consulate, warehouse

REAL_CONFIG = Path(__file__).resolve().parents[1] / "config" / "openaq_us_consulate_karachi.json"


def _record(start: datetime, value: float | None, has_flags: bool = False) -> dict:
    end = start + timedelta(hours=1)
    return {
        "value": value,
        "flagInfo": {"hasFlags": has_flags},
        "parameter": {"id": 2, "name": "pm25", "units": "µg/m³", "displayName": None},
        "period": {
            "label": "raw",
            "interval": "01:00:00",
            "datetimeFrom": {"utc": start.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "datetimeTo": {"utc": end.strftime("%Y-%m-%dT%H:%M:%SZ")},
        },
    }


class UsConsulateSourceTests(unittest.TestCase):
    """Synthetic software fixtures only; never emitted as project data."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        config = json.loads(REAL_CONFIG.read_text(encoding="utf-8"))
        config["window_start_utc"] = "2020-01-01T00:00:00Z"
        config["window_end_utc"] = "2020-02-01T00:00:00Z"
        (self.root / "config").mkdir()
        (self.root / "config" / REAL_CONFIG.name).write_text(json.dumps(config), encoding="utf-8")
        self.raw_dir = self.root / "data" / "raw" / config["source_id"] / f"openaq_v3_sensor_{config['openaq_sensor_id']}"
        self.raw_dir.mkdir(parents=True)
        (self.raw_dir / "location.json").write_text(
            json.dumps({"results": [{"provider": {"name": "AirNow"}, "licenses": [{"name": "US Public Domain"}]}]}),
            encoding="utf-8",
        )
        (self.raw_dir / "flags.json").write_text("{}", encoding="utf-8")
        # 2020-01-01 local day = 2019-12-31T19:00Z .. 2020-01-01T19:00Z; fixture starts at 2020-01-01T00:00Z.
        start = datetime(2020, 1, 1, 19, tzinfo=timezone.utc)  # 2020-01-02 00:00 local
        records = [_record(start + timedelta(hours=h), 20.0 + h) for h in range(20)]
        records += [_record(start + timedelta(hours=20), None)]
        records += [_record(start + timedelta(hours=21), 985.0)]
        records += [_record(start + timedelta(hours=22), 640.0)]
        records += [_record(start + timedelta(hours=23), 30.0, has_flags=True)]
        later = datetime(2020, 1, 3, 19, tzinfo=timezone.utc)  # 2020-01-04 local: only 5 valid hours
        records += [_record(later + timedelta(hours=h), 50.0) for h in range(5)]
        self._write_month("2020-01", records)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_month(self, month: str, records: list[dict]) -> None:
        body = json.dumps({"pages": [], "results": records}).encode("utf-8")
        (self.raw_dir / f"{month}.json").write_bytes(body)
        (self.raw_dir / f"{month}.provenance.json").write_text(
            json.dumps({"sha256": hashlib.sha256(body).hexdigest(), "record_count": len(records),
                        "request_url": "fixture", "fetched_at_utc": "2020-02-01T00:00:00Z"}),
            encoding="utf-8",
        )

    def _run(self) -> tuple[int, dict]:
        with patch.dict(os.environ, {"OPENAQ_API_KEY": ""}):
            return us_consulate.run_source_pipeline(
                self.root, run_id="fixture", now=datetime(2020, 2, 1, tzinfo=timezone.utc)
            )

    def _read(self, name: str) -> list[dict[str, str]]:
        with (self.root / "data" / "processed" / name).open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def test_flags_each_value_class_without_imputation(self) -> None:
        code, report = self._run()
        self.assertEqual(code, 0)
        self.assertEqual(
            report["quality_flag_counts"],
            {"extreme_value_review": 1, "missing_source_value": 1, "ok": 25,
             "source_flag_window": 1, "suspected_instrument_error_code": 1},
        )
        hourly = self._read("gold_us_consulate_karachi_hourly.csv")
        missing = [row for row in hourly if row["quality_flag"] == "missing_source_value"]
        self.assertEqual([row["pm25_ug_m3"] for row in missing], [""])
        self.assertEqual(report["counts"]["fills_applied"], 0)

    def test_daily_mean_requires_18_valid_hours_and_excludes_error_code(self) -> None:
        self._run()
        daily = {row["local_date"]: row for row in self._read("gold_us_consulate_karachi_daily.csv")}
        full = daily["2020-01-02"]
        # 20 ok hours (20..39) + 640 (kept for review) + 30 (source flag window); 985 and null excluded.
        expected = (sum(20.0 + h for h in range(20)) + 640.0 + 30.0) / 22
        self.assertEqual(full["valid_hours"], "22")
        self.assertAlmostEqual(float(full["pm25_daily_mean_ug_m3"]), expected, places=2)
        sparse = daily["2020-01-04"]
        self.assertEqual(sparse["pm25_daily_mean_ug_m3"], "")
        self.assertEqual(sparse["quality_flag"], "insufficient_valid_hours")

    def test_tampered_raw_file_fails_without_overwriting(self) -> None:
        path = self.raw_dir / "2020-01.json"
        path.write_bytes(path.read_bytes() + b" ")
        code, report = self._run()
        self.assertEqual(code, 1)
        self.assertIn("SHA-256", report["errors"][0])
        self.assertTrue(path.read_bytes().endswith(b" "))

    def test_missing_key_and_uncached_month_fails_clearly(self) -> None:
        (self.raw_dir / "2020-01.json").unlink()
        (self.raw_dir / "2020-01.provenance.json").unlink()
        code, report = self._run()
        self.assertEqual(code, 1)
        self.assertIn("OPENAQ_API_KEY", report["errors"][0])


class PearsonTests(unittest.TestCase):
    def test_pearson_matches_known_values(self) -> None:
        self.assertAlmostEqual(warehouse._pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertAlmostEqual(warehouse._pearson([1, 2, 3, 4], [8, 6, 4, 2]), -1.0)
        self.assertIsNone(warehouse._pearson([1, 1, 1], [1, 2, 3]))


if __name__ == "__main__":
    unittest.main()
