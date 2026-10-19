from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import tempfile
import os
from dataclasses import dataclass
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pipeline import readiness
from pipeline.run import ROOT


GOLD_PATH = ROOT / "data" / "processed" / "gold_air_quality.csv"
QUALITY_PATH = ROOT / "data" / "quality" / "quality_report.json"
OUTPUT_ROOT = ROOT / "data" / "reports"
MODEL_PATH = OUTPUT_ROOT / "forecast_linear_model.json"
METRICS_PATH = OUTPUT_ROOT / "forecast_metrics.json"
PREDICTIONS_PATH = OUTPUT_ROOT / "forecast_predictions.csv"
FEATURE_LAGS_DAYS = (1, 2, 7)
SPLIT_BOUNDS = {
    "train": (date(2016, 10, 6), date(2022, 7, 12)),
    "validation": (date(2022, 7, 13), date(2023, 10, 6)),
    "test": (date(2023, 10, 7), date(2024, 12, 31)),
}
PREDICTION_FIELDS = [
    "row_id",
    "observed_date",
    "split",
    "actual_pm25_ug_m3",
    "persistence_prediction_ug_m3",
    "persistence_latest_observation_date",
    "persistence_input_age_days",
    "model_prediction_ug_m3",
    "model_residual_actual_minus_prediction",
    "persistence_residual_actual_minus_prediction",
    "lag_1_day_pm25",
    "lag_2_day_pm25",
    "lag_7_day_pm25",
    "model_latest_input_age_days",
    "model_input_status",
    "evaluation_status",
]


class ForecastingError(Exception):
    """Raised when the historical forecasting experiment cannot be run safely."""


@dataclass(frozen=True)
class Observation:
    row_id: str
    observed_date: date
    value: float | None


@dataclass(frozen=True)
class LinearModel:
    intercept: float
    coefficients: tuple[float, ...]
    feature_lags_days: tuple[int, ...]
    training_rows: int
    training_start: str
    training_end: str

    def predict(self, features: tuple[float, ...]) -> float:
        if len(features) != len(self.coefficients):
            raise ForecastingError("Feature count does not match fitted model.")
        return self.intercept + sum(
            coefficient * value
            for coefficient, value in zip(self.coefficients, features)
        )


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _atomic_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _read_observations(path: Path) -> list[Observation]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            required = {"row_id", "observed_date", "value", "source_id", "source_version"}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise ForecastingError(f"{path} is missing required gold-table columns.")
            rows: list[Observation] = []
            seen_dates: set[date] = set()
            source_ids: set[str] = set()
            source_versions: set[str] = set()
            for line_number, record in enumerate(reader, start=2):
                try:
                    observed_date = date.fromisoformat(record["observed_date"])
                except (TypeError, ValueError) as exc:
                    raise ForecastingError(
                        f"Gold row {line_number} has an invalid date."
                    ) from exc
                if observed_date in seen_dates:
                    raise ForecastingError(f"Duplicate gold date {observed_date}.")
                seen_dates.add(observed_date)
                raw_value = record["value"].strip()
                if raw_value:
                    try:
                        value = float(raw_value)
                    except ValueError as exc:
                        raise ForecastingError(
                            f"Gold row {line_number} has an invalid PM2.5 value."
                        ) from exc
                    if not math.isfinite(value) or value < 0:
                        raise ForecastingError(
                            f"Gold row {line_number} has a negative or non-finite value."
                        )
                else:
                    value = None
                rows.append(Observation(record["row_id"], observed_date, value))
                source_ids.add(record["source_id"])
                source_versions.add(record["source_version"])
    except (OSError, csv.Error) as exc:
        raise ForecastingError(f"Cannot read gold table {path}: {exc}") from exc
    if not rows:
        raise ForecastingError("Gold table has no records.")
    if len(source_ids) != 1 or source_ids != {"paqi_karachi_daily_pm25"}:
        raise ForecastingError("Forecasting requires only the approved PAQI source.")
    if source_versions != {"10.5281/zenodo.15845428"}:
        raise ForecastingError("Gold table is not the pinned PAQI Zenodo version.")
    if rows != sorted(rows, key=lambda item: item.observed_date):
        raise ForecastingError("Gold records must be ordered chronologically.")
    return rows


def split_name(observed_date: date) -> str:
    for name, (start, end) in SPLIT_BOUNDS.items():
        if start <= observed_date <= end:
            return name
    raise ForecastingError(f"Observation date {observed_date} is outside frozen splits.")


def feature_values(
    observations_by_date: dict[date, Observation],
    target_date: date,
    lag_days: tuple[int, ...] = FEATURE_LAGS_DAYS,
) -> tuple[float, ...] | None:
    """Return exact calendar-day lags only; never substitute a later or stale value."""
    result: list[float] = []
    for lag in lag_days:
        prior = observations_by_date.get(target_date - timedelta(days=lag))
        if prior is None or prior.value is None:
            return None
        result.append(prior.value)
    return tuple(result)


def persistence_input(
    observations: list[Observation], target_date: date
) -> tuple[float, date, int] | None:
    """Find the latest valid reading strictly before target_date."""
    for observation in reversed(observations):
        if observation.observed_date >= target_date:
            continue
        if observation.value is not None:
            age_days = (target_date - observation.observed_date).days
            return observation.value, observation.observed_date, age_days
    return None


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ForecastingError("Training design matrix is singular.")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[index][-1] for index in range(size)]


def fit_linear_model(
    examples: list[tuple[date, tuple[float, ...], float]],
    feature_lags_days: tuple[int, ...] = FEATURE_LAGS_DAYS,
) -> LinearModel:
    if not examples:
        raise ForecastingError("No complete training examples are available.")
    if any(split_name(target_date) != "train" for target_date, _, _ in examples):
        raise ForecastingError("Model fitting accepts training dates only.")
    feature_count = len(feature_lags_days)
    if any(len(features) != feature_count for _, features, _ in examples):
        raise ForecastingError("Training examples have inconsistent feature counts.")

    x_means = [
        statistics.fmean(features[index] for _, features, _ in examples)
        for index in range(feature_count)
    ]
    y_mean = statistics.fmean(target for _, _, target in examples)
    centered_x = [
        tuple(features[index] - x_means[index] for index in range(feature_count))
        for _, features, _ in examples
    ]
    centered_y = [target - y_mean for _, _, target in examples]
    covariance = [
        [
            sum(row[left] * row[right] for row in centered_x)
            for right in range(feature_count)
        ]
        for left in range(feature_count)
    ]
    cross_covariance = [
        sum(row[index] * target for row, target in zip(centered_x, centered_y))
        for index in range(feature_count)
    ]
    coefficients = tuple(_solve_linear_system(covariance, cross_covariance))
    intercept = y_mean - sum(
        coefficient * mean for coefficient, mean in zip(coefficients, x_means)
    )
    return LinearModel(
        intercept=intercept,
        coefficients=coefficients,
        feature_lags_days=feature_lags_days,
        training_rows=len(examples),
        training_start=min(item[0] for item in examples).isoformat(),
        training_end=max(item[0] for item in examples).isoformat(),
    )


def regression_metrics(actual: list[float], predicted: list[float]) -> dict[str, Any]:
    if len(actual) != len(predicted) or not actual:
        raise ForecastingError("Metrics require non-empty, equal-length actual/prediction arrays.")
    errors = [prediction - observation for observation, prediction in zip(actual, predicted)]
    return {
        "n": len(actual),
        "mae": statistics.fmean(abs(error) for error in errors),
        "rmse": math.sqrt(statistics.fmean(error * error for error in errors)),
    }


def _quantile(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ForecastingError("Quantile requires values and probability in [0, 1].")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] + fraction * (ordered[high] - ordered[low])


def run_experiment(
    gold_path: Path = GOLD_PATH,
    quality_path: Path = QUALITY_PATH,
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, Any]:
    try:
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ForecastingError(f"Cannot read pipeline quality report {quality_path}: {exc}") from exc
    if quality.get("quality_status") not in ("passed", "passed_with_warnings"):
        raise ForecastingError("Forecasting blocked: pipeline quality report is not passing.")
    if quality.get("source_id") != "paqi_karachi_daily_pm25":
        raise ForecastingError("Forecasting blocked: quality report is not for PAQI.")

    raw_path = ROOT / "data" / "raw" / "paqi_karachi_daily_pm25" / "10.5281_zenodo.15845428" / "PAQI_Daily_PM2.5_Data_2016-2024_in_Karachi.csv"
    cleaned_path = ROOT / "data" / "cleaned" / "paqi_karachi_daily_pm25.csv"
    readiness.audit_warehouse_layers(raw_path, cleaned_path, gold_path)
    observations = _read_observations(gold_path)
    if observations[0].observed_date != SPLIT_BOUNDS["train"][0] or observations[-1].observed_date != SPLIT_BOUNDS["test"][1]:
        raise ForecastingError("Gold date range does not match the frozen split endpoints.")
    observations_by_date = {row.observed_date: row for row in observations}

    rows: list[dict[str, Any]] = []
    training_examples: list[tuple[date, tuple[float, ...], float]] = []
    for observation in observations:
        features = feature_values(observations_by_date, observation.observed_date)
        if split_name(observation.observed_date) == "train" and observation.value is not None and features is not None:
            training_examples.append((observation.observed_date, features, observation.value))
    model = fit_linear_model(training_examples)

    for observation in observations:
        prior = persistence_input(observations, observation.observed_date)
        features = feature_values(observations_by_date, observation.observed_date)
        model_prediction = model.predict(features) if features is not None else None
        actual = observation.value
        rows.append(
            {
                "row_id": observation.row_id,
                "observed_date": observation.observed_date.isoformat(),
                "split": split_name(observation.observed_date),
                "actual": actual,
                "persistence_prediction": prior[0] if prior else None,
                "persistence_latest_observation_date": prior[1].isoformat() if prior else "",
                "persistence_input_age_days": prior[2] if prior else None,
                "model_prediction": model_prediction,
                "model_residual": actual - model_prediction if actual is not None and model_prediction is not None else None,
                "persistence_residual": actual - prior[0] if actual is not None and prior is not None else None,
                "features": features,
                "model_latest_input_age_days": 1 if features is not None else None,
                "model_input_status": "complete_lags" if features is not None else "missing_one_or_more_exact_day_lags",
            }
        )

    metric_splits: dict[str, Any] = {}
    validation_model_rows = [
        row for row in rows
        if row["split"] == "validation" and row["actual"] is not None and row["model_prediction"] is not None
    ]
    validation_residuals = [row["model_residual"] for row in validation_model_rows]
    if not validation_residuals:
        raise ForecastingError("No validation model predictions are available for calibration.")
    interval_low_residual = _quantile(validation_residuals, 0.05)
    interval_high_residual = _quantile(validation_residuals, 0.95)

    for split in ("validation", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        baseline_rows = [
            row for row in split_rows
            if row["actual"] is not None and row["persistence_prediction"] is not None
        ]
        model_rows = [
            row for row in split_rows
            if row["actual"] is not None and row["model_prediction"] is not None
        ]
        matched_model_rows = [
            row for row in model_rows if row["persistence_prediction"] is not None
        ]
        baseline_age_counts = {
            "immediate_previous_calendar_day": sum(
                row["persistence_input_age_days"] == 1 for row in baseline_rows
            ),
            "older_than_previous_calendar_day": sum(
                row["persistence_input_age_days"] > 1 for row in baseline_rows
            ),
            "no_prior_valid_reading": sum(
                row["actual"] is not None and row["persistence_prediction"] is None
                for row in split_rows
            ),
            "missing_target": sum(row["actual"] is None for row in split_rows),
        }
        baseline_all_metrics = regression_metrics(
            [row["actual"] for row in baseline_rows],
            [row["persistence_prediction"] for row in baseline_rows],
        )
        model_metrics = regression_metrics(
            [row["actual"] for row in model_rows],
            [row["model_prediction"] for row in model_rows],
        )
        baseline_matched_metrics = regression_metrics(
            [row["actual"] for row in matched_model_rows],
            [row["persistence_prediction"] for row in matched_model_rows],
        )
        years = sorted({row["observed_date"][:4] for row in split_rows})
        by_year: dict[str, Any] = {}
        for year in years:
            year_rows = [row for row in split_rows if row["observed_date"][:4] == year]
            year_model_rows = [
                row for row in year_rows
                if row["actual"] is not None and row["model_prediction"] is not None
            ]
            year_matched_rows = [
                row for row in year_model_rows
                if row["persistence_prediction"] is not None
            ]
            year_model_metrics = (
                regression_metrics(
                    [row["actual"] for row in year_model_rows],
                    [row["model_prediction"] for row in year_model_rows],
                )
                if year_model_rows else None
            )
            year_persistence_all = [
                row for row in year_rows
                if row["actual"] is not None and row["persistence_prediction"] is not None
            ]
            year_persistence_metrics = (
                regression_metrics(
                    [row["actual"] for row in year_persistence_all],
                    [row["persistence_prediction"] for row in year_persistence_all],
                )
                if year_persistence_all else None
            )
            year_persistence_matched = (
                regression_metrics(
                    [row["actual"] for row in year_matched_rows],
                    [row["persistence_prediction"] for row in year_matched_rows],
                )
                if year_matched_rows else None
            )
            by_year[year] = {
                "persistence_all_eligible_targets": year_persistence_metrics,
                "linear_model": year_model_metrics,
                "persistence_on_model_matched_targets": year_persistence_matched,
                "paired_model_minus_persistence": (
                    {
                        "n": year_model_metrics["n"],
                        "mae_difference": year_model_metrics["mae"] - year_persistence_matched["mae"],
                        "rmse_difference": year_model_metrics["rmse"] - year_persistence_matched["rmse"],
                    }
                    if year_model_metrics is not None and year_persistence_matched is not None
                    else None
                ),
            }
        interval_test_rows = [
            row for row in model_rows if split == "test"
        ]
        interval_hits = sum(
            row["model_prediction"] + interval_low_residual
            <= row["actual"]
            <= row["model_prediction"] + interval_high_residual
            for row in interval_test_rows
        )
        metric_splits[split] = {
            "dates": {
                "start": SPLIT_BOUNDS[split][0].isoformat(),
                "end": SPLIT_BOUNDS[split][1].isoformat(),
            },
            "persistence_all_eligible_targets": baseline_all_metrics,
            "linear_model": model_metrics,
            "persistence_on_model_matched_targets": baseline_matched_metrics,
            "paired_model_minus_persistence": {
                "n": model_metrics["n"],
                "mae_difference": model_metrics["mae"] - baseline_matched_metrics["mae"],
                "rmse_difference": model_metrics["rmse"] - baseline_matched_metrics["rmse"],
            },
            "persistence_input_age_counts": baseline_age_counts,
            "model_complete_lag_target_count": len(model_rows),
            "model_excluded_for_missing_lag_count": sum(
                row["actual"] is not None and row["model_prediction"] is None
                for row in split_rows
            ),
            "by_target_year": by_year,
            "empirical_validation_residual_interval": {
                "source_split": "validation",
                "validation_residual_count": len(validation_residuals),
                "residual_quantiles": {
                    "lower_5_percent": interval_low_residual,
                    "upper_95_percent": interval_high_residual,
                },
                "test_coverage": (
                    interval_hits / len(interval_test_rows) if split == "test" else None
                ),
                "test_hits": interval_hits if split == "test" else None,
                "test_n": len(interval_test_rows) if split == "test" else None,
                "interpretation": "Historical empirical interval from validation residuals; not a guaranteed probabilistic forecast.",
            },
        }

    metrics = {
        "experiment": "PAQI Karachi daily PM2.5 next-day historical forecast",
        "source_id": quality["source_id"],
        "source_version": quality.get("source_version", "10.5281/zenodo.15845428"),
        "source_file_sha256": quality.get("source_file_sha256"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "target": "published PAQI Karachi daily PM2.5 series value; not a sensor-specific or citywide exposure estimate",
        "unit": "µg/m³",
        "prediction_horizon": "next reported daily series value",
        "split_boundaries": {
            split: {"start": bounds[0].isoformat(), "end": bounds[1].isoformat()}
            for split, bounds in SPLIT_BOUNDS.items()
        },
        "baseline": "latest valid PM2.5 observation strictly before target date; input date and age recorded",
        "model": {
            "type": "ordinary least squares linear regression with intercept",
            "features": [f"PM2.5 at exact calendar lag {lag} day(s)" for lag in FEATURE_LAGS_DAYS],
            "missing_lags": "Exclude target from model fitting/evaluation if any exact lag is missing; no imputation.",
            "training_rows": model.training_rows,
            "training_dates": {"start": model.training_start, "end": model.training_end},
            "learned_preprocessing": "None; coefficients fit on train dates only.",
            "test_tuning": "None; model specification fixed before test evaluation.",
        },
        "metrics": {
            "primary": "MAE",
            "secondary": "RMSE",
            "residual_convention": "actual minus prediction in per-date output",
        },
        "splits": metric_splits,
        "limitations": [
            "Historical backtest ends 2024-12-31 and is not a current forecast.",
            "PAQI station identity, aggregation, precise timezone/window, QA, blank-value meaning, and method history remain undocumented.",
            "Two-source compliance is not established; only the approved PAQI source is used.",
        ],
    }

    model_artifact = {
        "model_type": "ordinary_least_squares_linear_regression",
        "intercept": model.intercept,
        "feature_lags_days": list(model.feature_lags_days),
        "coefficients": list(model.coefficients),
        "training_rows": model.training_rows,
        "training_dates": {"start": model.training_start, "end": model.training_end},
        "source_version": "10.5281/zenodo.15845428",
        "source_file_sha256": quality.get("source_file_sha256"),
        "unit": "µg/m³",
        "learned_preprocessing": None,
    }
    prediction_records = []
    for row in rows:
        feature_map = dict(zip(FEATURE_LAGS_DAYS, row["features"] or ()))
        prediction_records.append(
            {
                "row_id": row["row_id"],
                "observed_date": row["observed_date"],
                "split": row["split"],
                "actual_pm25_ug_m3": "" if row["actual"] is None else row["actual"],
                "persistence_prediction_ug_m3": "" if row["persistence_prediction"] is None else row["persistence_prediction"],
                "persistence_latest_observation_date": row["persistence_latest_observation_date"],
                "persistence_input_age_days": "" if row["persistence_input_age_days"] is None else row["persistence_input_age_days"],
                "model_prediction_ug_m3": "" if row["model_prediction"] is None else row["model_prediction"],
                "model_residual_actual_minus_prediction": "" if row["model_residual"] is None else row["model_residual"],
                "persistence_residual_actual_minus_prediction": "" if row["persistence_residual"] is None else row["persistence_residual"],
                "lag_1_day_pm25": "" if 1 not in feature_map else feature_map[1],
                "lag_2_day_pm25": "" if 2 not in feature_map else feature_map[2],
                "lag_7_day_pm25": "" if 7 not in feature_map else feature_map[7],
                "model_latest_input_age_days": "" if row["model_latest_input_age_days"] is None else row["model_latest_input_age_days"],
                "model_input_status": row["model_input_status"],
                "evaluation_status": (
                    "missing_target_not_scored"
                    if row["actual"] is None
                    else "training_in_sample_not_scored"
                    if row["split"] == "train"
                    else "no_prior_valid_reading"
                    if row["persistence_prediction"] is None
                    else "model_excluded_missing_lag"
                    if row["model_prediction"] is None
                    else "evaluated"
                ),
            }
        )

    _atomic_json(output_root / MODEL_PATH.name, model_artifact)
    _atomic_json(output_root / METRICS_PATH.name, metrics)
    _atomic_csv(output_root / PREDICTIONS_PATH.name, PREDICTION_FIELDS, prediction_records)
    return metrics


def main() -> int:
    try:
        metrics = run_experiment()
    except (ForecastingError, readiness.ReadinessAuditError, OSError, csv.Error) as exc:
        print(f"Forecasting failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(metrics["splits"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
