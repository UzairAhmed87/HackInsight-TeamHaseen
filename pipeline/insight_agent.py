from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
GOLD_RELATIVE = Path("data/processed/gold_air_quality.csv")
QUALITY_RELATIVE = Path("data/quality/quality_report.json")
METRICS_RELATIVE = Path("data/reports/forecast_metrics.json")
PREDICTIONS_RELATIVE = Path("data/reports/forecast_predictions.csv")
SOURCE_REGISTER_RELATIVE = Path("docs/source_register.csv")
FORECAST_DOC_RELATIVE = Path("docs/forecasting_results.md")
ABSTENTION = "I don't know based on the available evidence."


class InsightAgentError(Exception):
    """Raised when required evidence is missing or cannot be validated."""


@dataclass(frozen=True)
class GoldRecord:
    row_id: str
    observed_date: date
    value: float | None
    quality_flag: str


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise InsightAgentError(f"Cannot read evidence file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InsightAgentError(f"Evidence file must contain a JSON object: {path}")
    return payload


def _read_gold(path: Path) -> list[GoldRecord]:
    required = {"row_id", "observed_date", "value", "quality_flag"}
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise InsightAgentError(f"Gold table lacks required columns: {sorted(required)}")
            records: list[GoldRecord] = []
            seen_ids: set[str] = set()
            seen_dates: set[date] = set()
            for line_number, row in enumerate(reader, start=2):
                row_id = row.get("row_id", "")
                if not row_id or row_id in seen_ids:
                    raise InsightAgentError(f"Gold row {line_number} has a missing or duplicate row ID.")
                seen_ids.add(row_id)
                try:
                    observed_date = date.fromisoformat(row["observed_date"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise InsightAgentError(f"Gold row {line_number} has an invalid observation date.") from exc
                if observed_date in seen_dates:
                    raise InsightAgentError(f"Gold table contains duplicate date {observed_date}.")
                seen_dates.add(observed_date)
                raw_value = (row.get("value") or "").strip()
                if raw_value:
                    try:
                        value = float(raw_value)
                    except ValueError as exc:
                        raise InsightAgentError(f"Gold row {line_number} has an invalid value.") from exc
                    if not math.isfinite(value) or value < 0:
                        raise InsightAgentError(f"Gold row {line_number} has a negative or non-finite value.")
                else:
                    value = None
                records.append(
                    GoldRecord(row_id, observed_date, value, row.get("quality_flag", ""))
                )
    except (OSError, csv.Error) as exc:
        raise InsightAgentError(f"Cannot read gold table {path}: {exc}") from exc
    if not records:
        raise InsightAgentError("Gold table contains no records.")
    return sorted(records, key=lambda record: record.observed_date)


def _read_source_register(path: Path) -> dict[str, str]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            for row in reader:
                if row.get("candidate_id") == "PAQI-KHI-DAILY":
                    return row
    except (OSError, csv.Error) as exc:
        raise InsightAgentError(f"Cannot read source register {path}: {exc}") from exc
    raise InsightAgentError("PAQI source entry is absent from the source register.")


def _utc_text(now: datetime | None) -> str:
    timestamp = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("now must be timezone-aware.")
    return timestamp.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _gold_evidence(
    records: list[GoldRecord],
    *,
    operation: str,
    values: dict[str, Any],
    row_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    return {
        "source_file": GOLD_RELATIVE.as_posix(),
        "kind": "gold_table_aggregation",
        "date_range": {
            "start": records[0].observed_date.isoformat(),
            "end": records[-1].observed_date.isoformat(),
        },
        "row_count": len(records),
        "numeric_row_count": sum(record.value is not None for record in records),
        "operation": operation,
        "values": values,
        "row_ids": list(row_ids or []),
    }


def _report_evidence(
    source_file: Path,
    locator: str,
    values: dict[str, Any],
    *,
    row_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "source_file": source_file.as_posix(),
        "kind": "report_field",
        "locator": locator,
        "values": values,
    }
    if row_ids is not None:
        item["row_ids"] = list(row_ids)
    return item


def _contains_any(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _classify(question: str) -> str:
    text = " ".join(question.lower().split())
    if re.search(r"\b(now|currently|today|live|real[ -]?time)\b", text):
        return "live"
    if _contains_any(
        text,
        "live",
        "real-time",
        "realtime",
        "right now",
        "currently",
        "current air",
        "today",
        "latest air",
        "is the air",
    ):
        return "live"
    if _contains_any(text, "cause", "caused", "because of", "traffic", "industry", "why did"):
        return "causal"
    if _contains_any(
        text,
        "forecast",
        "prediction",
        "persistence",
        "held-out",
        "held out",
        "test set",
        "mae",
        "rmse",
        "model beat",
    ):
        return "forecast"
    if _contains_any(
        text,
        "method",
        "monitor",
        "station",
        "sensor",
        "license",
        "licence",
        "provenance",
        "source",
        "independent",
        "aggregation",
        "timezone",
        "time zone",
        "quality assurance",
        "calibration",
    ):
        return "methodology"
    if _contains_any(text, "missing", "warning", "quality", "blank", "stale", "freshness"):
        return "quality"
    if _contains_any(text, "year-by-year", "year by year", "annual", "by year", "each year"):
        return "yearly"
    if _contains_any(text, "trend", "increase", "decrease", "over time", "changed"):
        return "trend"
    if _contains_any(text, "date range", "how many", "number of observations", "observation count", "observations", "dates covered", "date coverage"):
        return "overview"
    if _contains_any(text, "mean", "average", "median", "standard deviation", "std", "maximum", "minimum", "highest", "lowest", "value range"):
        return "statistics"
    return "unknown"


def _load_evidence(root: Path) -> tuple[list[GoldRecord], dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    records = _read_gold(root / GOLD_RELATIVE)
    quality = _read_json(root / QUALITY_RELATIVE)
    metrics = _read_json(root / METRICS_RELATIVE)
    _read_source_register(root / SOURCE_REGISTER_RELATIVE)
    predictions_path = root / PREDICTIONS_RELATIVE
    try:
        with predictions_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None or not {"row_id", "observed_date", "split"}.issubset(reader.fieldnames):
                raise InsightAgentError("Forecast predictions lack required provenance columns.")
            predictions = list(reader)
    except (OSError, csv.Error) as exc:
        raise InsightAgentError(f"Cannot read forecast predictions {predictions_path}: {exc}") from exc
    gold_dates = {record.row_id: record.observed_date.isoformat() for record in records}
    for row in predictions:
        if row["row_id"] not in gold_dates:
            raise InsightAgentError("Forecast predictions contain row IDs absent from the gold table.")
        if row["observed_date"] != gold_dates[row["row_id"]]:
            raise InsightAgentError("Forecast prediction date does not match its gold row ID.")
    return records, quality, metrics, predictions


def _answer(
    question: str,
    root: Path,
    now: datetime | None,
) -> dict[str, Any]:
    records, quality, metrics, predictions = _load_evidence(root)
    values = [record.value for record in records if record.value is not None]
    first_date, last_date = records[0].observed_date, records[-1].observed_date
    data_as_of = last_date.isoformat()
    route = _classify(question)
    evidence: list[dict[str, Any]] = []
    limitations: list[str] = []
    status = "answered"
    answer = ABSTENTION

    if route in {"live", "causal"}:
        if route == "live":
            answer = (
                f"{ABSTENTION} The available PAQI series ends on {data_as_of}; "
                "it cannot establish current or real-time air quality."
            )
            limitations.append("Historical measurements are not a live monitoring feed or health-warning service.")
        else:
            answer = (
                f"{ABSTENTION} The data can describe recorded PM2.5 values over time, "
                "but they do not establish why those values changed."
            )
            limitations.append("No causal design or source evidence linking changes to emissions, traffic, or policy is available.")
        evidence.append(
            _report_evidence(
                QUALITY_RELATIVE,
                "$.last_observation_date",
                {"last_observation_date": quality.get("last_observation_date", data_as_of)},
            )
        )
        if route == "causal":
            evidence.extend(
                [
                    _report_evidence(
                        SOURCE_REGISTER_RELATIVE,
                        "candidate_id=PAQI-KHI-DAILY",
                        {
                            "available_measurement": _read_source_register(
                                root / SOURCE_REGISTER_RELATIVE
                            ).get("dates_frequency_variables")
                        },
                    ),
                    _report_evidence(
                        QUALITY_RELATIVE,
                        "$.data_quality_agent.checks.measurement_methodology_documentation",
                        {
                            "methodology_limitations": quality.get("data_quality_agent", {})
                            .get("checks", {})
                            .get("measurement_methodology_documentation", {})
                            .get("detail")
                        },
                    ),
                ]
            )
        status = "abstained"
    elif route == "overview":
        answer = (
            f"The gold table contains {len(records):,} dated observations from "
            f"{first_date.isoformat()} through {last_date.isoformat()}; "
            f"{sum(value is not None for value in (record.value for record in records)):,} have numeric PM2.5 readings."
        )
        evidence.append(
            _gold_evidence(
                records,
                operation="count rows, unique dates, and nonblank numeric values from gold table",
                values={
                    "observation_count": len(records),
                    "unique_dates": len({record.observed_date for record in records}),
                    "numeric_pm25_count": len(values),
                },
                row_ids=[records[0].row_id, records[-1].row_id],
            )
        )
        evidence.append(
            _report_evidence(
                QUALITY_RELATIVE,
                "$.checks.city_station_identity",
                {"city_station_identity": quality.get("checks", {}).get("city_station_identity", {}).get("detail")},
            )
        )
        limitations.append("The dataset is the published PAQI series, not a demonstrated citywide exposure estimate.")
    elif route == "quality":
        missing = [record for record in records if record.value is None]
        agent_report = quality.get("data_quality_agent", {})
        counts = agent_report.get("counts", {})
        warnings = {
            name: check.get("detail")
            for name, check in agent_report.get("checks", {}).items()
            if check.get("status") == "warning"
        }
        answer = (
            f"{len(missing)} of {len(records):,} dated rows have blank PM2.5 values; "
            f"no values were imputed. The latest Data Quality Agent run recorded "
            f"{counts.get('warning_checks', 0)} warning checks and {counts.get('flags', 0)} FLAG decisions."
        )
        evidence.extend(
            [
                _gold_evidence(
                    records,
                    operation="count blank normalized PM2.5 cells",
                    values={"missing_pm25_count": len(missing), "dates": [row.observed_date.isoformat() for row in missing]},
                    row_ids=[row.row_id for row in missing],
                ),
                _report_evidence(
                    QUALITY_RELATIVE,
                    "$.data_quality_agent.checks",
                    {"warning_checks": warnings, "run_id": agent_report.get("run_id")},
                ),
                _report_evidence(
                    QUALITY_RELATIVE,
                    "$.data_quality_agent.counts",
                    {"warning_checks": warnings, "counts": counts, "run_id": agent_report.get("run_id")},
                ),
            ]
        )
        limitations.append("The current-run counts describe the latest agent run, not cumulative quality-log history.")
    elif route in {"statistics", "yearly", "trend"}:
        year_values: dict[int, list[GoldRecord]] = {}
        for record in records:
            if record.value is not None:
                year_values.setdefault(record.observed_date.year, []).append(record)
        if route == "yearly":
            summaries = {
                str(year): {
                    "n": len(rows),
                    "mean": statistics.fmean(row.value for row in rows if row.value is not None),
                    "median": statistics.median(row.value for row in rows if row.value is not None),
                    "minimum": min(row.value for row in rows if row.value is not None),
                    "maximum": max(row.value for row in rows if row.value is not None),
                }
                for year, rows in sorted(year_values.items())
            }
            answer = "Year-by-year descriptive PM2.5 summaries (ug/m3): " + "; ".join(
                f"{year}: n={item['n']}, mean={item['mean']:.2f}, median={item['median']:.2f}, range={item['minimum']:.2f}-{item['maximum']:.2f}"
                for year, item in summaries.items()
            ) + "."
            evidence.append(
                _gold_evidence(
                    records,
                    operation="group numeric gold rows by calendar year; calculate count, arithmetic mean, median, minimum and maximum",
                    values={"unit": "ug/m3", "by_year": summaries},
                )
            )
        else:
            mean = statistics.fmean(values)
            median = statistics.median(values)
            std = statistics.stdev(values) if len(values) > 1 else 0.0
            minimum_record = min((row for row in records if row.value is not None), key=lambda row: row.value)
            maximum_record = max((row for row in records if row.value is not None), key=lambda row: row.value)
            stats_values = {
                "n": len(values),
                "mean": mean,
                "median": median,
                "sample_standard_deviation": std,
                "minimum": {"value": minimum_record.value, "date": minimum_record.observed_date.isoformat(), "row_id": minimum_record.row_id},
                "maximum": {"value": maximum_record.value, "date": maximum_record.observed_date.isoformat(), "row_id": maximum_record.row_id},
                "unit": "ug/m3",
            }
            evidence.append(
                _gold_evidence(
                    records,
                    operation="calculate descriptive statistics from numeric gold values; sample standard deviation",
                    values=stats_values,
                    row_ids=[minimum_record.row_id, maximum_record.row_id],
                )
            )
            if route == "trend":
                first_year = min(year_values)
                last_year = max(year_values)
                first_mean = statistics.fmean(row.value for row in year_values[first_year] if row.value is not None)
                last_mean = statistics.fmean(row.value for row in year_values[last_year] if row.value is not None)
                answer = (
                    f"The observed annual mean was {first_mean:.2f} ug/m3 in {first_year} "
                    f"(n={len(year_values[first_year])}) and {last_mean:.2f} ug/m3 in {last_year} "
                    f"(n={len(year_values[last_year])}); this describes the recorded series and does not explain causes."
                )
                evidence[0]["operation"] = "calculate first- and last-calendar-year means from numeric gold rows"
                evidence[0]["values"] = {
                    "unit": "ug/m3",
                    "first_year": {"year": first_year, "n": len(year_values[first_year]), "mean": first_mean},
                    "last_year": {"year": last_year, "n": len(year_values[last_year]), "mean": last_mean},
                }
                evidence[0]["row_ids"] = [
                    year_values[first_year][0].row_id,
                    year_values[last_year][-1].row_id,
                ]
            else:
                answer = (
                    f"Across {len(values):,} numeric PM2.5 readings ({first_date} to {last_date}), "
                    f"mean={mean:.2f}, median={median:.2f}, sample standard deviation={std:.2f}, "
                    f"minimum={minimum_record.value:.2f}, maximum={maximum_record.value:.2f} ug/m3."
                )
        limitations.append("Descriptive statistics apply to the published PAQI series; they do not establish monitor identity or citywide representativeness.")
        evidence.append(
            _report_evidence(
                QUALITY_RELATIVE,
                "$.checks.city_station_identity",
                {"city_station_identity": quality.get("checks", {}).get("city_station_identity", {}).get("detail")},
            )
        )
    elif route == "forecast":
        validation = metrics.get("splits", {}).get("validation", {})
        test = metrics.get("splits", {}).get("test", {})
        test_dates = test.get("dates", {})
        model = test.get("linear_model", {})
        persistence = test.get("persistence_on_model_matched_targets", {})
        paired = test.get("paired_model_minus_persistence", {})
        prediction_test_rows = [
            row for row in predictions
            if row["split"] == "test"
            and row.get("evaluation_status") == "evaluated"
            and row.get("model_prediction_ug_m3", "")
        ]
        scored_test_dates = sorted(row["observed_date"] for row in prediction_test_rows)
        if (
            not test_dates
            or not model
            or test.get("dates", {}).get("end") != data_as_of
            or len(prediction_test_rows) != model.get("n")
            or not scored_test_dates
            or scored_test_dates[0] < test_dates.get("start", "")
            or scored_test_dates[-1] > test_dates.get("end", "")
        ):
            raise InsightAgentError("Forecast metrics lack consistent test-date or scored-row provenance.")
        answer = (
            f"On the held-out test split {test_dates['start']} to {test_dates['end']}, "
            f"the linear model scored n={model['n']}, MAE={model['mae']:.4f} and RMSE={model['rmse']:.4f} ug/m3. "
            f"Persistence on those same model-matched dates had MAE={persistence['mae']:.4f} and "
            f"RMSE={persistence['rmse']:.4f}; model-minus-persistence differences were "
            f"{paired['mae_difference']:.4f} MAE and {paired['rmse_difference']:.4f} RMSE."
        )
        evidence.extend(
            [
                _report_evidence(
                    METRICS_RELATIVE,
                    "$.splits.test",
                    {
                        "test_dates": test_dates,
                        "model": model,
                        "persistence_on_model_matched_targets": persistence,
                        "paired_model_minus_persistence": paired,
                        "validation_dates": validation.get("dates"),
                    },
                ),
                {
                    "source_file": PREDICTIONS_RELATIVE.as_posix(),
                    "kind": "forecast_prediction_rows",
                    "date_range": test_dates,
                    "scored_test_prediction_count": len(prediction_test_rows),
                    "sample_row_ids": [row["row_id"] for row in prediction_test_rows[:3]],
                },
            ]
        )
        try:
            forecast_doc = (root / FORECAST_DOC_RELATIVE).read_text(encoding="utf-8")
        except OSError as exc:
            raise InsightAgentError(f"Cannot read forecast limitation evidence: {exc}") from exc
        significance_note = "No significance test was performed."
        if significance_note in forecast_doc:
            evidence.append(
                {
                    "source_file": FORECAST_DOC_RELATIVE.as_posix(),
                    "kind": "document_section",
                    "locator": "## Result summary",
                    "values": {"statement": significance_note},
                }
            )
        limitations.append(
            f"This is historical backtest evidence ending {test_dates['end']}, not a live forecast; no statistical significance is claimed."
        )
        limitations.append("Only PAQI was used; two-source compliance is not established.")
    elif route == "methodology":
        source_row = _read_source_register(root / SOURCE_REGISTER_RELATIVE)
        quality_checks = quality.get("checks", {})
        known = {
            "publisher": source_row.get("publisher_or_original_source"),
            "license_and_permitted_use": source_row.get("licence_and_permitted_use"),
            "verified_description": source_row.get("dates_frequency_variables"),
        }
        unresolved = {
            key: quality_checks.get(key, {}).get("detail")
            for key in ("city_station_identity", "timestamp_and_resolution", "cross_source_independence")
            if quality_checks.get(key)
        }
        agent_checks = quality.get("data_quality_agent", {}).get("checks", {})
        methodology_detail = agent_checks.get("measurement_methodology_documentation", {}).get("detail")
        if methodology_detail:
            unresolved["measurement_methodology_documentation"] = methodology_detail
        answer = (
            f"Known: publisher/source is {known['publisher']}; the source register records {known['license_and_permitted_use']} "
            f"The project describes daily PM2.5 in ug/m3. Unresolved: {unresolved}."
        )
        evidence.extend(
            [
                _report_evidence(
                    SOURCE_REGISTER_RELATIVE,
                    "candidate_id=PAQI-KHI-DAILY",
                    known,
                ),
                _report_evidence(
                    QUALITY_RELATIVE,
                    "$.checks.city_station_identity",
                    {"city_station_identity": unresolved.get("city_station_identity")},
                ),
                _report_evidence(
                    QUALITY_RELATIVE,
                    "$.checks.timestamp_and_resolution",
                    {"timestamp_and_resolution": unresolved.get("timestamp_and_resolution")},
                ),
                _report_evidence(
                    QUALITY_RELATIVE,
                    "$.checks.cross_source_independence",
                    {"cross_source_independence": unresolved.get("cross_source_independence")},
                ),
                _report_evidence(
                    QUALITY_RELATIVE,
                    "$.data_quality_agent.checks.measurement_methodology_documentation",
                    {"measurement_methodology_documentation": methodology_detail},
                ),
            ]
        )
        limitations.append("Station identity, monitor/network aggregation, exact daily window/timezone and sensor QA are not established.")
        limitations.append("Reuse of a candidate second source and two-source compliance remain unresolved.")
        status = "partially_answered"
    else:
        answer = ABSTENTION + " This local agent supports only questions about the loaded PAQI gold table, quality report, source register and forecast evaluation."
        status = "abstained"
        limitations.append("No matching evidence category was found; no unsupported inference was attempted.")

    return {
        "question": question,
        "answer": answer,
        "status": status,
        "evidence": evidence,
        "limitations": limitations,
        "generated_at": _utc_text(now),
        "data_as_of": data_as_of,
    }


def answer_question(
    question: str,
    *,
    root: Path = ROOT,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("Question must not be empty.")
    return _answer(question, root.resolve(), now)


def _format_readable(result: dict[str, Any]) -> str:
    lines = [
        result["answer"],
        f"Status: {result['status']}",
        f"Data as of: {result['data_as_of']} | Generated: {result['generated_at']}",
    ]
    if result["evidence"]:
        lines.append("Evidence:")
        for item in result["evidence"]:
            source = item["source_file"]
            locator = item.get("locator") or item.get("date_range") or ""
            lines.append(f"- {source} {locator}".rstrip())
            if item.get("row_ids"):
                lines.append(f"  row IDs: {', '.join(item['row_ids'])}")
            if item.get("sample_row_ids"):
                lines.append(f"  sample row IDs: {', '.join(item['sample_row_ids'])}")
    if result["limitations"]:
        lines.append("Limitations:")
        lines.extend(f"- {limitation}" for limitation in result["limitations"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer evidence-grounded questions about the historical PAQI dataset.")
    parser.add_argument("question", help="Question about the local PAQI data and forecast evidence")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--json", action="store_true", help="Alias for --format json")
    args = parser.parse_args(argv)
    try:
        result = answer_question(args.question)
    except (InsightAgentError, ValueError) as exc:
        print(f"Insight Agent error: {exc}", file=sys.stderr)
        return 1
    if args.json or args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    else:
        print(_format_readable(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
