from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pipeline.run import ROOT, sha256_file


class ReadinessAuditError(Exception):
    """Raised when warehouse layers do not preserve source data and lineage."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None:
                raise ReadinessAuditError(f"{path} has no header.")
            return list(reader)
    except (OSError, csv.Error) as exc:
        raise ReadinessAuditError(f"Cannot read {path}: {exc}") from exc


def _numeric_value(raw: str, location: str) -> float | None:
    if raw.strip() == "":
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ReadinessAuditError(f"{location} contains an invalid numeric value.") from exc
    if not math.isfinite(value) or value < 0:
        raise ReadinessAuditError(f"{location} contains a non-finite or negative value.")
    return value


def audit_warehouse_layers(
    raw_path: Path,
    cleaned_path: Path,
    gold_path: Path,
) -> dict[str, Any]:
    raw_records = _read_csv(raw_path)
    cleaned_records = _read_csv(cleaned_path)
    gold_records = _read_csv(gold_path)
    source_hash = sha256_file(raw_path)

    if not (len(raw_records) == len(cleaned_records) == len(gold_records)):
        raise ReadinessAuditError(
            "Raw, cleaned, and gold row counts differ; source records may have been lost."
        )

    values: list[float] = []
    dates: list[date] = []
    missing_count = 0
    raw_value_counts: Counter[float] = Counter()
    last_valid_date: date | None = None
    split_sizes = {
        "train": math.floor(len(raw_records) * 0.70),
        "validation": math.floor(len(raw_records) * 0.15),
    }
    split_sizes["test"] = len(raw_records) - sum(split_sizes.values())
    split_bounds: dict[str, tuple[int, int]] = {
        "train": (0, split_sizes["train"]),
        "validation": (
            split_sizes["train"],
            split_sizes["train"] + split_sizes["validation"],
        ),
        "test": (
            split_sizes["train"] + split_sizes["validation"],
            len(raw_records),
        ),
    }
    split_evaluation: dict[str, dict[str, Any]] = {
        name: {
            "calendar_rows": end - start,
            "numeric_targets": 0,
            "persistence_targets_with_prior_valid_value": 0,
            "persistence_targets_with_immediate_previous_day_value": 0,
            "persistence_targets_with_stale_previous_value": 0,
            "stale_predictor_examples": [],
            "start_date": None,
            "end_date": None,
        }
        for name, (start, end) in split_bounds.items()
    }
    dates_seen: set[date] = set()
    longest_equal_run = 0
    current_equal_run = 0
    previous_numeric_date: date | None = None
    previous_numeric_value: float | None = None

    for index, (raw, cleaned, gold) in enumerate(
        zip(raw_records, cleaned_records, gold_records)
    ):
        location = f"record {index + 1}"
        try:
            observed_date = date.fromisoformat(raw["date"])
        except (KeyError, ValueError) as exc:
            raise ReadinessAuditError(f"{location} has an invalid raw date.") from exc
        dates.append(observed_date)
        if observed_date in dates_seen:
            raise ReadinessAuditError(f"{location} duplicates date {observed_date}.")
        dates_seen.add(observed_date)
        if raw["date"] != cleaned.get("observed_date") or raw["date"] != gold.get("observed_date"):
            raise ReadinessAuditError(f"{location} date differs across raw/cleaned/gold.")
        shared_fields = (
            "source_id",
            "source_version",
            "source_file_sha256",
            "source_record_key",
            "observed_date",
            "city",
            "station_id",
            "pollutant",
            "value",
            "source_value_raw",
            "quality_flag",
            "unit",
            "time_resolution",
            "timezone",
        )
        if any(cleaned.get(field) != gold.get(field) for field in shared_fields):
            raise ReadinessAuditError(f"{location} cleaned/gold lineage fields differ.")
        raw_value = raw.get("pm25_concentration_ug_per_m3")
        if raw_value is None or raw_value != cleaned.get("source_value_raw") or raw_value != gold.get("source_value_raw"):
            raise ReadinessAuditError(f"{location} source value differs across warehouse layers.")
        value = _numeric_value(raw_value, location)
        normalized = cleaned.get("value")
        if value is None:
            missing_count += 1
            if normalized != "" or gold.get("value") != "" or cleaned.get("quality_flag") != "missing_pm25_value":
                raise ReadinessAuditError(f"{location} missing-value flag/value was not preserved.")
            current_equal_run = 0
        else:
            values.append(value)
            raw_value_counts[value] += 1
            if normalized is None or gold.get("value") != normalized:
                raise ReadinessAuditError(f"{location} normalized value differs in gold.")
            try:
                normalized_value = float(normalized)
            except (TypeError, ValueError) as exc:
                raise ReadinessAuditError(f"{location} normalized value is invalid.") from exc
            if normalized_value != value:
                raise ReadinessAuditError(f"{location} numeric value differs from raw source.")
            if cleaned.get("quality_flag", "") or gold.get("quality_flag", ""):
                raise ReadinessAuditError(f"{location} numeric value has an unexpected quality flag.")
            if (
                previous_numeric_date is not None
                and observed_date - previous_numeric_date == timedelta(days=1)
                and value == previous_numeric_value
            ):
                current_equal_run += 1
            else:
                current_equal_run = 1
            longest_equal_run = max(longest_equal_run, current_equal_run)
            previous_numeric_date = observed_date
            previous_numeric_value = value
        expected_key = f"csv_data_record_{index + 1:07d}"
        if cleaned.get("source_record_key") != expected_key or gold.get("source_record_key") != expected_key:
            raise ReadinessAuditError(f"{location} source record lineage key is unstable.")
        if cleaned.get("source_file_sha256") != source_hash or gold.get("source_file_sha256") != source_hash:
            raise ReadinessAuditError(f"{location} source-file SHA-256 lineage does not match.")
        expected_row_id = hashlib.sha256(
            f"{gold.get('source_id')}|{gold.get('source_version')}|{expected_key}".encode("utf-8")
        ).hexdigest()
        if gold.get("row_id") != expected_row_id:
            raise ReadinessAuditError(f"{location} gold row_id is invalid.")
        split_name = next(
            name for name, (start, end) in split_bounds.items() if start <= index < end
        )
        split_row = split_evaluation[split_name]
        split_row["start_date"] = split_row["start_date"] or observed_date.isoformat()
        split_row["end_date"] = observed_date.isoformat()
        if value is not None:
            split_row["numeric_targets"] += 1
            if last_valid_date is not None:
                split_row["persistence_targets_with_prior_valid_value"] += 1
                age_days = (observed_date - last_valid_date).days
                if age_days == 1:
                    split_row["persistence_targets_with_immediate_previous_day_value"] += 1
                else:
                    split_row["persistence_targets_with_stale_previous_value"] += 1
                    split_row["stale_predictor_examples"].append(
                        {
                            "target_date": observed_date.isoformat(),
                            "previous_valid_date": last_valid_date.isoformat(),
                            "age_days": age_days,
                        }
                    )
            last_valid_date = observed_date

    if dates != sorted(dates):
        raise ReadinessAuditError("Raw observations are not in chronological order.")
    missing_dates: list[str] = []
    if dates:
        current = dates[0]
        while current <= dates[-1]:
            if current not in dates_seen:
                missing_dates.append(current.isoformat())
            current += timedelta(days=1)
    repeated_values = {
        str(value): count for value, count in raw_value_counts.items() if count > 1
    }
    all_values_one_decimal = all(
        abs(value * 10 - round(value * 10)) < 1e-9 for value in values
    )
    return {
        "row_count": len(raw_records),
        "numeric_count": len(values),
        "missing_value_count": missing_count,
        "negative_count": 0,
        "non_finite_count": 0,
        "date_count": len(dates_seen),
        "first_date": dates[0].isoformat() if dates else None,
        "last_date": dates[-1].isoformat() if dates else None,
        "missing_dates_within_observed_span": missing_dates,
        "date_ordered": dates == sorted(dates),
        "numeric_statistics_ug_m3": {
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "median": statistics.median(values) if values else None,
            "mean": statistics.mean(values) if values else None,
            "standard_deviation_sample": statistics.stdev(values) if len(values) > 1 else None,
            "standard_deviation_population": statistics.pstdev(values) if values else None,
        },
        "value_repetition": {
            "distinct_numeric_values": len(raw_value_counts),
            "numeric_rows_with_a_repeated_magnitude": sum(
                count for count in raw_value_counts.values() if count > 1
            ),
            "distinct_magnitudes_repeated": len(repeated_values),
            "maximum_occurrences_of_one_magnitude": max(raw_value_counts.values(), default=0),
            "longest_consecutive_identical_value_run": longest_equal_run,
            "all_numeric_readings_have_one_decimal_place": all_values_one_decimal,
        },
        "splits_by_chronological_row_position": split_evaluation,
        "lineage": {
            "raw_sha256": source_hash,
            "raw_cleaned_gold_values_and_dates_match_in_order": True,
            "all_gold_row_ids_recomputed_and_matched": True,
            "all_source_record_keys_and_file_hashes_matched": True,
        },
    }


def main() -> int:
    data_root = ROOT / "data"
    try:
        summary = audit_warehouse_layers(
            data_root
            / "raw"
            / "paqi_karachi_daily_pm25"
            / "10.5281_zenodo.15845428"
            / "PAQI_Daily_PM2.5_Data_2016-2024_in_Karachi.csv",
            data_root / "cleaned" / "paqi_karachi_daily_pm25.csv",
            data_root / "processed" / "gold_air_quality.csv",
        )
    except ReadinessAuditError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
