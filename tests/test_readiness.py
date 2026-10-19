from __future__ import annotations

import csv
import hashlib
import statistics
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from pipeline import readiness, run


class ReadinessAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = {
            "source_id": "paqi_karachi_daily_pm25",
            "publisher": "PAQI",
            "version": "10.5281/zenodo.15845428",
            "source_url": "https://doi.org/10.5281/zenodo.15845428",
            "filename": "fixture.csv",
            "expected_header": ["date", "pm25_concentration_ug_per_m3"],
            "city": "Karachi",
            "pollutant": "PM2.5",
            "unit": "µg/m³",
            "time_resolution": "daily_24h_average",
            "timezone": None,
        }
        self.raw_path = self.root / "raw.csv"
        with self.raw_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(self.source["expected_header"])
            first_date = date(2024, 1, 1)
            for index in range(10):
                value = "" if index == 4 else ("10.0" if index == 1 else f"{10 + index}.0")
                writer.writerow(
                    [(first_date + timedelta(days=index)).isoformat(), value]
                )
        self.clean_path = self.root / "cleaned.csv"
        self.gold_path = self.root / "gold.csv"
        file_hash = hashlib.sha256(self.raw_path.read_bytes()).hexdigest()
        cleaned, rejected, _ = run.parse_and_clean(
            self.raw_path, self.source, file_hash
        )
        self.assertEqual(rejected, [])
        gold = run.make_gold(cleaned, self.source["source_url"])
        run.atomic_csv(self.clean_path, run.CLEAN_FIELDS, cleaned)
        run.atomic_csv(self.gold_path, run.GOLD_FIELDS, gold)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_audit_reports_stats_date_gaps_and_chronological_splits(self) -> None:
        result = readiness.audit_warehouse_layers(
            self.raw_path, self.clean_path, self.gold_path
        )
        self.assertEqual(result["row_count"], 10)
        self.assertEqual(result["numeric_count"], 9)
        self.assertEqual(result["missing_value_count"], 1)
        self.assertEqual(result["missing_dates_within_observed_span"], [])
        self.assertEqual(result["numeric_statistics_ug_m3"]["minimum"], 10.0)
        self.assertEqual(result["numeric_statistics_ug_m3"]["maximum"], 19.0)
        fixture_values = [10.0, 10.0, 12.0, 13.0, 15.0, 16.0, 17.0, 18.0, 19.0]
        self.assertEqual(
            result["numeric_statistics_ug_m3"]["mean"],
            statistics.mean(fixture_values),
        )
        self.assertEqual(
            result["numeric_statistics_ug_m3"]["median"],
            statistics.median(fixture_values),
        )
        self.assertEqual(
            result["numeric_statistics_ug_m3"]["standard_deviation_sample"],
            statistics.stdev(fixture_values),
        )
        self.assertEqual(result["value_repetition"]["distinct_numeric_values"], 8)
        self.assertEqual(result["value_repetition"]["numeric_rows_with_a_repeated_magnitude"], 2)
        self.assertEqual(result["value_repetition"]["longest_consecutive_identical_value_run"], 2)
        self.assertEqual(result["splits_by_chronological_row_position"]["test"]["start_date"], "2024-01-09")
        self.assertTrue(result["lineage"]["all_gold_row_ids_recomputed_and_matched"])

    def test_audit_fails_if_gold_value_does_not_preserve_source(self) -> None:
        with self.gold_path.open(encoding="utf-8", newline="") as stream:
            records = list(csv.DictReader(stream))
        records[0]["source_value_raw"] = "999"
        run.atomic_csv(self.gold_path, run.GOLD_FIELDS, records)
        with self.assertRaisesRegex(readiness.ReadinessAuditError, "lineage fields differ"):
            readiness.audit_warehouse_layers(
                self.raw_path, self.clean_path, self.gold_path
            )


if __name__ == "__main__":
    unittest.main()
