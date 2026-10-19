from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pipeline import run


class PipelineUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = {
            "source_id": "paqi_karachi_daily_pm25",
            "publisher": "Pakistan Air Quality Initiative (PAQI)",
            "title": "Unveiling Karachi",
            "version": "10.5281/zenodo.15845428",
            "metadata_url": "https://zenodo.example/metadata",
            "source_url": "https://doi.org/10.5281/zenodo.15845428",
            "download_url": "https://zenodo.example/data.csv",
            "filename": "sample.csv",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "expected_size_bytes": 10,
            "expected_md5": "0" * 32,
            "expected_zenodo_license_id": "cc-by-4.0",
            "expected_header": ["date", "pm25_concentration_ug_per_m3"],
            "city": "Karachi",
            "pollutant": "PM2.5",
            "unit": "µg/m³",
            "time_resolution": "daily_24h_average",
            "timezone": None,
            "attribution": "test attribution",
            "request_description": "test request",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_fixture(self, contents: str) -> Path:
        path = self.root / "fixture.csv"
        path.write_text(contents, encoding="utf-8", newline="")
        return path

    def test_hash_helpers_match_known_software_fixture(self) -> None:
        path = self.root / "hash_fixture.txt"
        path.write_bytes(b"software-test-fixture")
        self.assertEqual(
            run.sha256_file(path),
            hashlib.sha256(b"software-test-fixture").hexdigest(),
        )
        self.assertEqual(
            run.md5_file(path),
            hashlib.md5(b"software-test-fixture").hexdigest(),
        )

    def test_valid_cache_is_reused_and_corrupt_cache_is_preserved(self) -> None:
        previous_data_root = run.DATA_ROOT
        try:
            run.DATA_ROOT = self.root / "data"
            payload = b"cached-source"
            self.source["expected_size_bytes"] = len(payload)
            self.source["expected_md5"] = hashlib.md5(payload).hexdigest()
            raw_dir = (
                run.DATA_ROOT
                / "raw"
                / self.source["source_id"]
                / self.source["version"].replace("/", "_")
            )
            raw_dir.mkdir(parents=True)
            raw = raw_dir / self.source["filename"]
            raw.write_bytes(payload)
            sidecar = raw.with_suffix(raw.suffix + ".provenance.json")
            sidecar.write_text(
                json.dumps({"fetch_timestamp_utc": "2026-10-20T00:00:00Z"}),
                encoding="utf-8",
            )
            result = run.download_or_reuse(
                self.source, 1, {"checksum": f"md5:{self.source['expected_md5']}"}
            )
            self.assertEqual(result.acquisition_status, "reused_cached_file")
            self.assertEqual(result.sha256, hashlib.sha256(payload).hexdigest())
            raw.write_bytes(b"corrupted")
            with self.assertRaisesRegex(run.PipelineError, "preserved and not overwritten"):
                run.download_or_reuse(
                    self.source, 1, {"checksum": f"md5:{self.source['expected_md5']}"}
                )
            self.assertEqual(raw.read_bytes(), b"corrupted")
        finally:
            run.DATA_ROOT = previous_data_root

    def test_normalization_and_stable_gold_lineage(self) -> None:
        fixture = self.write_fixture(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-02,14.50\n"
            "2024-01-03,0\n"
        )
        source_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
        cleaned, rejected, stats = run.parse_and_clean(fixture, self.source, source_hash)
        gold_a = run.make_gold(cleaned, self.source["source_url"])
        gold_b = run.make_gold(cleaned, self.source["source_url"])
        self.assertEqual(rejected, [])
        self.assertEqual(stats["valid_record_count"], 2)
        self.assertEqual(cleaned[0]["value"], "14.5")
        self.assertEqual(cleaned[0]["unit"], "µg/m³")
        self.assertEqual(cleaned[0]["timezone"], "")
        self.assertEqual(gold_a, gold_b)
        self.assertEqual(len({row["row_id"] for row in gold_a}), 2)
        self.assertEqual(gold_a[0]["source_file_sha256"], source_hash)

    def test_bad_records_are_preserved_and_duplicate_dates_detected(self) -> None:
        fixture = self.write_fixture(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-02,10\n"
            "2024-01-02,11\n"
            "not-a-date,12\n"
            "2024-01-04,-1\n"
            "2024-01-05,NaN\n"
            "2024-01-06,\n"
            "2024-01-06\n"
        )
        cleaned, rejected, stats = run.parse_and_clean(
            fixture, self.source, hashlib.sha256(fixture.read_bytes()).hexdigest()
        )
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(len(rejected), 4)
        self.assertEqual(stats["duplicate_dates"], {"2024-01-02": 2})
        self.assertEqual(stats["missing_value_count"], 1)
        self.assertEqual(cleaned[-1]["quality_flag"], "missing_pm25_value")
        self.assertEqual(cleaned[-1]["value"], "")
        self.assertIn("invalid date", rejected[0]["rejection_reason"])
        self.assertEqual(rejected[-1]["raw_fields_json"], '["2024-01-06"]')

    def test_schema_mismatch_fails_explicitly(self) -> None:
        fixture = self.write_fixture("date,value\n2024-01-02,10\n")
        with self.assertRaisesRegex(run.PipelineError, "Unexpected CSV header"):
            run.parse_and_clean(fixture, self.source, "hash")

    def test_quality_report_fails_on_duplicates_and_invalid_measurements(self) -> None:
        fixture = self.write_fixture(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-02,10\n"
            "2024-01-02,11\n"
            "2024-01-03,-1\n"
        )
        file_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
        cleaned, rejected, stats = run.parse_and_clean(fixture, self.source, file_hash)
        report = run.calculate_quality(
            cleaned,
            rejected,
            stats,
            source=self.source,
            raw_sha256=file_hash,
            warning_days=30,
        )
        self.assertEqual(report["quality_status"], "failed")
        self.assertIn("date_uniqueness", report["critical_failures"])
        self.assertIn("nonnegative_finite_pm25", report["critical_failures"])

    def test_manifest_appends_auditable_rows(self) -> None:
        raw = self.root / "raw.csv"
        raw.write_text("fixture", encoding="utf-8")
        result = run.DownloadResult(
            raw_path=raw,
            sha256="a" * 64,
            md5="b" * 32,
            byte_size=7,
            fetched_at_utc="2026-10-20T00:00:00Z",
            http_status=200,
            acquisition_status="downloaded",
        )
        manifest = self.root / "manifest.csv"
        for run_id in ("r1", "r2"):
            run.append_manifest(
                manifest,
                run_id=run_id,
                source=self.source,
                result=result,
                metadata_url=self.source["metadata_url"],
                metadata_status=200,
            )
        with manifest.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["sha256"], "a" * 64)
        self.assertIn("GET https://zenodo.example/data.csv", rows[0]["request_query"])
        self.assertEqual(rows[1]["fetch_timestamp_utc"], result.fetched_at_utc)

    def test_pinned_metadata_rejects_unexpected_checksum(self) -> None:
        metadata = {
            "id": 15845428,
            "doi": self.source["version"],
            "metadata": {"license": {"id": "cc-by-4.0"}},
            "files": [
                {
                    "key": self.source["filename"],
                    "size": self.source["expected_size_bytes"],
                    "checksum": "md5:" + "f" * 32,
                }
            ],
        }
        with self.assertRaisesRegex(run.PipelineError, "checksum differs"):
            run.validate_metadata(self.source, metadata)

    def test_config_disallows_unapproved_source_enablement(self) -> None:
        config_path = self.root / "sources.json"
        config_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "request_timeout_seconds": 1,
                    "freshness_warning_days": 30,
                    "sources": [
                        {"source_id": "openaq_pakistan", "enabled": True}
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(run.PipelineError, "Only the reviewed"):
            run.load_config(config_path)

    def test_pipeline_records_source_availability_failure_and_exits_nonzero(self) -> None:
        config_path = self.root / "config" / "sources.json"
        config_path.parent.mkdir()
        config_path.write_bytes(run.CONFIG_PATH.read_bytes())
        with patch.object(
            run,
            "validate_source_availability",
            side_effect=run.PipelineError("fixture source unavailable"),
        ):
            exit_code, status = run.run_pipeline(self.root)
        self.assertEqual(exit_code, 1)
        self.assertEqual(status["status"], "failed")
        report = json.loads(
            (self.root / "data" / "reports" / "execution_status.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("fixture source unavailable", report["errors"][0])
        self.assertEqual(status["acquisition_status"], "metadata_check_pending")

    def test_empty_valid_csv_is_distinguished_from_acquisition_failure(self) -> None:
        config_path = self.root / "config" / "sources.json"
        config_path.parent.mkdir()
        config_path.write_bytes(run.CONFIG_PATH.read_bytes())
        raw_path = self.root / "empty.csv"
        raw_path.write_text(
            "date,pm25_concentration_ug_per_m3\n", encoding="utf-8"
        )
        cached_result = run.DownloadResult(
            raw_path=raw_path,
            sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            md5=hashlib.md5(raw_path.read_bytes()).hexdigest(),
            byte_size=raw_path.stat().st_size,
            fetched_at_utc="2026-10-20T00:00:00Z",
            http_status=200,
            acquisition_status="reused_cached_file",
        )
        with (
            patch.object(run, "validate_source_availability", return_value=({}, 200)),
            patch.object(run, "download_or_reuse", return_value=cached_result),
        ):
            exit_code, status = run.run_pipeline(self.root)
        self.assertEqual(exit_code, 1)
        self.assertEqual(status["acquisition_status"], "reused_cached_file")
        self.assertIn("contains no data records", status["errors"][0])


if __name__ == "__main__":
    unittest.main()
