"""Third source (live): The Urban Unit AirGradient PM2.5 network in Karachi, hourly aggregates via OpenAQ v3.

Raw evidence per sensor and month under data/raw/urban_unit_karachi_airgradient_pm25/sensor_<id>/:
  <YYYY-MM>.json          completed month, immutable once its SHA-256 sidecar exists
  <YYYY-MM>.partial.json  current month, re-fetched every run until the month closes
This partial file is the only raw artifact that is replaced; its sidecar says so.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pipeline.run import atomic_csv, atomic_json, sha256_file, utc_text
from pipeline.us_consulate import SourceError, _check, _Client, _decision, _month_windows, _parse_utc

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "openaq_urban_unit_karachi.json"

HOURLY_FIELDS = [
    "row_id",
    "source_id",
    "location_id",
    "sensor_id",
    "location_name",
    "datetime_from_utc",
    "datetime_to_utc",
    "local_date",
    "source_value_raw",
    "pm25_ug_m3",
    "hour_coverage_percent",
    "quality_flag",
    "raw_file",
    "raw_file_sha256",
]
SENSOR_DAILY_FIELDS = [
    "row_id",
    "source_id",
    "location_id",
    "location_name",
    "local_date",
    "valid_hours",
    "pm25_daily_mean_ug_m3",
    "quality_flag",
]
NETWORK_DAILY_FIELDS = [
    "local_date",
    "sensors_with_complete_day",
    "network_median_pm25_ug_m3",
    "network_min_sensor_mean_ug_m3",
    "network_max_sensor_mean_ug_m3",
]
DAILY_VALID_FLAGS = {"ok", "source_flag", "extreme_value_review"}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceError(f"Cannot read {path}: {exc}") from exc


def _fetch_hours(client: _Client, config: dict[str, Any], sensor_id: int, lower: datetime, upper: datetime) -> tuple[dict[str, Any], str]:
    results: list[dict[str, Any]] = []
    pages = []
    first_url = ""
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "datetime_from": lower.isoformat().replace("+00:00", "Z"),
                "datetime_to": upper.isoformat().replace("+00:00", "Z"),
                "limit": config["page_limit"],
                "page": page,
            }
        )
        url = f"https://api.openaq.org/v3/sensors/{sensor_id}/hours?{query}"
        first_url = first_url or url
        payload = json.loads(client.get(url))
        batch = payload.get("results")
        if not isinstance(batch, list):
            raise SourceError(f"Unexpected OpenAQ response shape for {url}")
        pages.append({"request_url": url, "meta": payload.get("meta", {})})
        results.extend(batch)
        if len(batch) < config["page_limit"]:
            break
        page += 1
    return {"pages": pages, "results": results}, first_url


def acquire(root: Path, config: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    api_key = os.environ.get("OPENAQ_API_KEY", "").strip()
    client = _Client(api_key, config) if api_key else None
    end = now.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    current_month = end.strftime("%Y-%m")
    raw_files: list[dict[str, Any]] = []
    for location in config["locations"]:
        sensor_dir = root / "data" / "raw" / config["source_id"] / f"sensor_{location['sensor_id']}"
        sensor_dir.mkdir(parents=True, exist_ok=True)
        for month, lower, upper in _month_windows(_parse_utc(config["window_start_utc"]), end):
            partial = month == current_month
            path = sensor_dir / (f"{month}.partial.json" if partial else f"{month}.json")
            sidecar = path.with_name(path.name.replace(".json", ".provenance.json"))
            if not partial and path.exists() and sidecar.exists():
                provenance = json.loads(sidecar.read_text(encoding="utf-8"))
                if sha256_file(path) != provenance["sha256"]:
                    raise SourceError(f"Cached raw file {path} no longer matches its recorded SHA-256.")
                raw_files.append({**provenance, "path": path, "location": location, "acquisition": "cache_verified"})
                continue
            if not partial and (path.exists() or sidecar.exists()):
                raise SourceError(f"Incomplete raw evidence for {path}; refusing to overwrite.")
            if client is None:
                if partial and path.exists() and sidecar.exists():
                    provenance = json.loads(sidecar.read_text(encoding="utf-8"))
                    if sha256_file(path) == provenance["sha256"]:
                        raw_files.append({**provenance, "path": path, "location": location, "acquisition": "cache_partial"})
                        continue
                raise SourceError(
                    f"OPENAQ_API_KEY is not set and {path.name} for sensor {location['sensor_id']} is not cached. "
                    "Get a free key at https://explore.openaq.org/register and export OPENAQ_API_KEY."
                )
            payload, request_url = _fetch_hours(client, config, location["sensor_id"], lower, upper)
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=0).encode("utf-8")
            path.write_bytes(body)
            provenance = {
                "source_id": config["source_id"],
                "location_id": location["location_id"],
                "sensor_id": location["sensor_id"],
                "license": config["license"],
                "request_url": request_url,
                "window_utc": [lower.isoformat(), upper.isoformat()],
                "fetched_at_utc": utc_text(now),
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "record_count": len(payload["results"]),
                "partial_month": partial,
                "note": "Verbatim OpenAQ hourly aggregates; API key omitted. Partial months are replaced each run.",
            }
            sidecar.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            raw_files.append({**provenance, "path": path, "location": location, "acquisition": "fetched"})
        for stale in sensor_dir.glob("*.partial*.json"):
            if not stale.name.startswith(current_month):
                stale.unlink()
    return raw_files


def _clean(config: dict[str, Any], raw_files: list[dict[str, Any]], root: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    zone = ZoneInfo(config["timezone"])
    rows: list[dict[str, Any]] = []
    stats = Counter()
    seen: set[tuple[int, str]] = set()
    for raw in raw_files:
        location = raw["location"]
        relative = Path(raw["path"]).relative_to(root).as_posix()
        for record in json.loads(Path(raw["path"]).read_text(encoding="utf-8")).get("results", []):
            try:
                period = record["period"]
                start = period["datetimeFrom"]["utc"]
                end = period["datetimeTo"]["utc"]
                value = record["value"]
                unit = record["parameter"]["units"]
                name = record["parameter"]["name"]
                coverage = (record.get("coverage") or {}).get("percentCoverage")
                has_flags = bool((record.get("flagInfo") or {}).get("hasFlags"))
            except (KeyError, TypeError):
                stats["schema_errors"] += 1
                continue
            if name != config["parameter"] or unit != config["unit"] or period.get("interval") != "01:00:00":
                stats["schema_errors"] += 1
                continue
            key = (location["sensor_id"], start)
            if key in seen:
                stats["duplicates"] += 1
                continue
            seen.add(key)
            if value is None:
                flag = "missing_source_value"
            elif not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                flag = "invalid_value"
            elif value > config["plausible_max_ug_m3"]:
                flag = "implausible_high"
            elif coverage is not None and coverage < config["min_hour_coverage_percent"]:
                flag = "low_hour_coverage"
            elif value > 500:
                flag = "extreme_value_review"
            elif has_flags:
                flag = "source_flag"
            else:
                flag = "ok"
            rows.append(
                {
                    "row_id": hashlib.sha256(f"{config['source_id']}|{location['sensor_id']}|{start}".encode()).hexdigest(),
                    "source_id": config["source_id"],
                    "location_id": location["location_id"],
                    "sensor_id": location["sensor_id"],
                    "location_name": location["name"],
                    "datetime_from_utc": start,
                    "datetime_to_utc": end,
                    "local_date": _parse_utc(start).astimezone(zone).date().isoformat(),
                    "source_value_raw": "" if value is None else repr(value),
                    "pm25_ug_m3": f"{float(value):g}" if flag not in {"missing_source_value", "invalid_value"} else "",
                    "hour_coverage_percent": "" if coverage is None else f"{coverage:g}",
                    "quality_flag": flag,
                    "raw_file": relative,
                    "raw_file_sha256": raw["sha256"],
                }
            )
    rows.sort(key=lambda row: (row["location_id"], row["datetime_from_utc"]))
    run_length = config["stuck_value_hours"]
    for location_id in {row["location_id"] for row in rows}:
        series = [row for row in rows if row["location_id"] == location_id]
        index = 0
        while index < len(series):
            end_index = index
            while (
                end_index + 1 < len(series)
                and series[end_index + 1]["pm25_ug_m3"] != ""
                and series[end_index + 1]["pm25_ug_m3"] == series[index]["pm25_ug_m3"]
            ):
                end_index += 1
            if series[index]["pm25_ug_m3"] != "" and end_index - index + 1 >= run_length:
                for row in series[index : end_index + 1]:
                    if row["quality_flag"] == "ok":
                        row["quality_flag"] = "stuck_value_review"
            index = end_index + 1
    return rows, stats


def _daily(config: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["location_id"], row["local_date"]), []).append(row)
    sensor_daily = []
    for (location_id, local_date), hours in sorted(grouped.items()):
        valid = [float(row["pm25_ug_m3"]) for row in hours if row["quality_flag"] in DAILY_VALID_FLAGS]
        enough = len(valid) >= config["daily_min_valid_hours"]
        sensor_daily.append(
            {
                "row_id": hashlib.sha256(f"{config['source_id']}|{location_id}|daily|{local_date}".encode()).hexdigest(),
                "source_id": config["source_id"],
                "location_id": location_id,
                "location_name": hours[0]["location_name"],
                "local_date": local_date,
                "valid_hours": len(valid),
                "pm25_daily_mean_ug_m3": f"{statistics.fmean(valid):.2f}" if enough else "",
                "quality_flag": "ok" if enough else "insufficient_valid_hours",
            }
        )
    by_date: dict[str, list[float]] = {}
    for row in sensor_daily:
        if row["pm25_daily_mean_ug_m3"]:
            by_date.setdefault(row["local_date"], []).append(float(row["pm25_daily_mean_ug_m3"]))
    network = [
        {
            "local_date": local_date,
            "sensors_with_complete_day": len(values),
            "network_median_pm25_ug_m3": f"{statistics.median(values):.2f}",
            "network_min_sensor_mean_ug_m3": f"{min(values):.2f}",
            "network_max_sensor_mean_ug_m3": f"{max(values):.2f}",
        }
        for local_date, values in sorted(by_date.items())
    ]
    return sensor_daily, network


def run_source_pipeline(root: Path = ROOT, *, run_id: str = "", now: datetime | None = None) -> tuple[int, dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    checked_at = utc_text(now)
    config = load_config(root / "config" / CONFIG_PATH.name)
    report_path = root / "data" / "quality" / "urban_unit_quality_report.json"
    checks: dict[str, Any] = {}
    log: list[dict[str, str]] = []
    try:
        raw_files = acquire(root, config, now)
    except SourceError as exc:
        report = {"source_id": config["source_id"], "run_id": run_id, "checked_at_utc": checked_at,
                  "status": "failure", "quality_status": "failed", "errors": [str(exc)]}
        atomic_json(report_path, report)
        return 1, report
    acquisitions = Counter(raw["acquisition"] for raw in raw_files)
    _check(checks, "acquisition_and_licence", "pass",
           f"{len(raw_files)} sensor-month raw files across {len(config['locations'])} sensors "
           f"({dict(acquisitions)}); licence {config['license']} per OpenAQ location metadata.")

    rows, stats = _clean(config, raw_files, root)
    _check(checks, "record_schema", "fail" if stats["schema_errors"] else "pass",
           f"{stats['schema_errors']} records failed the pm25 µg/m³ 1-hour schema." if stats["schema_errors"]
           else f"All {len(rows)} hourly records match the pm25 µg/m³ 1-hour schema.")
    if stats["duplicates"]:
        _decision(log, checked_at, issue="identical_duplicate", severity="warning", decision="FIX",
                  action="dropped_duplicate_hour", reason=f"{stats['duplicates']} repeated sensor-hours; first kept.")
    _check(checks, "duplicate_timestamps", "warning" if stats["duplicates"] else "pass",
           f"{stats['duplicates']} duplicate sensor-hours dropped." if stats["duplicates"] else "No duplicate sensor-hours.")

    flags = Counter(row["quality_flag"] for row in rows)
    bad = flags["invalid_value"] + flags["implausible_high"]
    _check(checks, "value_range", "warning" if bad else "pass",
           f"{bad} negative or >{config['plausible_max_ug_m3']} µg/m³ hours excluded from daily means." if bad
           else f"All numeric hours within 0–{config['plausible_max_ug_m3']} µg/m³.")
    for issue, action, reason in (
        ("missing_source_value", "retained_blank", "hourly value null at source"),
        ("invalid_value", "retained_excluded_from_daily_mean", "negative or non-finite value"),
        ("implausible_high", "retained_excluded_from_daily_mean", f"value above {config['plausible_max_ug_m3']} µg/m³"),
        ("low_hour_coverage", "retained_excluded_from_daily_mean",
         f"OpenAQ hour coverage below {config['min_hour_coverage_percent']}%"),
        ("stuck_value_review", "retained_excluded_from_daily_mean",
         f"same value for ≥{config['stuck_value_hours']} consecutive hours (possible frozen sensor)"),
        ("source_flag", "retained_included", "OpenAQ flag present on the hour"),
        ("extreme_value_review", "retained_included_pending_review", "value above 500 µg/m³; no evidence it is wrong"),
    ):
        if flags[issue]:
            _decision(log, checked_at, issue=issue, severity="warning", decision="FLAG", action=action,
                      reason=f"{flags[issue]} sensor-hours: {reason}.")
    _check(checks, "low_coverage_and_stuck_values", "warning" if flags["low_hour_coverage"] + flags["stuck_value_review"] else "pass",
           f"{flags['low_hour_coverage']} low-coverage hours and {flags['stuck_value_review']} stuck-value hours "
           "kept but excluded from daily means.")

    expected = 0
    by_sensor: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_sensor.setdefault(row["location_id"], []).append(row)
    latest_by_sensor = {}
    for location_id, series in by_sensor.items():
        first, last = _parse_utc(series[0]["datetime_from_utc"]), _parse_utc(series[-1]["datetime_from_utc"])
        expected += int((last - first).total_seconds() // 3600) + 1
        latest_by_sensor[series[0]["location_name"]] = series[-1]["datetime_to_utc"]
    absent = expected - len(rows)
    _check(checks, "hourly_continuity", "warning" if absent else "pass",
           f"{absent} sensor-hours absent between each sensor's first and last report; not synthesised.")
    if absent:
        _decision(log, checked_at, issue="absent_hours", severity="warning", decision="FILL", action="not_applied",
                  reason=f"{absent} sensor-hours missing; low-cost sensor outages are not imputed.")
    if flags["missing_source_value"]:
        _decision(log, checked_at, issue="missing_source_value", severity="warning", decision="FILL", action="not_applied",
                  reason=f"{flags['missing_source_value']} null hours left blank.")

    latest = max(latest_by_sensor.values()) if latest_by_sensor else ""
    age_hours = round((now - _parse_utc(latest)).total_seconds() / 3600, 1) if latest else None
    stale = sorted(name for name, ts in latest_by_sensor.items()
                   if (now - _parse_utc(ts)).total_seconds() / 3600 > config["sensor_stale_warning_hours"])
    fresh = age_hours is not None and age_hours <= config["freshness_warning_hours"]
    _check(checks, "freshness", "pass" if fresh and not stale else "warning",
           f"Latest network hour ends {latest} ({age_hours} h ago); "
           + (f"stale sensors (>{config['sensor_stale_warning_hours']} h): {', '.join(stale)}." if stale else "no stale sensors."))
    _check(checks, "measurement_caveat", "warning", config["measurement_caveat"])
    _decision(log, checked_at, issue="uncorrected_low_cost_sensor", severity="warning", decision="FLAG", action="disclosed",
              reason=config["measurement_caveat"])

    latest_hour_rows = [row for row in rows if row["datetime_to_utc"] == latest and row["quality_flag"] in DAILY_VALID_FLAGS]
    latest_values = [float(row["pm25_ug_m3"]) for row in latest_hour_rows]
    latest_hour = {
        "datetime_to_utc": latest,
        "sensors_reporting": len(latest_values),
        "sensors_configured": len(config["locations"]),
        "median_pm25_ug_m3": round(statistics.median(latest_values), 1) if latest_values else None,
        "min_pm25_ug_m3": round(min(latest_values), 1) if latest_values else None,
        "max_pm25_ug_m3": round(max(latest_values), 1) if latest_values else None,
        "by_sensor": {row["location_name"]: float(row["pm25_ug_m3"]) for row in latest_hour_rows},
        "row_ids": [row["row_id"] for row in latest_hour_rows],
    }

    sensor_daily, network = _daily(config, rows)
    atomic_csv(root / "data" / "cleaned" / "urban_unit_karachi_hourly_pm25.csv", HOURLY_FIELDS, rows)
    atomic_csv(root / "data" / "processed" / "gold_urban_unit_karachi_hourly.csv", HOURLY_FIELDS, rows)
    atomic_csv(root / "data" / "processed" / "gold_urban_unit_karachi_sensor_daily.csv", SENSOR_DAILY_FIELDS, sensor_daily)
    atomic_csv(root / "data" / "processed" / "gold_urban_unit_karachi_network_daily.csv", NETWORK_DAILY_FIELDS, network)

    statuses = [check["status"] for check in checks.values()]
    status = "failure" if "fail" in statuses else "success_with_warnings" if "warning" in statuses else "success"
    report = {
        "agent": "deterministic_data_quality_agent",
        "source_id": config["source_id"],
        "title": config["title"],
        "original_publisher": config["original_publisher"],
        "access_platform": config["access_platform"],
        "license": config["license"],
        "attribution": config["attribution"],
        "run_id": run_id,
        "checked_at_utc": checked_at,
        "status": status,
        "quality_status": {"success": "passed", "success_with_warnings": "passed_with_warnings"}.get(status, "failed"),
        "sensors": len(config["locations"]),
        "hourly_gold_rows": len(rows),
        "hourly_numeric_rows": sum(row["pm25_ug_m3"] != "" for row in rows),
        "sensor_daily_rows": len(sensor_daily),
        "network_daily_rows": len(network),
        "first_observation_utc": min((row["datetime_from_utc"] for row in rows), default=""),
        "last_observation_utc": latest,
        "latest_age_hours": age_hours,
        "latest_by_sensor_utc": latest_by_sensor,
        "latest_hour": latest_hour,
        "latest_network_day": network[-1] if network else None,
        "quality_flag_counts": dict(sorted(flags.items())),
        "checks": checks,
        "counts": {
            "passed_checks": statuses.count("pass"),
            "warning_checks": statuses.count("warning"),
            "failed_checks": statuses.count("fail"),
            "fixes": sum(entry["decision"] == "FIX" for entry in log),
            "fills_applied": 0,
            "fills_not_applied": sum(entry["decision"] == "FILL" for entry in log),
            "flags": sum(entry["decision"] == "FLAG" for entry in log),
        },
        "decision_log": log,
    }
    atomic_json(report_path, report)
    from pipeline.data_quality_agent import append_quality_log

    append_quality_log(root / "data" / "quality" / "urban_unit_quality_log.csv", log, run_id=run_id)
    return (1 if status == "failure" else 0), report


def main() -> int:
    code, report = run_source_pipeline(run_id=utc_text().replace(":", "").replace("-", ""))
    print(json.dumps({key: report.get(key) for key in ("status", "hourly_gold_rows", "last_observation_utc",
                                                       "latest_age_hours", "quality_flag_counts", "counts", "errors")},
                     indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
