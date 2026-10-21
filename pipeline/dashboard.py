from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pipeline import insight_agent
from pipeline import live_sensors


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "dashboard"
GOLD_RELATIVE = Path("data/processed/gold_air_quality.csv")
QUALITY_RELATIVE = Path("data/quality/quality_report.json")
EXECUTION_RELATIVE = Path("data/reports/execution_status.json")
METRICS_RELATIVE = Path("data/reports/forecast_metrics.json")
WAREHOUSE_RELATIVE = Path("data/quality/warehouse_quality_report.json")
SOURCE_REGISTER_RELATIVE = Path("docs/source_register.csv")
MAX_QUESTION_BYTES = 4096
SUCCESS_STATUSES = {"success", "success_with_warnings"}
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"


def _live_snapshot(root: Path, *, now: datetime) -> dict[str, Any]:
    """Best-effort live block; never fails the historical dashboard."""
    try:
        return live_sensors.fetch_live_snapshot(root, now=now, use_cache=True)
    except live_sensors.LiveSensorError as exc:
        return {
            "status": "unavailable",
            "error": str(exc),
            "sensors": [],
            "primary_sensor": None,
            "available_pm25_sensor_count": 0,
            "coverage_disclaimer": (
                "Live sensor configuration could not be loaded. Historical dashboard remains available."
            ),
            "unavailable_targets": [],
            "notes": [str(exc)],
            "generated_at_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
    except Exception as exc:  # noqa: BLE001 - dashboard must stay up
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: live fetch failed",
            "sensors": [],
            "primary_sensor": None,
            "available_pm25_sensor_count": 0,
            "coverage_disclaimer": (
                "Live upstream request failed. Historical PAQI evidence remains available."
            ),
            "unavailable_targets": [],
            "notes": [f"{type(exc).__name__}: {exc}"],
            "generated_at_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }


class DashboardDataError(Exception):
    """Raised when dashboard evidence is missing or inconsistent."""


def _json_file(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardDataError(f"Cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DashboardDataError(f"Expected a JSON object in {path}.")
    return value


def _source_register(root: Path) -> dict[str, str]:
    path = root / SOURCE_REGISTER_RELATIVE
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None:
                raise DashboardDataError("Source register has no header.")
            for row in reader:
                if row.get("candidate_id") == "PAQI-KHI-DAILY":
                    return row
    except (OSError, csv.Error) as exc:
        raise DashboardDataError(f"Cannot load {path}: {exc}") from exc
    raise DashboardDataError("The PAQI source is missing from the source register.")


def _read_gold(path: Path) -> list[dict[str, Any]]:
    required = {"row_id", "observed_date", "value", "quality_flag"}
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise DashboardDataError(f"Gold table lacks required columns: {sorted(required)}")
            rows: list[dict[str, Any]] = []
            ids: set[str] = set()
            dates: set[date] = set()
            for line, row in enumerate(reader, start=2):
                row_id = row.get("row_id", "")
                if not row_id or row_id in ids:
                    raise DashboardDataError(f"Missing or duplicate row ID at gold CSV line {line}.")
                ids.add(row_id)
                try:
                    observed = date.fromisoformat(row["observed_date"])
                except (TypeError, ValueError) as exc:
                    raise DashboardDataError(f"Invalid observation date at gold CSV line {line}.") from exc
                if observed in dates:
                    raise DashboardDataError(f"Duplicate gold observation date: {observed.isoformat()}.")
                dates.add(observed)
                raw_value = (row.get("value") or "").strip()
                try:
                    number = float(raw_value) if raw_value else None
                except ValueError as exc:
                    raise DashboardDataError(f"Invalid PM2.5 value at gold CSV line {line}.") from exc
                if number is not None and (number < 0 or number != number or number in (float("inf"), float("-inf"))):
                    raise DashboardDataError(f"Invalid non-finite/negative PM2.5 value at gold CSV line {line}.")
                rows.append(
                    {
                        "row_id": row_id,
                        "date": observed.isoformat(),
                        "value": number,
                        "quality_flag": row.get("quality_flag", ""),
                    }
                )
    except (OSError, csv.Error) as exc:
        raise DashboardDataError(f"Cannot load gold table {path}: {exc}") from exc
    if not rows:
        raise DashboardDataError("Gold table is empty.")
    return sorted(rows, key=lambda row: row["date"])


def _year_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import statistics

    grouped: dict[str, list[float]] = {}
    for row in rows:
        if row["value"] is not None:
            grouped.setdefault(row["date"][:4], []).append(row["value"])
    summaries = []
    for year, values in sorted(grouped.items()):
        summaries.append(
            {
                "year": int(year),
                "n": len(values),
                "missing": sum(
                    row["date"].startswith(year) and row["value"] is None for row in rows
                ),
                "mean": statistics.fmean(values),
                "median": statistics.median(values),
                "minimum": min(values),
                "maximum": max(values),
            }
        )
    return summaries


def _freshness(last_date: str, quality: dict[str, Any], now: datetime) -> dict[str, Any]:
    try:
        latest = date.fromisoformat(last_date)
    except ValueError as exc:
        raise DashboardDataError(f"Invalid last observation date: {last_date}") from exc
    utc_today = now.astimezone(timezone.utc).date()
    age = (utc_today - latest).days
    threshold = int(
        quality.get("data_quality_agent", {}).get("freshness_warning_days")
        or quality.get("checks", {}).get("freshness", {}).get("warning_days")
        or 30
    )
    return {
        "last_observation_date": last_date,
        "age_days": age,
        "warning_threshold_days": threshold,
        "is_stale": age > threshold,
        "label": "Historical data; not current conditions.",
    }


def build_dashboard_payload(
    root: Path = ROOT,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware.")
    gold = _read_gold(root / GOLD_RELATIVE)
    quality = _json_file(root / QUALITY_RELATIVE)
    execution = _json_file(root / EXECUTION_RELATIVE)
    metrics = _json_file(root / METRICS_RELATIVE)
    try:
        warehouse = _json_file(root / WAREHOUSE_RELATIVE)
    except DashboardDataError:
        warehouse = {}
    two_source = warehouse.get("two_source_compliance", "not_established")
    source = _source_register(root)
    first_date = gold[0]["date"]
    last_date = gold[-1]["date"]
    missing = [row for row in gold if row["value"] is None]
    agent_report = quality.get("data_quality_agent", {})
    agent_checks = agent_report.get("checks", {})
    current_counts = agent_report.get("counts", execution.get("data_quality_agent_counts", {}))
    latest_run_status = execution.get("status", "unknown")
    last_success = None
    if latest_run_status in SUCCESS_STATUSES:
        last_success = {
            "run_id": execution.get("run_id"),
            "finished_at_utc": execution.get("finished_at_utc"),
            "status": latest_run_status,
        }
    checks = agent_report.get("checks", {})
    return {
        "generated_at_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "overview": {
            "start_date": first_date,
            "end_date": last_date,
            "dated_records": len(gold),
            "numeric_readings": sum(row["value"] is not None for row in gold),
            "missing_readings": len(missing),
            "freshness": _freshness(last_date, quality, now),
            "pipeline": {
                "latest_status": latest_run_status,
                "latest_run_id": execution.get("run_id"),
                "latest_finished_at_utc": execution.get("finished_at_utc"),
                "last_successful_run": last_success,
                "success_history_note": (
                    "The persisted execution status stores the latest run only; older successful run history is not retained here."
                    if last_success is None
                    else "This is the latest persisted run and it completed successfully (warnings may be present)."
                ),
            },
        },
        "historical": {
            "unit": "µg/m³",
            "series": gold,
            "yearly_summary": _year_summaries(gold),
            "missing_dates": [row["date"] for row in missing],
            "interpretation": (
                "Published PAQI Karachi series; station identity and citywide exposure representativeness are not established."
            ),
        },
        "quality": {
            "pipeline_status": quality.get("quality_status", execution.get("quality_status", "unknown")),
            "agent_status": agent_report.get("status", execution.get("data_quality_agent_status", "unknown")),
            "run_id": agent_report.get("run_id"),
            "checked_at_utc": agent_report.get("checked_at_utc"),
            "count_scope": agent_report.get("count_scope", "current_run_only"),
            "counts": current_counts,
            "checks": [
                {"name": name, **check}
                for name, check in checks.items()
            ],
            "warning_checks": [
                {"name": name, **check}
                for name, check in checks.items()
                if check.get("status") == "warning"
            ],
            "unresolved_methodology": agent_checks.get(
                "measurement_methodology_documentation", {}
            ).get("detail", "Measurement methodology remains unresolved."),
            "two_source_compliance": two_source,
            "append_only_log_is_historical": True,
        },
        "forecast": {
            "experiment": metrics.get("experiment"),
            "unit": metrics.get("unit", "µg/m³"),
            "historical_only": True,
            "validation": metrics.get("splits", {}).get("validation", {}),
            "test": metrics.get("splits", {}).get("test", {}),
            "limitations": metrics.get("limitations", []),
        },
        "source": {
            "name": source.get("candidate"),
            "publisher": source.get("publisher_or_original_source"),
            "url": source.get("official_dataset_or_access_url"),
            "license_summary": source.get("licence_and_permitted_use"),
            "license_url": LICENSE_URL,
            "independence_status": source.get("independence_status"),
            "two_source_compliance": two_source,
            "attribution": (
                "Omar Abid, Dawar Hameed Butt, and Mahad Naveed / Pakistan Air Quality Initiative (PAQI), "
                "Unveiling Karachi's Air, version DOI 10.5281/zenodo.15845428, CC BY 4.0. "
                "Identify modifications; do not imply endorsement."
            ),
        },
        "warehouse": {
            "two_source_compliance": two_source,
            "total_gold_rows": warehouse.get("total_gold_rows"),
            "sources": warehouse.get("sources", []),
            "cross_source": warehouse.get("cross_source", {}),
            "checks": warehouse.get("checks", {}),
        },
        "live": _live_snapshot(root, now=now),
        "health_guidance": {
            "title": "Understanding PM2.5",
            "summary": (
                "PM2.5 is particulate matter with diameter ≤2.5 micrometres. Elevated outdoor "
                "concentrations are associated with respiratory and cardiovascular risk in population studies."
            ),
            "caveat": (
                "This dashboard does not diagnose individuals or issue medical advice. "
                "An instantaneous or short-window sensor reading is not the same as a 24-hour mean "
                "used in many air-quality standards. For emergencies, follow official Pakistan guidance "
                "and local health services."
            ),
            "reference": "WHO global air-quality guidelines (2021) discuss health evidence for PM2.5; local regulations may differ.",
        },
        "how_it_works": [
            "Acquire published historical PAQI Karachi daily PM2.5 from a pinned Zenodo record with checksum verification.",
            "Validate and organize measurements into raw, cleaned and gold layers without inventing values.",
            "Describe historical patterns and missingness from the gold table only.",
            "Evaluate next-day forecasting on chronological train/validation/test splits versus persistence.",
            "Answer evidence-grounded questions locally; abstain when evidence is insufficient.",
            "Optionally fetch public AirGradient point sensors for live neighbourhood readings — never as a citywide AQI.",
        ],
    }


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
    )
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(root: Path = ROOT) -> type[BaseHTTPRequestHandler]:
    root = root.resolve()

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "HackInsightDashboard/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _security_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            )

        def do_GET(self) -> None:
            route = urlsplit(self.path).path
            if route == "/api/dashboard":
                try:
                    payload = build_dashboard_payload(root)
                except (DashboardDataError, OSError, ValueError):
                    _send_json(
                        self,
                        500,
                        {"error": "Dashboard evidence is unavailable. Please try again later."},
                    )
                    return
                _send_json(self, 200, payload)
                return
            if route == "/api/live":
                now = datetime.now(timezone.utc)
                payload = _live_snapshot(root, now=now)
                # Always 200 with explicit status so the historical UI never hard-fails on live outages.
                _send_json(self, 200, payload)
                return
            assets = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/index.html": ("index.html", "text/html; charset=utf-8"),
                "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            }
            asset = assets.get(route)
            if asset is None:
                self.send_error(404, "Not found")
                return
            path = ASSET_ROOT / asset[0]
            try:
                body = path.read_bytes()
            except OSError:
                self.send_error(500, "Dashboard asset unavailable")
                return
            self.send_response(200)
            self.send_header("Content-Type", asset[1])
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/api/ask":
                self.send_error(404, "Not found")
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                _send_json(self, 400, {"error": "Invalid Content-Length."})
                return
            if size <= 0 or size > MAX_QUESTION_BYTES:
                _send_json(self, 413 if size > MAX_QUESTION_BYTES else 400, {"error": "Question body must be between 1 and 4096 bytes."})
                return
            try:
                body = json.loads(self.rfile.read(size).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                _send_json(self, 400, {"error": "Request body must be valid UTF-8 JSON."})
                return
            question = body.get("question") if isinstance(body, dict) else None
            if not isinstance(question, str) or not question.strip():
                _send_json(self, 400, {"error": "A non-empty string question is required."})
                return
            try:
                answer = insight_agent.answer_question(question, root=root)
            except (insight_agent.InsightAgentError, ValueError):
                _send_json(
                    self,
                    500,
                    {"error": "The Insight Agent could not access its evidence. Please try again later."},
                )
                return
            _send_json(self, 200, answer)

    return DashboardHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local HackInsight dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    server = ThreadingHTTPServer((args.host, args.port), make_handler(ROOT))
    print(f"HackInsight dashboard running at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
