from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"
DATA_ROOT = ROOT / "data"
MANIFEST_FIELDS = [
    "run_id",
    "source_id",
    "publisher",
    "source_url",
    "request_query",
    "license",
    "version",
    "filename",
    "raw_path",
    "fetch_timestamp_utc",
    "recorded_at_utc",
    "acquisition_status",
    "sha256",
    "md5",
    "byte_size",
    "http_status",
]
CLEAN_FIELDS = [
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
]
GOLD_FIELDS = [
    "row_id",
    *CLEAN_FIELDS,
    "source_url",
]


class PipelineError(Exception):
    """An explicit, reportable pipeline failure."""


@dataclass(frozen=True)
class DownloadResult:
    raw_path: Path
    sha256: str
    md5: str
    byte_size: int
    fetched_at_utc: str
    http_status: int
    acquisition_status: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as temporary:
        json.dump(payload, temporary, indent=2, ensure_ascii=False)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def atomic_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as temporary:
        writer = csv.DictWriter(temporary, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or CONFIG_PATH
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Cannot read source configuration {path}: {exc}") from exc
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise PipelineError("Configuration schema_version must be 1.")
    timeout = config.get("request_timeout_seconds")
    if not isinstance(timeout, int) or timeout < 1:
        raise PipelineError("request_timeout_seconds must be a positive integer.")
    freshness_days = config.get("freshness_warning_days")
    if not isinstance(freshness_days, int) or freshness_days < 0:
        raise PipelineError("freshness_warning_days must be a non-negative integer.")
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PipelineError("Configuration must contain a non-empty sources list.")
    if not all(isinstance(source, dict) for source in sources):
        raise PipelineError("Every configured source must be a JSON object.")
    enabled = [source for source in sources if source.get("enabled") is True]
    if len(enabled) != 1 or enabled[0].get("source_id") != "paqi_karachi_daily_pm25":
        raise PipelineError(
            "Only the reviewed, version-pinned PAQI source may be enabled in Phase 2."
        )
    source = enabled[0]
    required = (
        "source_id",
        "publisher",
        "source_url",
        "metadata_url",
        "download_url",
        "filename",
        "license",
        "license_url",
        "version",
        "expected_size_bytes",
        "expected_md5",
        "expected_zenodo_license_id",
        "expected_header",
        "city",
        "pollutant",
        "unit",
        "time_resolution",
        "attribution",
        "request_description",
    )
    missing = [field for field in required if not source.get(field)]
    if missing:
        raise PipelineError(f"Enabled source is missing fields: {', '.join(missing)}")
    if source["license"] != "CC BY 4.0" or source["version"] != "10.5281/zenodo.15845428":
        raise PipelineError("PAQI licence or pinned version differs from reviewed evidence.")
    if not re.fullmatch(r"[0-9a-f]{32}", source["expected_md5"]):
        raise PipelineError("expected_md5 must be 32 lowercase hexadecimal characters.")
    if not isinstance(source["expected_size_bytes"], int):
        raise PipelineError("expected_size_bytes must be an integer.")
    if source["expected_size_bytes"] <= 0:
        raise PipelineError("expected_size_bytes must be positive.")
    if source["expected_header"] != ["date", "pm25_concentration_ug_per_m3"]:
        raise PipelineError("PAQI source header differs from the verified source schema.")
    for field in ("metadata_url", "download_url", "source_url", "license_url"):
        if not str(source[field]).startswith("https://"):
            raise PipelineError(f"{field} must use HTTPS.")
    return config


def request_json(url: str, timeout: int) -> tuple[dict[str, Any], int]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "HackInsight26-data-pipeline/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise PipelineError("Zenodo metadata response exceeded the 2 MiB safety limit.")
            payload = json.loads(body.decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Source metadata request failed for {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PipelineError("Zenodo metadata response must be a JSON object.")
    return payload, status


def validate_source_availability(source: dict[str, Any], timeout: int) -> tuple[dict[str, Any], int]:
    metadata, status = request_json(source["metadata_url"], timeout)
    validate_metadata(source, metadata)
    files = metadata["files"]
    match = next(item for item in files if item.get("key") == source["filename"])
    return match, status


def validate_metadata(source: dict[str, Any], metadata: dict[str, Any]) -> None:
    if metadata.get("id") != 15845428 or metadata.get("doi") != source["version"]:
        raise PipelineError("Zenodo metadata does not match the pinned record/version DOI.")
    zenodo_license = (metadata.get("metadata") or {}).get("license") or {}
    if zenodo_license.get("id") != source["expected_zenodo_license_id"]:
        raise PipelineError(
            f"Zenodo licence mismatch: expected {source['expected_zenodo_license_id']!r}, "
            f"received {zenodo_license.get('id')!r}."
        )
    files = metadata.get("files")
    if not isinstance(files, list):
        raise PipelineError("Zenodo metadata has no files list.")
    match = next((item for item in files if item.get("key") == source["filename"]), None)
    if not match:
        raise PipelineError(f"Pinned file {source['filename']} is absent from Zenodo metadata.")
    if match.get("size") != source["expected_size_bytes"]:
        raise PipelineError("Zenodo file size differs from the reviewed pinned metadata.")
    checksum = str(match.get("checksum", ""))
    if checksum.lower() != f"md5:{source['expected_md5']}":
        raise PipelineError("Zenodo file checksum differs from the reviewed pinned metadata.")


def download_or_reuse(
    source: dict[str, Any],
    timeout: int,
    metadata_file: dict[str, Any],
) -> DownloadResult:
    raw_dir = DATA_ROOT / "raw" / source["source_id"] / source["version"].replace("/", "_")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / source["filename"]
    sidecar_path = raw_path.with_suffix(raw_path.suffix + ".provenance.json")
    if raw_path.exists():
        actual_size = raw_path.stat().st_size
        actual_md5 = md5_file(raw_path)
        actual_sha256 = sha256_file(raw_path)
        if actual_size != source["expected_size_bytes"] or actual_md5 != source["expected_md5"]:
            raise PipelineError(
                f"Cached raw file failed pinned size/MD5 verification: {raw_path}. "
                "It was preserved and not overwritten."
            )
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            fetched_at = sidecar["fetch_timestamp_utc"]
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise PipelineError(
                f"Valid cached bytes lack acquisition provenance sidecar: {sidecar_path}"
            ) from exc
        return DownloadResult(
            raw_path,
            actual_sha256,
            actual_md5,
            actual_size,
            fetched_at,
            200,
            "reused_cached_file",
        )

    request = urllib.request.Request(
        source["download_url"],
        headers={"User-Agent": "HackInsight26-data-pipeline/1.0"},
        method="GET",
    )
    fetched_at = utc_text()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read(source["expected_size_bytes"] + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PipelineError(f"Dataset acquisition failed for {source['download_url']}: {exc}") from exc
    if status != 200:
        raise PipelineError(f"Dataset acquisition returned HTTP {status}.")
    if len(body) > source["expected_size_bytes"]:
        raise PipelineError("Dataset response exceeded the pinned expected byte size.")
    actual_md5 = hashlib.md5(body).hexdigest()
    if len(body) != source["expected_size_bytes"] or actual_md5 != source["expected_md5"]:
        raise PipelineError(
            "Downloaded file failed pinned byte-size/MD5 verification; "
            "the incomplete or changed response was not retained as source data."
        )
    actual_sha256 = hashlib.sha256(body).hexdigest()
    fd, temporary_name = tempfile.mkstemp(prefix=".download-", dir=raw_dir)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        if raw_path.exists():
            raise PipelineError(f"Refusing to overwrite existing raw evidence {raw_path}.")
        os.replace(temporary_path, raw_path)
        atomic_json(
            sidecar_path,
            {
                "source_id": source["source_id"],
                "publisher": source["publisher"],
                "source_url": source["source_url"],
                "download_url": source["download_url"],
                "version": source["version"],
                "license": source["license"],
                "fetch_timestamp_utc": fetched_at,
                "acquisition_status": "downloaded",
                "http_status": status,
                "byte_size": len(body),
                "md5": actual_md5,
                "sha256": actual_sha256,
                "zenodo_metadata_checksum": metadata_file.get("checksum"),
            },
        )
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return DownloadResult(
        raw_path,
        actual_sha256,
        actual_md5,
        len(body),
        fetched_at,
        status,
        "downloaded",
    )


def append_manifest(
    path: Path,
    *,
    run_id: str,
    source: dict[str, Any],
    result: DownloadResult,
    metadata_url: str,
    metadata_status: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    request_query = (
        f"GET {metadata_url} -> HTTP {metadata_status}; "
        f"GET {source['download_url']} (version={source['version']}, "
        f"filename={source['filename']}); {source['request_description']}"
    )
    row = {
        "run_id": run_id,
        "source_id": source["source_id"],
        "publisher": source["publisher"],
        "source_url": source["source_url"],
        "request_query": request_query,
        "license": source["license"],
        "version": source["version"],
        "filename": source["filename"],
        "raw_path": (
            result.raw_path.relative_to(ROOT).as_posix()
            if result.raw_path.is_relative_to(ROOT)
            else result.raw_path.as_posix()
        ),
        "fetch_timestamp_utc": result.fetched_at_utc,
        "recorded_at_utc": utc_text(),
        "acquisition_status": result.acquisition_status,
        "sha256": result.sha256,
        "md5": result.md5,
        "byte_size": result.byte_size,
        "http_status": result.http_status,
    }
    with path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def parse_and_clean(
    raw_path: Path,
    source: dict[str, Any],
    source_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    date_counts: dict[str, int] = {}
    malformed_row_count = 0
    invalid_date_count = 0
    invalid_value_count = 0
    missing_value_count = 0
    required_header = source["expected_header"]
    try:
        stream = raw_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise PipelineError(f"Cannot open downloaded CSV {raw_path}: {exc}") from exc
    with stream:
        reader = csv.reader(stream, strict=True)
        try:
            header = next(reader)
        except (StopIteration, csv.Error) as exc:
            raise PipelineError("Source CSV is empty or malformed before its header.") from exc
        if header != required_header:
            raise PipelineError(f"Unexpected CSV header: {header!r}; expected {required_header!r}.")
        for record_number, fields in enumerate(reader, start=1):
            source_record_key = f"csv_data_record_{record_number:07d}"
            if len(fields) != len(required_header):
                malformed_row_count += 1
                rejected.append(
                    {
                        "source_record_key": source_record_key,
                        "raw_fields_json": json.dumps(fields, ensure_ascii=False),
                        "rejection_reason": f"expected {len(required_header)} columns, found {len(fields)}",
                    }
                )
                continue
            raw_date, raw_value = fields
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
                    raise ValueError("date must use YYYY-MM-DD")
                parsed_date = date.fromisoformat(raw_date)
                if parsed_date.isoformat() != raw_date:
                    raise ValueError("date is not canonical ISO format")
            except ValueError as exc:
                invalid_date_count += 1
                rejected.append(
                    {
                        "source_record_key": source_record_key,
                        "raw_fields_json": json.dumps(fields, ensure_ascii=False),
                        "rejection_reason": f"invalid date: {exc}",
                    }
                )
                continue
            quality_flag = ""
            if raw_value.strip() == "":
                value_text = ""
                quality_flag = "missing_pm25_value"
                missing_value_count += 1
            else:
                try:
                    value = Decimal(raw_value)
                    if not value.is_finite():
                        raise ValueError("value must be finite")
                    if value < 0:
                        raise ValueError("PM2.5 concentration cannot be negative")
                    numeric_float = float(value)
                    if not math.isfinite(numeric_float) or (
                        value != 0 and numeric_float == 0
                    ):
                        raise ValueError("value is outside supported numeric range")
                    value_text = canonical_decimal_text(value)
                except (ValueError, InvalidOperation) as exc:
                    invalid_value_count += 1
                    rejected.append(
                        {
                            "source_record_key": source_record_key,
                            "raw_fields_json": json.dumps(fields, ensure_ascii=False),
                            "rejection_reason": f"invalid PM2.5 value: {exc}",
                        }
                    )
                    continue
            iso_date = parsed_date.isoformat()
            date_counts[iso_date] = date_counts.get(iso_date, 0) + 1
            cleaned.append(
                {
                    "source_id": source["source_id"],
                    "source_version": source["version"],
                    "source_file_sha256": source_sha256,
                    "source_record_key": source_record_key,
                    "observed_date": iso_date,
                    "city": source["city"],
                    "station_id": "",
                    "pollutant": source["pollutant"],
                    "value": value_text,
                    "source_value_raw": raw_value,
                    "quality_flag": quality_flag,
                    "unit": source["unit"],
                    "time_resolution": source["time_resolution"],
                    "timezone": source["timezone"] or "",
                }
            )
    duplicate_dates = {key: count for key, count in date_counts.items() if count > 1}
    if not cleaned and not rejected:
        raise PipelineError("CSV has a valid header but contains no data records.")
    return cleaned, rejected, {
        "input_record_count": len(cleaned) + len(rejected),
        "valid_record_count": len(cleaned),
        "rejected_record_count": len(rejected),
        "duplicate_dates": duplicate_dates,
        "unique_date_count": len(date_counts),
        "date_counts": date_counts,
        "malformed_row_count": malformed_row_count,
        "invalid_date_count": invalid_date_count,
        "invalid_value_count": invalid_value_count,
        "missing_value_count": missing_value_count,
    }


def make_gold(cleaned: list[dict[str, Any]], source_url: str) -> list[dict[str, Any]]:
    gold: list[dict[str, Any]] = []
    for record in cleaned:
        identity = "|".join(
            (
                record["source_id"],
                record["source_version"],
                record["source_record_key"],
            )
        )
        row_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        gold.append({"row_id": row_id, **record, "source_url": source_url})
    return gold


def calculate_quality(
    cleaned: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    parse_stats: dict[str, Any],
    *,
    source: dict[str, Any],
    raw_sha256: str,
    warning_days: int,
) -> dict[str, Any]:
    observed_dates = sorted(parse_stats["date_counts"])
    missing_dates: list[str] = []
    if observed_dates:
        first = date.fromisoformat(observed_dates[0])
        last = date.fromisoformat(observed_dates[-1])
        current = first
        while current <= last:
            text = current.isoformat()
            if text not in parse_stats["date_counts"]:
                missing_dates.append(text)
            current = date.fromordinal(current.toordinal() + 1)
        latest = date.fromisoformat(observed_dates[-1])
        age_days = (utc_now().date() - latest).days
    else:
        first = last = None
        age_days = None
    checks = {
        "schema": {"status": "pass", "detail": "Header exactly matches configured source schema."},
        "source_row_shape": {
            "status": "fail" if parse_stats["malformed_row_count"] else "pass",
            "detail": f"{parse_stats['malformed_row_count']} records have unexpected column counts.",
        },
        "date_parse": {
            "status": "fail" if parse_stats["invalid_date_count"] else "pass",
            "detail": f"{parse_stats['invalid_date_count']} invalid date values; rejects are preserved separately.",
        },
        "nonnegative_finite_pm25": {
            "status": "fail" if parse_stats["invalid_value_count"] else "pass",
            "detail": f"{parse_stats['invalid_value_count']} invalid PM2.5 values; rejects are preserved separately.",
        },
        "measurement_missingness": {
            "status": "warning" if parse_stats["missing_value_count"] else "pass",
            "detail": (
                f"{parse_stats['missing_value_count']} source rows have blank PM2.5 values; "
                "rows remain in cleaned/gold with quality flags."
            ),
        },
        "row_id_uniqueness": {
            "status": "pass" if len({r['source_record_key'] for r in cleaned}) == len(cleaned) else "fail",
            "detail": "Source record key is based on pinned CSV data-record ordinal.",
        },
        "date_uniqueness": {
            "status": "pass" if not parse_stats["duplicate_dates"] else "fail",
            "detail": f"{len(parse_stats['duplicate_dates'])} dates occur more than once.",
        },
        "missing_dates_within_observed_span": {
            "status": "warning" if missing_dates else "pass",
            "detail": f"{len(missing_dates)} absent calendar dates between observed endpoints; no imputation applied.",
        },
        "city_station_identity": {
            "status": "warning",
            "detail": "Publisher provides no station identifier in the declared schema; city is publisher-labeled Karachi.",
        },
        "timestamp_and_resolution": {
            "status": "warning",
            "detail": "Date-only daily records; publisher describes 24-hour averages but timezone/window is unspecified.",
        },
        "cross_source_independence": {
            "status": "not_run",
            "detail": "Only one cleared source is enabled; EPA reuse/provenance and OpenAQ lineage are unresolved.",
        },
        "freshness": {
            "status": "warning" if age_days is not None and age_days > warning_days else "pass",
            "detail": (
                f"Latest observation {observed_dates[-1]}; {age_days} days before current UTC date. "
                "A fresh fetch of this static historical dataset does not mean fresh observations."
                if observed_dates
                else "No valid observation date available."
            ),
        },
    }
    critical_failures = [
        name for name, check in checks.items() if check["status"] == "fail"
    ]
    return {
        "generated_at_utc": utc_text(),
        "source_id": source["source_id"],
        "source_version": source["version"],
        "source_file_sha256": raw_sha256,
        "publisher": source["publisher"],
        "license": source["license"],
        "attribution": source["attribution"],
        "input_record_count": parse_stats["input_record_count"],
        "valid_record_count": parse_stats["valid_record_count"],
        "numeric_pm25_record_count": (
            parse_stats["valid_record_count"] - parse_stats["missing_value_count"]
        ),
        "rejected_record_count": len(rejected),
        "missing_measurement_count": parse_stats["missing_value_count"],
        "cleaned_record_count": len(cleaned),
        "gold_record_count": len(cleaned),
        "first_observation_date": first.isoformat() if first else None,
        "last_observation_date": last.isoformat() if last else None,
        "unique_observation_dates": parse_stats["unique_date_count"],
        "duplicate_dates": parse_stats["duplicate_dates"],
        "missing_dates_within_observed_span": missing_dates,
        "checks": checks,
        "critical_failures": critical_failures,
        "quality_status": "failed" if critical_failures else "passed_with_warnings",
        "transformations": [
            "Parsed the pinned UTF-8 CSV with strict header and column-count checks.",
            "Parsed date as a date-only ISO value; no timezone or timestamp was invented.",
            "Parsed PM2.5 as a finite number; original unit µg/m³ retained without conversion.",
            "Retained blank PM2.5 source values as blank normalized values with missing_pm25_value quality flags.",
            "Assigned source_record_key from data-record ordinal because publisher supplies no record ID.",
            "Set city from publisher dataset title; station_id is blank because no station ID is published in the declared schema.",
            "Rejected invalid records are written to quality/rejected_records.csv with original parsed fields and reason.",
            "No imputation, deduplication, aggregation, or cross-source join was performed.",
            "Gold row_id is SHA-256 of source_id, pinned version, and source_record_key.",
        ],
    }


def write_run_status(path: Path, status: dict[str, Any]) -> None:
    atomic_json(path, status)


def run_pipeline(root: Path = ROOT) -> tuple[int, dict[str, Any]]:
    global ROOT, DATA_ROOT, CONFIG_PATH
    from pipeline.data_quality_agent import (
        DataQualityAgentError,
        append_quality_log,
        audit_data_quality,
        schema_failure_result,
    )

    original_root, original_data, original_config = ROOT, DATA_ROOT, CONFIG_PATH
    ROOT = root.resolve()
    DATA_ROOT = ROOT / "data"
    CONFIG_PATH = ROOT / "config" / "sources.json"
    run_id = utc_now().strftime("%Y%m%dT%H%M%S.%fZ")
    status_path = DATA_ROOT / "reports" / "execution_status.json"
    status: dict[str, Any] = {
        "run_id": run_id,
        "started_at_utc": utc_text(),
        "status": "running",
        "source_id": None,
        "acquisition_status": None,
        "errors": [],
    }
    source: dict[str, Any] | None = None
    try:
        config = load_config()
        source = next(item for item in config["sources"] if item.get("enabled") is True)
        status["source_id"] = source["source_id"]
        status["acquisition_status"] = "metadata_check_pending"
        timeout = config["request_timeout_seconds"]
        metadata_file, metadata_status = validate_source_availability(source, timeout)
        status["acquisition_status"] = "source_metadata_validated"
        result = download_or_reuse(source, timeout, metadata_file)
        status.update(
            {
                "acquisition_status": result.acquisition_status,
                "source_fetch_timestamp_utc": result.fetched_at_utc,
                "source_request_http_status": metadata_status,
                "raw_file": result.raw_path.relative_to(ROOT).as_posix()
                if result.raw_path.is_relative_to(ROOT)
                else result.raw_path.as_posix(),
                "raw_byte_size": result.byte_size,
                "raw_sha256": result.sha256,
                "raw_md5": result.md5,
            }
        )
        manifest_path = DATA_ROOT / "manifests" / "manifest.csv"
        append_manifest(
            manifest_path,
            run_id=run_id,
            source=source,
            result=result,
            metadata_url=source["metadata_url"],
            metadata_status=metadata_status,
        )
        cleaned, rejected, parse_stats = parse_and_clean(
            result.raw_path, source, result.sha256
        )
        gold = make_gold(cleaned, source["source_url"])
        quality = calculate_quality(
            cleaned,
            rejected,
            parse_stats,
            source=source,
            raw_sha256=result.sha256,
            warning_days=config["freshness_warning_days"],
        )
        atomic_csv(DATA_ROOT / "cleaned" / "paqi_karachi_daily_pm25.csv", CLEAN_FIELDS, cleaned)
        atomic_csv(
            DATA_ROOT / "processed" / "gold_air_quality.csv",
            GOLD_FIELDS,
            gold,
        )
        atomic_csv(
            DATA_ROOT / "quality" / "rejected_records.csv",
            ["source_record_key", "raw_fields_json", "rejection_reason"],
            rejected,
        )
        issues = [
            {
                "source_record_key": record["source_record_key"],
                "source_fields_json": json.dumps(
                    [record["observed_date"], record["source_value_raw"]],
                    ensure_ascii=False,
                ),
                "issue_type": record["quality_flag"],
                "action": "Retained in cleaned and gold with blank normalized value; exclude from numeric evaluation.",
            }
            for record in cleaned
            if record["quality_flag"]
        ]
        issues.extend(
            {
                "source_record_key": record["source_record_key"],
                "source_fields_json": record["raw_fields_json"],
                "issue_type": record["rejection_reason"],
                "action": "Preserved in raw and rejected_records.csv; omitted from cleaned and gold.",
            }
            for record in rejected
        )
        atomic_csv(
            DATA_ROOT / "quality" / "record_issues.csv",
            ["source_record_key", "source_fields_json", "issue_type", "action"],
            issues,
        )
        quality_path = DATA_ROOT / "quality" / "quality_report.json"
        agent_report, quality_log = audit_data_quality(
            raw_path=result.raw_path,
            cleaned_path=DATA_ROOT / "cleaned" / "paqi_karachi_daily_pm25.csv",
            gold_path=DATA_ROOT / "processed" / "gold_air_quality.csv",
            rejected_path=DATA_ROOT / "quality" / "rejected_records.csv",
            base_quality=quality,
            source=source,
            warning_days=config["freshness_warning_days"],
            manifest_path=manifest_path,
            run_id=run_id,
        )
        quality["data_quality_agent"] = agent_report
        append_quality_log(
            DATA_ROOT / "quality" / "quality_log.csv",
            quality_log,
            run_id=run_id,
        )
        atomic_json(quality_path, quality)
        agent_failures = [
            name for name, check in agent_report["checks"].items()
            if check["status"] == "fail"
        ]
        agent_warnings = [
            name for name, check in agent_report["checks"].items()
            if check["status"] == "warning"
        ]
        if agent_failures:
            quality["quality_status"] = "failed"
            quality["critical_failures"] = sorted(
                set(quality["critical_failures"] + agent_failures)
            )
        elif agent_warnings and quality["quality_status"] == "passed":
            quality["quality_status"] = "passed_with_warnings"
        quality["quality_decision_counts"] = agent_report["counts"]
        atomic_json(quality_path, quality)
        status.update(
            {
                "input_record_count": parse_stats["input_record_count"],
                "cleaned_record_count": len(cleaned),
                "gold_record_count": len(gold),
                "numeric_pm25_record_count": (
                    len(cleaned) - parse_stats["missing_value_count"]
                ),
                "rejected_record_count": len(rejected),
                "missing_measurement_count": parse_stats["missing_value_count"],
                "quality_status": quality["quality_status"],
                "data_quality_agent_status": agent_report["status"],
                "data_quality_agent_counts": agent_report["counts"],
                "data_quality_agent_failed_checks": agent_failures,
                "data_quality_agent_warning_checks": agent_warnings,
                "critical_failures": quality["critical_failures"],
                "warning_checks": [
                    f"pipeline.{name}"
                    for name, check in quality["checks"].items()
                    if check["status"] == "warning"
                ]
                + [f"data_quality_agent.{name}" for name in agent_warnings],
                "finished_at_utc": utc_text(),
            }
        )
        if quality["critical_failures"] or agent_failures:
            status["status"] = "failed"
            status["errors"] = [
                "Critical quality checks failed: "
                + ", ".join(quality["critical_failures"] + agent_failures)
            ]
            write_run_status(status_path, status)
            return 1, status
        status["status"] = (
            "success_with_warnings"
            if quality["quality_status"] == "passed_with_warnings" or agent_warnings
            else "success"
        )
        write_run_status(status_path, status)
        return 0, status
    except (PipelineError, DataQualityAgentError, OSError, csv.Error) as exc:
        if (
            source is not None
            and isinstance(exc, PipelineError)
            and str(exc).startswith("Unexpected CSV header:")
        ):
            agent_report, quality_log = schema_failure_result(
                raw_path=result.raw_path,
                source=source,
                run_id=run_id,
            )
            atomic_json(
                DATA_ROOT / "quality" / "quality_report.json",
                {
                    "source_id": source["source_id"],
                    "source_version": source["version"],
                    "source_file_sha256": result.sha256,
                    "quality_status": "failed",
                    "critical_failures": ["schema"],
                    "checks": {
                        "schema": {
                            "status": "fail",
                            "detail": str(exc),
                        }
                    },
                    "data_quality_agent": agent_report,
                },
            )
            append_quality_log(
                DATA_ROOT / "quality" / "quality_log.csv",
                quality_log,
                run_id=run_id,
            )
        status["status"] = "failed"
        status["errors"] = [str(exc)]
        status["finished_at_utc"] = utc_text()
        write_run_status(status_path, status)
        return 1, status
    finally:
        ROOT, DATA_ROOT, CONFIG_PATH = original_root, original_data, original_config


def main() -> int:
    code, status = run_pipeline()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
