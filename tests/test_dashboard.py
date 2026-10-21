from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import HTTPServer
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch
from urllib.request import Request, urlopen

from pipeline import dashboard


class DashboardPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = dashboard.ROOT
        self.now = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
        self._previous_live_flag = os.environ.get("HACKINSIGHT_DISABLE_LIVE")
        os.environ["HACKINSIGHT_DISABLE_LIVE"] = "1"

    def tearDown(self) -> None:
        if self._previous_live_flag is None:
            os.environ.pop("HACKINSIGHT_DISABLE_LIVE", None)
        else:
            os.environ["HACKINSIGHT_DISABLE_LIVE"] = self._previous_live_flag

    def test_payload_exposes_actual_records_missingness_and_staleness(self) -> None:
        payload = dashboard.build_dashboard_payload(self.root, now=self.now)
        overview = payload["overview"]
        self.assertEqual(overview["start_date"], "2016-10-06")
        self.assertEqual(overview["end_date"], "2024-12-31")
        self.assertEqual(overview["dated_records"], 3009)
        self.assertEqual(overview["numeric_readings"], 3003)
        self.assertEqual(overview["missing_readings"], 6)
        self.assertTrue(overview["freshness"]["is_stale"])
        self.assertGreater(overview["freshness"]["age_days"], 30)
        self.assertTrue(all(row["value"] is None for row in payload["historical"]["series"] if row["date"] in payload["historical"]["missing_dates"]))
        self.assertIn("live", payload)
        self.assertEqual(payload["live"]["status"], "unavailable")
        self.assertIn("health_guidance", payload)
        self.assertTrue(payload["how_it_works"])

    def test_payload_uses_current_run_quality_counts_and_unresolved_statuses(self) -> None:
        payload = dashboard.build_dashboard_payload(self.root, now=self.now)
        quality = payload["quality"]
        self.assertEqual(quality["count_scope"], "current_run_only")
        self.assertEqual(quality["counts"]["warning_checks"], 4)
        self.assertEqual(quality["counts"]["flags"], 12)
        self.assertTrue(quality["warning_checks"])
        self.assertIn("unresolved", quality["unresolved_methodology"])
        self.assertEqual(quality["two_source_compliance"], "established")
        warehouse = payload["warehouse"]
        self.assertEqual({item["source_id"] for item in warehouse["sources"]}, {"paqi_karachi_daily_pm25", "us_consulate_karachi_pm25", "urban_unit_karachi_airgradient_pm25"})
        self.assertGreater(warehouse["total_gold_rows"], 100000)
        self.assertGreater(warehouse["cross_source"]["paired_days"], 1000)

    def test_payload_forecast_has_validation_and_held_out_test_provenance(self) -> None:
        payload = dashboard.build_dashboard_payload(self.root, now=self.now)
        validation = payload["forecast"]["validation"]
        test = payload["forecast"]["test"]
        self.assertEqual(validation["dates"]["start"], "2022-07-13")
        self.assertEqual(test["dates"]["start"], "2023-10-07")
        self.assertEqual(test["dates"]["end"], "2024-12-31")
        self.assertEqual(test["linear_model"]["n"], 436)
        self.assertEqual(test["persistence_on_model_matched_targets"]["n"], 436)
        self.assertTrue(payload["forecast"]["historical_only"])

    def test_payload_does_not_claim_last_success_when_latest_persisted_run_failed(self) -> None:
        original = dashboard._json_file

        def patched(path: Path) -> dict:
            value = original(path)
            if path.name == "execution_status.json":
                value["status"] = "failed"
            return value

        dashboard._json_file = patched
        try:
            payload = dashboard.build_dashboard_payload(self.root, now=self.now)
        finally:
            dashboard._json_file = original
        self.assertIsNone(payload["overview"]["pipeline"]["last_successful_run"])
        self.assertIn("not retained", payload["overview"]["pipeline"]["success_history_note"])


class DashboardHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._previous_live_flag = os.environ.get("HACKINSIGHT_DISABLE_LIVE")
        os.environ["HACKINSIGHT_DISABLE_LIVE"] = "1"
        cls.server = HTTPServer(("127.0.0.1", 0), dashboard.make_handler(dashboard.ROOT))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        if cls._previous_live_flag is None:
            os.environ.pop("HACKINSIGHT_DISABLE_LIVE", None)
        else:
            os.environ["HACKINSIGHT_DISABLE_LIVE"] = cls._previous_live_flag

    def test_dashboard_page_and_data_api_are_served(self) -> None:
        with urlopen(f"{self.base_url}/", timeout=5) as response:
            page = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("Historical and live layers are separate", page)
            self.assertIn("LIVE SENSOR MONITORING", page)
            self.assertIn("Public neighbourhood sensors", page)
            self.assertEqual(response.headers["Content-Security-Policy"].split(";")[0], "default-src 'self'")
        with urlopen(f"{self.base_url}/api/dashboard", timeout=5) as response:
            payload = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["overview"]["missing_readings"], 6)
            self.assertIn("live", payload)
        with urlopen(f"{self.base_url}/api/live", timeout=5) as response:
            live = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(live["status"], "unavailable")

    def test_question_api_returns_existing_insight_agent_evidence(self) -> None:
        request = Request(
            f"{self.base_url}/api/ask",
            data=json.dumps({"question": "How many readings are missing?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            answer = json.loads(response.read())
        self.assertEqual(answer["status"], "answered")
        evidence = next(item for item in answer["evidence"] if item["kind"] == "gold_table_aggregation")
        self.assertEqual(evidence["values"]["missing_pm25_count"], 6)
        self.assertEqual(evidence["source_file"], "data/processed/gold_air_quality.csv")

    def test_question_api_rejects_invalid_body_and_unknown_route(self) -> None:
        request = Request(
            f"{self.base_url}/api/ask",
            data=b'{"command":"anything"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=5)
        self.assertEqual(error.exception.code, 400)
        with self.assertRaises(HTTPError) as missing:
            urlopen(f"{self.base_url}/arbitrary", timeout=5)
        self.assertEqual(missing.exception.code, 404)

    def test_public_api_errors_do_not_expose_local_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            server = HTTPServer(
                ("127.0.0.1", 0),
                dashboard.make_handler(Path(temporary)),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                endpoint = f"http://127.0.0.1:{server.server_port}/api/dashboard"
                with self.assertRaises(HTTPError) as error:
                    urlopen(endpoint, timeout=5)
                self.assertEqual(error.exception.code, 500)
                message = json.loads(error.exception.read())
                self.assertNotIn(temporary, message["error"])
                self.assertNotIn("Traceback", message["error"])
                ask = Request(
                    f"http://127.0.0.1:{server.server_port}/api/ask",
                    data=json.dumps({"question": "How many observations?"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as ask_error:
                    urlopen(ask, timeout=5)
                ask_message = json.loads(ask_error.exception.read())
                self.assertEqual(ask_error.exception.code, 500)
                self.assertNotIn(temporary, ask_message["error"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_oversized_question_is_rejected(self) -> None:
        request = Request(
            f"{self.base_url}/api/ask",
            data=json.dumps({"question": "x" * 5000}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=5)
        self.assertEqual(error.exception.code, 413)

    def test_render_deployment_is_free_native_python_git_service(self) -> None:
        readme = (dashboard.ROOT / "README.md").read_text(encoding="utf-8")
        render_config = (dashboard.ROOT / "render.yaml").read_text(encoding="utf-8")
        gitignore = (dashboard.ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("runtime: python", render_config)
        self.assertIn("plan: free", render_config)
        self.assertIn("startCommand: python -m pipeline.dashboard --host 0.0.0.0", render_config)
        self.assertIn("healthCheckPath: /api/dashboard", render_config)
        for artifact in (
            "data/processed/gold_air_quality.csv",
            "data/quality/quality_report.json",
            "data/reports/execution_status.json",
            "data/reports/forecast_metrics.json",
            "data/reports/forecast_predictions.csv",
        ):
            self.assertIn(f"!/{artifact}", gitignore)
        self.assertIn("/data/raw/", gitignore)
        self.assertIn("/data/quality/*", gitignore)
        self.assertIn("/data/Unveiling-Karachi-Air_PAQI.pdf", gitignore)
        self.assertIn("free", readme.lower())
        self.assertFalse((dashboard.ROOT / "Dockerfile").exists())

    def test_host_port_environment_variable_is_used(self) -> None:
        with (
            patch.dict(os.environ, {"PORT": "8765"}),
            patch.object(dashboard, "ThreadingHTTPServer") as server_type,
        ):
            server_type.return_value.serve_forever.side_effect = KeyboardInterrupt
            self.assertEqual(dashboard.main(["--host", "0.0.0.0"]), 0)
        server_type.assert_called_once()
        self.assertEqual(server_type.call_args.args[0], ("0.0.0.0", 8765))


if __name__ == "__main__":
    unittest.main()
