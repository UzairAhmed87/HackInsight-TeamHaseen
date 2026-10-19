from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pipeline import data_quality_agent as agent, run


class DataQualityAgentTests(unittest.TestCase):
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
            "license": "CC BY 4.0",
            "attribution": "test attribution",
        }
        self.raw_path = self.root / "raw.csv"
        self.cleaned_path = self.root / "cleaned.csv"
        self.gold_path = self.root / "gold.csv"
        self.rejected_path = self.root / "rejected.csv"
        self.quality_path = self.root / "quality.json"
        self.manifest_path = self.root / "manifest.csv"
        self.now = datetime(2024, 1, 10, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self, raw_text: str) -> tuple[dict, list[dict[str, str]]]:
        self.raw_path.write_text(raw_text, encoding="utf-8", newline="")
        raw_hash = hashlib.sha256(self.raw_path.read_bytes()).hexdigest()
        cleaned, rejected, stats = run.parse_and_clean(
            self.raw_path, self.source, raw_hash
        )
        gold = run.make_gold(cleaned, self.source["source_url"])
        run.atomic_csv(self.cleaned_path, run.CLEAN_FIELDS, cleaned)
        run.atomic_csv(self.gold_path, run.GOLD_FIELDS, gold)
        run.atomic_csv(
            self.rejected_path,
            ["source_record_key", "raw_fields_json", "rejection_reason"],
            rejected,
        )
        quality = run.calculate_quality(
            cleaned,
            rejected,
            stats,
            source=self.source,
            raw_sha256=raw_hash,
            warning_days=30,
        )
        self.quality_path.write_text("{}", encoding="utf-8")
        with self.manifest_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["source_id", "sha256", "fetch_timestamp_utc"])
            writer.writeheader()
            writer.writerow(
                {
                    "source_id": self.source["source_id"],
                    "sha256": raw_hash,
                    "fetch_timestamp_utc": "2024-01-09T00:00:00Z",
                }
            )
        return quality, cleaned

    def audit(self, quality: dict):
        return agent.audit_data_quality(
            raw_path=self.raw_path,
            cleaned_path=self.cleaned_path,
            gold_path=self.gold_path,
            rejected_path=self.rejected_path,
            base_quality=quality,
            source=self.source,
            warning_days=30,
            manifest_path=self.manifest_path,
            run_id="fixture-run",
            now=self.now,
        )

    def test_missing_value_is_not_filled_and_is_flagged(self) -> None:
        quality, cleaned = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,10.0\n"
            "2024-01-02,\n"
            "2024-01-03,12.0\n"
        )
        report, issues = self.audit(quality)
        missing = [row for row in issues if row["observed_date"] == "2024-01-02"]
        self.assertTrue(
            any(row["decision"] == "FILL" and row["action_taken"] == "not_applied" for row in missing)
        )
        self.assertTrue(any(row["decision"] == "FLAG" for row in missing))
        self.assertEqual(report["counts"]["fills_applied"], 0)
        self.assertEqual(report["counts"]["fills_not_applied"], 1)
        self.assertEqual(cleaned[1]["value"], "")
        self.assertEqual(report["status"], "success_with_warnings")

    def test_duplicate_dates_are_flagged_without_deduplication(self) -> None:
        quality, cleaned = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,10\n"
            "2024-01-01,11\n"
        )
        report, issues = self.audit(quality)
        duplicate_issues = [row for row in issues if row["issue"] == "duplicate_observation_date"]
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(duplicate_issues), 2)
        self.assertEqual(report["checks"]["duplicate_dates"]["status"], "fail")
        self.assertEqual(report["status"], "failure")

    def test_calendar_gap_is_flagged_not_filled(self) -> None:
        quality, _ = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,10\n"
            "2024-01-03,12\n"
        )
        report, issues = self.audit(quality)
        gap = [row for row in issues if row["issue"] == "missing_calendar_date"]
        self.assertEqual(len(gap), 1)
        self.assertEqual(gap[0]["observed_date"], "2024-01-02")
        self.assertEqual(gap[0]["decision"], "FLAG")
        self.assertEqual(gap[0]["action_taken"], "not_filled")
        self.assertEqual(report["checks"]["date_continuity"]["status"], "warning")

    def test_negative_and_nonfinite_values_are_logged_as_rejected_flags(self) -> None:
        quality, _ = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,-2\n"
            "2024-01-02,NaN\n"
            "2024-01-03,Infinity\n"
        )
        report, issues = self.audit(quality)
        invalid = [row for row in issues if row["issue"] == "invalid_pm25_value"]
        self.assertEqual(len(invalid), 3)
        self.assertTrue(all(row["decision"] == "FLAG" for row in invalid))
        self.assertTrue(all(row["source_row_id"] for row in invalid))
        self.assertEqual(report["checks"]["nonnegative_finite_pm25"]["status"], "fail")

    def test_safe_numeric_normalization_is_audited_and_original_preserved(self) -> None:
        quality, cleaned = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,01.500\n"
            "2024-01-02,2\n"
        )
        report, issues = self.audit(quality)
        fix = next(row for row in issues if row["decision"] == "FIX")
        self.assertEqual(fix["issue"], "numeric_representation_normalized")
        self.assertEqual(fix["action_taken"], "normalized_numeric_value; exact_source_value_preserved")
        self.assertEqual(cleaned[0]["source_value_raw"], "01.500")
        self.assertEqual(cleaned[0]["value"], "1.5")
        self.assertEqual(report["counts"]["fixes"], 1)

    def test_whitespace_and_numeric_forms_are_normalized_without_loss(self) -> None:
        quality, cleaned = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01, 10.0 \n"
            "2024-01-02,11\n"
            "2024-01-03,12.50\n"
            "2024-01-04,9007199254740993.125\n"
            "2024-01-05,9007199254740993.123456789012345678901234567890123\n"
        )
        report, issues = self.audit(quality)
        fixes = [row for row in issues if row["decision"] == "FIX"]
        self.assertEqual(
            [(row["source_value_raw"], row["value"]) for row in cleaned],
            [
                (" 10.0 ", "10"),
                ("11", "11"),
                ("12.50", "12.5"),
                ("9007199254740993.125", "9007199254740993.125"),
                (
                    "9007199254740993.123456789012345678901234567890123",
                    "9007199254740993.123456789012345678901234567890123",
                ),
            ],
        )
        self.assertEqual(len(fixes), 2)
        self.assertEqual(report["counts"]["fixes"], 2)

    def test_malformed_numeric_text_is_rejected_and_flagged(self) -> None:
        quality, cleaned = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,10\n"
            "2024-01-02,not-a-reading\n"
        )
        report, issues = self.audit(quality)
        invalid = [row for row in issues if row["issue"] == "invalid_pm25_value"]
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid[0]["decision"], "FLAG")
        self.assertEqual(report["status"], "failure")

    def test_lineage_mismatch_fails_without_silent_repair(self) -> None:
        quality, _ = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,10\n"
            "2024-01-02,11\n"
        )
        with self.gold_path.open(encoding="utf-8", newline="") as stream:
            gold = list(csv.DictReader(stream))
        gold[0]["value"] = "999"
        run.atomic_csv(self.gold_path, run.GOLD_FIELDS, gold)
        report, issues = self.audit(quality)
        lineage = [row for row in issues if row["issue"] == "raw_cleaned_gold_lineage_mismatch"]
        self.assertEqual(report["checks"]["raw_cleaned_gold_lineage"]["status"], "fail")
        self.assertEqual(len(lineage), 1)
        self.assertEqual(lineage[0]["decision"], "FLAG")
        self.assertIn("no lineage repair", lineage[0]["action_taken"])
        self.assertEqual(gold[0]["value"], "999")

    def test_stale_source_is_a_source_level_warning(self) -> None:
        quality, _ = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2020-01-01,10\n"
        )
        report, issues = self.audit(quality)
        stale = [row for row in issues if row["issue"] == "stale_source_observations"]
        self.assertEqual(report["checks"]["source_freshness"]["status"], "warning")
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["source_row_id"], "")
        self.assertEqual(stale[0]["decision"], "FLAG")

    def test_schema_change_fails_without_reinterpreting_source(self) -> None:
        self.raw_path.write_text(
            "date,pm25_concentration_ug_per_m3,station\n2024-01-01,10,site-a\n",
            encoding="utf-8",
            newline="",
        )
        report, issues = agent.schema_failure_result(
            raw_path=self.raw_path,
            source=self.source,
            checked_at=self.now,
        )
        self.assertEqual(report["status"], "failure")
        self.assertEqual(report["checks"]["required_columns_and_schema"]["status"], "fail")
        self.assertEqual(issues[0]["decision"], "FLAG")
        self.assertIn("raw source preserved", issues[0]["action_taken"])

    def test_repeated_audits_have_identical_decisions(self) -> None:
        quality, _ = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,10.0\n"
            "2024-01-02,\n"
        )
        first_report, first_issues = self.audit(quality)
        second_report, second_issues = self.audit(quality)
        self.assertEqual(first_report["checks"], second_report["checks"])
        self.assertEqual(first_report["counts"], second_report["counts"])
        self.assertEqual(first_issues, second_issues)

    def test_quality_log_appends_audit_history(self) -> None:
        quality, _ = self.build(
            "date,pm25_concentration_ug_per_m3\n"
            "2024-01-01,\n"
        )
        _, issues = self.audit(quality)
        log_path = self.root / "quality_log.csv"
        agent.append_quality_log(log_path, issues, run_id="run-one")
        agent.append_quality_log(log_path, issues, run_id="run-two")
        with log_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 2 * len(issues))
        self.assertEqual(rows[0]["issue"], rows[len(issues)]["issue"])
        self.assertEqual(rows[0]["run_id"], "run-one")
        self.assertEqual(rows[len(issues)]["run_id"], "run-two")

    def test_legacy_log_migration_preserves_events_and_adds_run_identity(self) -> None:
        log_path = self.root / "quality_log.csv"
        with log_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=agent.LEGACY_LOG_FIELDS)
            writer.writeheader()
            writer.writerow(
                {
                    "checked_at_utc": "2024-01-10T00:00:00Z",
                    "source_row_id": "row-a",
                    "source_record_key": "record-a",
                    "observed_date": "2024-01-01",
                    "issue": "legacy_issue",
                    "severity": "warning",
                    "decision": "FLAG",
                    "action_taken": "none",
                    "reason": "legacy event",
                    "source_file_sha256": "abc",
                }
            )
        agent.append_quality_log(log_path, [], run_id="new-run")
        with log_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["run_id"], "legacy:2024-01-10T00:00:00Z")
        self.assertEqual(rows[0]["issue"], "legacy_issue")

    def test_pipeline_runs_agent_and_emits_quality_log(self) -> None:
        config_dir = self.root / "config"
        config_dir.mkdir()
        config_path = config_dir / "sources.json"
        config_path.write_bytes(run.CONFIG_PATH.read_bytes())
        source_file = self.root / "pipeline_source.csv"
        source_file.write_text(
            "date,pm25_concentration_ug_per_m3\n"
            "2016-10-06,10\n"
            "2016-10-07,\n"
            "2016-10-08,12\n",
            encoding="utf-8",
            newline="",
        )
        source_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
        result = run.DownloadResult(
            raw_path=source_file,
            sha256=source_hash,
            md5=hashlib.md5(source_file.read_bytes()).hexdigest(),
            byte_size=source_file.stat().st_size,
            fetched_at_utc="2026-10-20T00:00:00Z",
            http_status=200,
            acquisition_status="reused_cached_file",
        )
        with (
            patch.object(run, "validate_source_availability", return_value=({}, 200)),
            patch.object(run, "download_or_reuse", return_value=result),
        ):
            exit_code, first_status = run.run_pipeline(self.root)
            self.assertEqual(exit_code, 0)
            exit_code, status = run.run_pipeline(self.root)
        self.assertEqual(exit_code, 0)
        self.assertNotEqual(first_status["run_id"], status["run_id"])
        self.assertEqual(status["data_quality_agent_status"], "success_with_warnings")
        quality_path = self.root / "data" / "quality" / "quality_report.json"
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        self.assertEqual(quality["data_quality_agent"]["status"], "success_with_warnings")
        self.assertEqual(quality["data_quality_agent"]["run_id"], status["run_id"])
        self.assertEqual(quality["data_quality_agent"]["count_scope"], "current_run_only")
        log_path = self.root / "data" / "quality" / "quality_log.csv"
        with log_path.open(encoding="utf-8", newline="") as stream:
            logged = list(csv.DictReader(stream))
        self.assertTrue(any(row["issue"] == "unresolved_missing_pm25" for row in logged))
        self.assertEqual(
            {row["run_id"] for row in logged},
            {first_status["run_id"], status["run_id"]},
        )
        self.assertEqual(
            quality["data_quality_agent"]["two_source_compliance"],
            "not_established",
        )

    def test_pipeline_fails_on_critical_invalid_measurement(self) -> None:
        config_dir = self.root / "config"
        config_dir.mkdir()
        (config_dir / "sources.json").write_bytes(run.CONFIG_PATH.read_bytes())
        source_file = self.root / "pipeline_source.csv"
        source_file.write_text(
            "date,pm25_concentration_ug_per_m3\n"
            "2016-10-06,-1\n",
            encoding="utf-8",
            newline="",
        )
        source_bytes = source_file.read_bytes()
        result = run.DownloadResult(
            raw_path=source_file,
            sha256=hashlib.sha256(source_bytes).hexdigest(),
            md5=hashlib.md5(source_bytes).hexdigest(),
            byte_size=len(source_bytes),
            fetched_at_utc="2026-10-20T00:00:00Z",
            http_status=200,
            acquisition_status="reused_cached_file",
        )
        with (
            patch.object(run, "validate_source_availability", return_value=({}, 200)),
            patch.object(run, "download_or_reuse", return_value=result),
        ):
            exit_code, status = run.run_pipeline(self.root)
        self.assertEqual(exit_code, 1)
        self.assertEqual(status["status"], "failed")
        self.assertIn("nonnegative_finite_pm25", status["critical_failures"])


if __name__ == "__main__":
    unittest.main()
