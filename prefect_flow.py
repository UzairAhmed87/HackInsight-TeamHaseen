"""Hourly Prefect flow: rebuild the warehouse, run the Data Quality Agent, re-evaluate the model.

Every flow run, successful or failed, is appended to ``prefect_runs.csv`` by Prefect state hooks.
The file is written only by this flow; do not edit it by hand.

Run locally:      python prefect_flow.py
Hourly schedule:  .github/workflows/hourly-pipeline.yml (GitHub Actions cron) runs this flow.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prefect import flow, get_run_logger, task

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline import forecasting  # noqa: E402
from pipeline import run as warehouse  # noqa: E402

RUNS_LOG = ROOT / "prefect_runs.csv"
EXECUTION_STATUS = ROOT / "data" / "reports" / "execution_status.json"
QUALITY_REPORT = ROOT / "data" / "quality" / "quality_report.json"
FORECAST_METRICS = ROOT / "data" / "reports" / "forecast_metrics.json"

RUN_FIELDS = [
    "flow_run_id",
    "flow_run_name",
    "state",
    "started_at_utc",
    "finished_at_utc",
    "duration_seconds",
    "pipeline_run_id",
    "pipeline_status",
    "quality_status",
    "dq_checks_passed",
    "dq_checks_warning",
    "dq_checks_failed",
    "gold_rows",
    "latest_observation_date",
    "test_mae_linear",
    "test_mae_persistence",
    "message",
]


class PipelineRunFailed(RuntimeError):
    """Raised when a pipeline stage exits nonzero so Prefect marks the run Failed."""


def _utc(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@task(name="build-warehouse-and-quality-agent", retries=2, retry_delay_seconds=60)
def build_warehouse() -> dict[str, Any]:
    logger = get_run_logger()
    code, status = warehouse.run_pipeline()
    logger.info("Warehouse run %s finished with status %s", status.get("run_id"), status.get("status"))
    if code != 0:
        raise PipelineRunFailed(f"make data failed: {status.get('errors')}")
    return status


@task(name="evaluate-forecast-model")
def evaluate_model() -> dict[str, Any]:
    logger = get_run_logger()
    if forecasting.main() != 0:
        raise PipelineRunFailed("Forecast evaluation failed.")
    metrics = _read_json(FORECAST_METRICS)
    test = metrics.get("splits", {}).get("test", {})
    logger.info(
        "Test MAE linear=%s persistence=%s",
        test.get("linear_model", {}).get("mae"),
        test.get("persistence_on_model_matched_targets", {}).get("mae"),
    )
    return metrics


def _record_run(flow_obj: Any, flow_run: Any, state: Any) -> None:
    execution = _read_json(EXECUTION_STATUS)
    quality = _read_json(QUALITY_REPORT)
    counts = quality.get("data_quality_agent", {}).get("counts", {})
    test = _read_json(FORECAST_METRICS).get("splits", {}).get("test", {})
    started = flow_run.start_time
    finished = datetime.now(timezone.utc)
    row = {
        "flow_run_id": str(flow_run.id),
        "flow_run_name": flow_run.name,
        "state": state.name,
        "started_at_utc": _utc(started),
        "finished_at_utc": _utc(finished),
        "duration_seconds": round((finished - started).total_seconds(), 2) if started else "",
        "pipeline_run_id": execution.get("run_id", ""),
        "pipeline_status": execution.get("status", ""),
        "quality_status": quality.get("quality_status", ""),
        "dq_checks_passed": counts.get("passed_checks", ""),
        "dq_checks_warning": counts.get("warning_checks", ""),
        "dq_checks_failed": counts.get("failed_checks", ""),
        "gold_rows": quality.get("gold_record_count", ""),
        "latest_observation_date": quality.get("last_observation_date", ""),
        "test_mae_linear": test.get("linear_model", {}).get("mae", ""),
        "test_mae_persistence": test.get("persistence_on_model_matched_targets", {}).get("mae", ""),
        "message": (state.message or "")[:300],
    }
    new_file = not RUNS_LOG.exists() or RUNS_LOG.stat().st_size == 0
    with RUNS_LOG.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=RUN_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


@flow(
    name="hackinsight-hourly-pipeline",
    description="Rebuild raw/cleaned/gold layers, run the Data Quality Agent and re-evaluate the forecast.",
    on_completion=[_record_run],
    on_failure=[_record_run],
    on_crashed=[_record_run],
)
def hackinsight_pipeline() -> dict[str, Any]:
    status = build_warehouse()
    metrics = evaluate_model()
    return {"pipeline_status": status.get("status"), "test": metrics.get("splits", {}).get("test", {}).get("dates")}


if __name__ == "__main__":
    try:
        hackinsight_pipeline()
    except Exception as exc:  # noqa: BLE001 - flow state is recorded by hooks; exit nonzero for the scheduler
        print(f"Flow failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
