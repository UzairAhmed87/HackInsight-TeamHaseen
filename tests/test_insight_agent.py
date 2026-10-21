from __future__ import annotations

import csv
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pipeline import insight_agent


class InsightAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = insight_agent.ROOT
        self.now = datetime(2026, 10, 20, 3, 45, 51, tzinfo=timezone.utc)
        with (self.root / insight_agent.GOLD_RELATIVE).open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            self.gold_rows = list(csv.DictReader(stream))
        self.gold_ids = {row["row_id"] for row in self.gold_rows}

    def ask(self, question: str) -> dict:
        return insight_agent.answer_question(question, root=self.root, now=self.now)

    def test_date_range_and_observation_count_are_grounded_in_gold(self) -> None:
        result = self.ask("What date range and how many observations are available?")
        self.assertEqual(result["status"], "answered")
        self.assertIn("3,009", result["answer"])
        self.assertIn("2016-10-06", result["answer"])
        self.assertIn("2024-12-31", result["answer"])
        self.assertEqual(result["data_as_of"], "2024-12-31")
        evidence = result["evidence"][0]
        self.assertEqual(evidence["row_count"], len(self.gold_rows))
        self.assertTrue(set(evidence["row_ids"]).issubset(self.gold_ids))

    def test_missing_value_question_cites_actual_missing_gold_rows(self) -> None:
        result = self.ask("How many PM2.5 readings are missing?")
        self.assertIn("6 of 3,009", result["answer"])
        self.assertIn("no values were imputed", result["answer"])
        gold_evidence = next(item for item in result["evidence"] if item["kind"] == "gold_table_aggregation")
        expected_ids = {
            row["row_id"] for row in self.gold_rows if not row["value"].strip()
        }
        self.assertEqual(set(gold_evidence["row_ids"]), expected_ids)
        self.assertEqual(gold_evidence["values"]["missing_pm25_count"], 6)

    def test_numeric_statistic_is_calculated_from_numeric_gold_values(self) -> None:
        result = self.ask("What is the mean PM2.5 reading?")
        self.assertEqual(result["status"], "answered")
        evidence = result["evidence"][0]
        self.assertEqual(evidence["values"]["n"], 3003)
        self.assertGreater(evidence["values"]["mean"], 0)
        self.assertTrue(set(evidence["row_ids"]).issubset(self.gold_ids))

    def test_historical_trend_is_descriptive_not_causal(self) -> None:
        result = self.ask("What is the historical PM2.5 trend over time?")
        self.assertEqual(result["status"], "answered")
        self.assertIn("does not explain causes", result["answer"])
        evidence = result["evidence"][0]["values"]
        self.assertEqual(evidence["first_year"]["year"], 2016)
        self.assertEqual(evidence["last_year"]["year"], 2024)

    def test_causal_question_abstains_with_methodology_evidence(self) -> None:
        result = self.ask("Did traffic cause the PM2.5 increase?")
        self.assertEqual(result["status"], "abstained")
        self.assertIn("I don't know based on the available evidence.", result["answer"])
        self.assertTrue(
            any(item["source_file"] == insight_agent.SOURCE_REGISTER_RELATIVE.as_posix() for item in result["evidence"])
        )

    def test_forecast_evidence_resolves_to_test_split_predictions(self) -> None:
        result = self.ask("How did the model compare with persistence on the held-out test set?")
        self.assertEqual(result["status"], "answered")
        metric_evidence = next(
            item for item in result["evidence"] if item["source_file"] == insight_agent.METRICS_RELATIVE.as_posix()
        )
        self.assertEqual(metric_evidence["locator"], "$.splits.test")
        self.assertEqual(
            metric_evidence["values"]["test_dates"],
            {"start": "2023-10-07", "end": "2024-12-31"},
        )
        prediction_evidence = next(
            item for item in result["evidence"] if item["kind"] == "forecast_prediction_rows"
        )
        with (self.root / insight_agent.PREDICTIONS_RELATIVE).open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            predictions = list(csv.DictReader(stream))
        scored_test_ids = {
            row["row_id"]
            for row in predictions
            if row["split"] == "test" and row["evaluation_status"] == "evaluated"
        }
        self.assertEqual(prediction_evidence["scored_test_prediction_count"], 436)
        self.assertTrue(set(prediction_evidence["sample_row_ids"]).issubset(scored_test_ids))

    def test_current_question_uses_latest_network_hour_without_citywide_claim(self) -> None:
        result = self.ask("What is the current air quality in Karachi?")
        report = json.loads((self.root / insight_agent.NETWORK_REPORT_RELATIVE).read_text(encoding="utf-8"))
        hour = report["latest_hour"]
        self.assertEqual(result["status"], "partially_answered")
        self.assertIn("cannot give a citywide air-quality index", result["answer"])
        self.assertIn(f"{hour['median_pm25_ug_m3']} µg/m³", result["answer"])
        self.assertEqual(result["data_as_of"], hour["datetime_to_utc"])
        self.assertNotEqual(result["data_as_of"], result["generated_at"])

    def test_live_question_abstains_when_network_report_has_no_reading(self) -> None:
        original = insight_agent._read_json

        def without_network(path: Path) -> dict:
            if path.name == insight_agent.NETWORK_REPORT_RELATIVE.name:
                return {}
            return original(path)

        with patch.object(insight_agent, "_read_json", without_network):
            result = self.ask("What is the current air quality in Karachi?")
        self.assertEqual(result["status"], "abstained")
        self.assertIn("cannot establish current or real-time", result["answer"])
        self.assertEqual(result["data_as_of"], "2024-12-31")

    def test_cross_source_question_cites_warehouse_agreement(self) -> None:
        result = self.ask("Do PAQI and the US Consulate monitor agree?")
        cross = json.loads((self.root / insight_agent.WAREHOUSE_RELATIVE).read_text(encoding="utf-8"))["cross_source"]
        self.assertEqual(result["status"], "answered")
        self.assertIn(f"Pearson r = {cross['pearson_r']}", result["answer"])
        self.assertIn(f"{cross['paired_days']:,} days", result["answer"])

    def test_warehouse_question_lists_every_source(self) -> None:
        result = self.ask("Which sources are in the warehouse?")
        self.assertIn("3 sources", result["answer"])
        self.assertIn("US Public Domain", result["answer"])

    def test_unresolved_methodology_is_partially_answered(self) -> None:
        result = self.ask("What monitor and daily averaging method produced these values?")
        self.assertEqual(result["status"], "partially_answered")
        self.assertIn("Unresolved", result["answer"])
        self.assertTrue(any(item["source_file"] == insight_agent.SOURCE_REGISTER_RELATIVE.as_posix() for item in result["evidence"]))
        self.assertTrue(any(item["source_file"] == insight_agent.QUALITY_RELATIVE.as_posix() for item in result["evidence"]))

    def test_unknown_question_abstains(self) -> None:
        result = self.ask("Which team won the football match?")
        self.assertEqual(result["status"], "abstained")
        self.assertIn("I don't know based on the available evidence.", result["answer"])

    def test_identical_inputs_produce_same_answer_except_generated_time(self) -> None:
        first = self.ask("Give year-by-year PM2.5 summaries.")
        second = self.ask("Give year-by-year PM2.5 summaries.")
        self.assertEqual(first, second)

    def test_every_evidence_reference_resolves(self) -> None:
        results = [
            self.ask("How did the model perform on the test set?"),
            self.ask("What monitor and daily averaging method produced these values?"),
            self.ask("How many PM2.5 readings are missing?"),
            self.ask("Did traffic cause the PM2.5 increase?"),
            self.ask("What is the current air quality in Karachi?"),
            self.ask("What is the mean PM2.5 reading?"),
            self.ask("What date range and how many observations are available?"),
            self.ask("Do PAQI and the US Consulate monitor agree?"),
            self.ask("Which sources are in the warehouse?"),
        ]
        for result in results:
            for item in result["evidence"]:
                source = self.root / Path(item["source_file"])
                self.assertTrue(source.is_file(), item["source_file"])
                if item.get("kind") == "gold_table_aggregation":
                    self.assertTrue(set(item.get("row_ids", [])).issubset(self.gold_ids))
                if item.get("kind") == "forecast_prediction_rows":
                    self.assertTrue(set(item.get("sample_row_ids", [])).issubset(self.gold_ids))
                locator = item.get("locator", "")
                if locator.startswith("$."):
                    payload = json.loads(source.read_text(encoding="utf-8"))
                    for token in locator[2:].split("."):
                        payload = payload[token]
                    self.assertIsNotNone(payload)
                elif locator.startswith("candidate_id="):
                    with source.open(encoding="utf-8-sig", newline="") as stream:
                        rows = list(csv.DictReader(stream))
                    candidate = locator.split("=", 1)[1]
                    self.assertTrue(any(row["candidate_id"] == candidate for row in rows))
                elif item.get("kind") == "document_section":
                    text = source.read_text(encoding="utf-8")
                    self.assertIn(item["locator"], text)
                    self.assertIn(item["values"]["statement"], text)


if __name__ == "__main__":
    unittest.main()
