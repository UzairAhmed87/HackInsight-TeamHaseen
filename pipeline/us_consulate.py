"""Second independent source: U.S. Consulate General Karachi hourly PM2.5 (AirNow via OpenAQ v3).

Layers
  raw      data/raw/us_consulate_karachi_pm25/openaq_v3_sensor_<id>/<YYYY-MM>.json (verbatim API pages)
           plus <YYYY-MM>.provenance.json sidecars; never overwritten once checksum-verified.
  cleaned  data/cleaned/us_consulate_karachi_hourly_pm25.csv (one row per raw record, typed, flagged)
  gold     data/processed/gold_us_consulate_karachi_hourly.csv and ..._daily.csv

The OpenAQ API key is read from OPENAQ_API_KEY and is never written to any artifact. Without a key,
the pipeline rebuilds from checksum-verified cached raw files only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.run import atomic_csv, atomic_json, sha256_file, utc_text

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "openaq_us_consulate_karachi.json"
USER_AGENT = "HackInsight-AirQuality-Pakistan/1.0 (research pipeline; contact via GitHub repo)"

CLEAN_FIELDS = [
    "row_id",
    "source_id",
    "sensor_id",
    "raw_file",
    "raw_file_sha256",
    "raw_record_index",
    "datetime_from_utc",
    "datetime_to_utc",
    "datetime_to_local",
    "local_date",
    "source_value_raw",
    "pm25_ug_m3",
    "has_source_flags",
    "quality_flag",
]
HOURLY_GOLD_FIELDS = [
    "row_id",
    "source_id",
    "datetime_to_utc",
    "datetime_to_local",
    "local_date",
    "pm25_ug_m3",
    "quality_flag",
    "raw_file_sha256",
]
DAILY_GOLD_FIELDS = [
    "row_id",
    "source_id",
    "local_date",
    "valid_hours",
    "pm25_daily_mean_ug_m3",
    "pm25_daily_min_ug_m3",
    "pm25_daily_max_ug_m3",
    "quality_flag",
    "hourly_row_ids_sha256",
]
PROVENANCE_FIELDS = [
    "source_id",
    "raw_file",
    "sha256",
    "bytes",
    "record_count",
    "request_url",
    "fetched_at_utc",
    "acquisition",
]


class SourceError(Exception):
    """Raised when the source cannot be acquired or rebuilt with trustworthy evidence."""


@dataclass(frozen=True)
class RawMonth:
    month: str
    path: Path
    sha256: str
    record_count: int
    request_url: str
    fetched_at_utc: str
    acquisition: str


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceError(f"Cannot read {path}: {exc}") from exc


def _parse_utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def _month_windows(start: datetime, end: datetime) -> list[tuple[str, datetime, datetime]]:
    windows = []
    year, month = start.year, start.month
    while datetime(year, month, 1, tzinfo=timezone.utc) < end:
        lower = datetime(year, month, 1, tzinfo=timezone.utc)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        upper = min(datetime(year, month, 1, tzinfo=timezone.utc), end)
        windows.append((lower.strftime("%Y-%m"), max(lower, start), upper))
    return windows


class _Client:
    def __init__(self, api_key: str, config: dict[str, Any]) -> None:
        self.api_key = api_key
        self.timeout = config["request_timeout_seconds"]
        self.min_gap = config["min_seconds_between_requests"]
        self._last = 0.0

    def get(self, url: str) -> bytes:
        for attempt in range(5):
            wait = self.min_gap - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            request = urllib.request.Request(
                url,
                headers={"X-API-Key": self.api_key, "Accept": "application/json", "User-Agent": USER_AGENT},
            )
            self._last = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                if exc.code in (408, 429, 500, 502, 503, 504) and attempt < 4:
                    time.sleep(min(60, 5 * 2**attempt))
                    continue
                raise SourceError(f"OpenAQ request failed with HTTP {exc.code}: {url}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < 4:
                    time.sleep(min(60, 5 * 2**attempt))
                    continue
                raise SourceError(f"OpenAQ request failed: {exc}") from exc
        raise SourceError(f"OpenAQ request kept failing: {url}")


def _fetch_month(client: _Client, config: dict[str, Any], lower: datetime, upper: datetime) -> tuple[dict[str, Any], str]:
    results: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
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
        url = f"{config['measurements_url']}?{query}"
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


def acquire(root: Path = ROOT, config: dict[str, Any] | None = None) -> list[RawMonth]:
    """Return checksum-verified raw months, fetching only months not already cached."""
    config = config or load_config(root / "config" / CONFIG_PATH.name)
    raw_dir = root / "data" / "raw" / config["source_id"] / f"openaq_v3_sensor_{config['openaq_sensor_id']}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("OPENAQ_API_KEY", "").strip()
    client = _Client(api_key, config) if api_key else None

    location_path = raw_dir / "location.json"
    if not location_path.exists():
        if client is None:
            raise SourceError("OPENAQ_API_KEY is not set and no cached location metadata exists.")
        location_path.write_bytes(client.get(config["location_url"]))
    location = json.loads(location_path.read_text(encoding="utf-8"))["results"][0]
    licences = [entry.get("name") for entry in location.get("licenses") or []]
    if config["license"] not in licences:
        raise SourceError(f"Location licence {licences} does not include configured {config['license']!r}.")
    provider = (location.get("provider") or {}).get("name")
    if provider != "AirNow":
        raise SourceError(f"Unexpected provider {provider!r} for location {config['openaq_location_id']}.")

    flags_path = raw_dir / "flags.json"
    if not flags_path.exists():
        if client is None:
            raise SourceError("OPENAQ_API_KEY is not set and no cached OpenAQ flag records exist.")
        # The flags endpoint ignores limit/page and always returns the full list, so fetch once and verify the count.
        url = f"{config['location_url']}/flags"
        payload = json.loads(client.get(url))
        if len(payload.get("results", [])) != payload.get("meta", {}).get("found"):
            raise SourceError("OpenAQ flags response is incomplete; refusing to record partial evidence.")
        flags_path.write_text(
            json.dumps({"request_url": url, "payload": payload}, ensure_ascii=False, indent=0) + "\n",
            encoding="utf-8",
        )

    months: list[RawMonth] = []
    windows = _month_windows(_parse_utc(config["window_start_utc"]), _parse_utc(config["window_end_utc"]))
    for month, lower, upper in windows:
        path = raw_dir / f"{month}.json"
        sidecar = raw_dir / f"{month}.provenance.json"
        if path.exists() and sidecar.exists():
            provenance = json.loads(sidecar.read_text(encoding="utf-8"))
            digest = sha256_file(path)
            if digest != provenance["sha256"]:
                raise SourceError(f"Cached raw file {path} no longer matches its recorded SHA-256.")
            months.append(
                RawMonth(month, path, digest, provenance["record_count"], provenance["request_url"],
                         provenance["fetched_at_utc"], "cache_verified")
            )
            continue
        if path.exists() or sidecar.exists():
            raise SourceError(f"Incomplete raw evidence for {month}; refusing to overwrite {path}.")
        if client is None:
            raise SourceError(
                f"OPENAQ_API_KEY is not set and raw month {month} is not cached. "
                "Get a free key at https://explore.openaq.org/register and export OPENAQ_API_KEY."
            )
        payload, request_url = _fetch_month(client, config, lower, upper)
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=0).encode("utf-8")
        path.write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        fetched_at = utc_text()
        provenance = {
            "source_id": config["source_id"],
            "original_publisher": config["original_publisher"],
            "access_platform": config["access_platform"],
            "license": config["license"],
            "attribution": config["attribution"],
            "request_url": request_url,
            "window_utc": [lower.isoformat(), upper.isoformat()],
            "fetched_at_utc": fetched_at,
            "sha256": digest,
            "bytes": len(body),
            "record_count": len(payload["results"]),
            "note": "Verbatim OpenAQ results; API key omitted from all recorded URLs.",
        }
        sidecar.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        months.append(RawMonth(month, path, digest, len(payload["results"]), request_url, fetched_at, "fetched"))
    return months


def _row_id(source_id: str, sensor_id: int, datetime_from_utc: str) -> str:
    return hashlib.sha256(f"{source_id}|{sensor_id}|{datetime_from_utc}".encode("utf-8")).hexdigest()


def _check(checks: dict[str, Any], name: str, status: str, detail: str) -> None:
    checks[name] = {"status": status, "detail": detail}


def _decision(
    log: list[dict[str, str]],
    checked_at: str,
    *,
    issue: str,
    severity: str,
    decision: str,
    action: str,
    reason: str,
    source_hash: str = "",
    row_id: str = "",
    record_key: str = "",
    observed_date: str = "",
) -> None:
    log.append(
        {
            "checked_at_utc": checked_at,
            "source_row_id": row_id,
            "source_record_key": record_key,
            "observed_date": observed_date,
            "issue": issue,
            "severity": severity,
            "decision": decision,
            "action_taken": action,
            "reason": reason,
            "source_file_sha256": source_hash,
        }
    )


def _clean(config: dict[str, Any], months: list[RawMonth], root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from zoneinfo import ZoneInfo

    local_zone = ZoneInfo(config["timezone"])
    window = (_parse_utc(config["window_start_utc"]), _parse_utc(config["window_end_utc"]))
    rows: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    stats = {"schema_errors": [], "duplicates_identical": 0, "duplicates_conflicting": 0, "out_of_window": 0}
    for raw in months:
        records = json.loads(raw.path.read_text(encoding="utf-8")).get("results", [])
        relative = raw.path.relative_to(root).as_posix()
        for index, record in enumerate(records):
            try:
                period = record["period"]
                start = period["datetimeFrom"]["utc"]
                end = period["datetimeTo"]["utc"]
                parameter = record["parameter"]
                value = record["value"]
                has_flags = bool(record["flagInfo"]["hasFlags"])
            except (KeyError, TypeError):
                stats["schema_errors"].append(f"{relative}#{index}")
                continue
            if (
                parameter.get("name") != config["parameter"]
                or parameter.get("units") != config["unit"]
                or period.get("interval") != "01:00:00"
                or (value is not None and not isinstance(value, (int, float)))
            ):
                stats["schema_errors"].append(f"{relative}#{index}")
                continue
            start_dt = _parse_utc(start)
            if not window[0] <= start_dt < window[1]:
                stats["out_of_window"] += 1
                continue
            if start in seen:
                if seen[start]["source_value_raw"] == ("" if value is None else repr(value)):
                    stats["duplicates_identical"] += 1
                else:
                    stats["duplicates_conflicting"] += 1
                    seen[start]["quality_flag"] = "conflicting_duplicate"
                continue
            if value is None:
                flag = "missing_source_value"
            elif not math.isfinite(value) or value < 0:
                flag = "invalid_value"
            elif value > config["plausible_max_ug_m3"]:
                flag = "implausible_high"
            elif value == 985:
                flag = "suspected_instrument_error_code"
            elif value > 500:
                flag = "extreme_value_review"
            elif has_flags:
                flag = "source_flag_window"
            else:
                flag = "ok"
            local_start = start_dt.astimezone(local_zone)
            row = {
                "row_id": _row_id(config["source_id"], config["openaq_sensor_id"], start),
                "source_id": config["source_id"],
                "sensor_id": config["openaq_sensor_id"],
                "raw_file": relative,
                "raw_file_sha256": raw.sha256,
                "raw_record_index": index,
                "datetime_from_utc": start,
                "datetime_to_utc": end,
                "datetime_to_local": _parse_utc(end).astimezone(local_zone).isoformat(),
                "local_date": local_start.date().isoformat(),
                "source_value_raw": "" if value is None else repr(value),
                "pm25_ug_m3": "" if value is None or flag == "invalid_value" else format(float(value), "g"),
                "has_source_flags": str(has_flags).lower(),
                "quality_flag": flag,
            }
            seen[start] = row
            rows.append(row)
    rows.sort(key=lambda row: row["datetime_from_utc"])
    return rows, stats


DAILY_VALID_FLAGS = {"ok", "source_flag_window", "extreme_value_review"}


def _daily(config: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_date.setdefault(row["local_date"], []).append(row)
    daily = []
    for local_date in sorted(by_date):
        hours = by_date[local_date]
        valid = [float(row["pm25_ug_m3"]) for row in hours if row["quality_flag"] in DAILY_VALID_FLAGS]
        enough = len(valid) >= config["daily_min_valid_hours"]
        digest = hashlib.sha256("".join(sorted(row["row_id"] for row in hours)).encode("utf-8")).hexdigest()
        daily.append(
            {
                "row_id": hashlib.sha256(f"{config['source_id']}|daily|{local_date}".encode("utf-8")).hexdigest(),
                "source_id": config["source_id"],
                "local_date": local_date,
                "valid_hours": len(valid),
                "pm25_daily_mean_ug_m3": f"{sum(valid) / len(valid):.2f}" if enough else "",
                "pm25_daily_min_ug_m3": f"{min(valid):g}" if enough else "",
                "pm25_daily_max_ug_m3": f"{max(valid):g}" if enough else "",
                "quality_flag": "ok" if enough else "insufficient_valid_hours",
                "hourly_row_ids_sha256": digest,
            }
        )
    return daily


def run_source_pipeline(root: Path = ROOT, *, run_id: str = "", now: datetime | None = None) -> tuple[int, dict[str, Any]]:
    """Acquire, clean, publish gold layers and run the source Data Quality Agent. Returns (exit_code, report)."""
    from collections import Counter

    now = now or datetime.now(timezone.utc)
    checked_at = utc_text(now)
    config = load_config(root / "config" / CONFIG_PATH.name)
    checks: dict[str, Any] = {}
    log: list[dict[str, str]] = []
    report_path = root / "data" / "quality" / "us_consulate_quality_report.json"

    try:
        months = acquire(root, config)
    except SourceError as exc:
        report = {"source_id": config["source_id"], "run_id": run_id, "checked_at_utc": checked_at,
                  "status": "failure", "quality_status": "failed", "errors": [str(exc)]}
        atomic_json(report_path, report)
        return 1, report
    fetched = sum(month.acquisition == "fetched" for month in months)
    _check(checks, "acquisition_and_licence", "pass",
           f"{len(months)} monthly raw files ({fetched} fetched this run, {len(months) - fetched} reused after SHA-256 "
           f"verification); provider AirNow and licence '{config['license']}' confirmed from OpenAQ location metadata.")

    rows, stats = _clean(config, months, root)
    raw_records = sum(month.record_count for month in months)
    if stats["schema_errors"]:
        _check(checks, "record_schema", "fail",
               f"{len(stats['schema_errors'])} raw records did not match the expected pm25 µg/m³ hourly schema.")
        _decision(log, checked_at, issue="schema_mismatch", severity="critical", decision="FLAG",
                  action="pipeline_failure; raw preserved",
                  reason=f"{len(stats['schema_errors'])} records rejected, first: {stats['schema_errors'][:3]}")
    else:
        _check(checks, "record_schema", "pass", f"All {raw_records} raw records are pm25, µg/m³, 1-hour periods.")

    duplicates = stats["duplicates_identical"] + stats["duplicates_conflicting"]
    if stats["duplicates_conflicting"]:
        _check(checks, "duplicate_timestamps", "fail",
               f"{stats['duplicates_conflicting']} timestamps have conflicting duplicate values.")
        _decision(log, checked_at, issue="conflicting_duplicate", severity="critical", decision="FLAG",
                  action="pipeline_failure", reason=f"{stats['duplicates_conflicting']} rows: conflicting values for one hour.")
    elif stats["duplicates_identical"]:
        _check(checks, "duplicate_timestamps", "warning", f"{duplicates} identical duplicate records dropped.")
        _decision(log, checked_at, issue="identical_duplicate", severity="warning", decision="FIX",
                  action="dropped_exact_duplicate",
                  reason=f"{duplicates} rows: same hour and same value repeated; first occurrence kept.")
    else:
        _check(checks, "duplicate_timestamps", "pass", "No duplicate hourly timestamps.")

    flag_counts = Counter(row["quality_flag"] for row in rows)
    missing = flag_counts["missing_source_value"]
    _check(checks, "missing_values", "warning" if missing else "pass",
           f"{missing} of {len(rows)} hourly records have no published value (OpenAQ nulls readings that failed its limit "
           "checks, e.g. the -999 missing-data code). Retained as blank; not imputed.")
    if missing:
        _decision(log, checked_at, issue="missing_source_value", severity="warning", decision="FILL",
                  action="not_applied",
                  reason=f"{missing} rows: hourly PM2.5 is null at source; interpolation would invent exposure, so no fill.")
        _decision(log, checked_at, issue="missing_source_value", severity="warning", decision="FLAG",
                  action="retained_blank_excluded_from_daily_mean", reason=f"{missing} rows flagged missing_source_value.")

    invalid = flag_counts["invalid_value"] + flag_counts["implausible_high"]
    _check(checks, "value_range", "fail" if invalid else "pass",
           f"{invalid} negative, non-finite or >{config['plausible_max_ug_m3']} µg/m³ values." if invalid
           else f"All numeric values within 0–{config['plausible_max_ug_m3']} µg/m³.")
    for row in rows:
        if row["quality_flag"] in {"suspected_instrument_error_code", "extreme_value_review", "invalid_value", "implausible_high"}:
            exclude = row["quality_flag"] != "extreme_value_review"
            _decision(
                log, checked_at, issue=row["quality_flag"],
                severity="warning", decision="FLAG",
                action="retained_excluded_from_daily_mean" if exclude else "retained_included_pending_review",
                reason=(
                    f"Value {row['source_value_raw']} µg/m³ equals 985, the upper-limit/error value reported by BAM-1020 "
                    "monitors; not treated as a real concentration."
                    if row["quality_flag"] == "suspected_instrument_error_code"
                    else f"Value {row['source_value_raw']} µg/m³ is above 500; no evidence it is wrong, kept but marked for review."
                ),
                source_hash=row["raw_file_sha256"], row_id=row["row_id"],
                record_key=row["datetime_from_utc"], observed_date=row["local_date"],
            )
    suspect = flag_counts["suspected_instrument_error_code"] + flag_counts["extreme_value_review"]
    _check(checks, "suspect_values", "warning" if suspect else "pass",
           f"{flag_counts['suspected_instrument_error_code']} hour(s) at the 985 µg/m³ instrument limit excluded from daily "
           f"means; {flag_counts['extreme_value_review']} hour(s) above 500 µg/m³ kept and flagged for review.")

    source_flagged = flag_counts["source_flag_window"]
    _check(checks, "source_flags", "pass",
           f"{source_flagged} numeric hours fall inside an OpenAQ 'Limits exceeded' window caused by neighbouring "
           "nulled readings; the values themselves passed limits and are kept.")
    if source_flagged:
        _decision(log, checked_at, issue="source_flag_window", severity="info", decision="FLAG",
                  action="retained_included", reason=f"{source_flagged} rows overlap an OpenAQ limits flag window.")

    expected_hours = 0
    if rows:
        first, last = _parse_utc(rows[0]["datetime_from_utc"]), _parse_utc(rows[-1]["datetime_from_utc"])
        expected_hours = int((last - first).total_seconds() // 3600) + 1
    absent = expected_hours - len(rows)
    _check(checks, "hourly_continuity", "warning" if absent else "pass",
           f"{absent} hours have no record at all between the first and last observation ({expected_hours} expected).")
    if absent:
        _decision(log, checked_at, issue="absent_hours", severity="warning", decision="FILL", action="not_applied",
                  reason=f"{absent} hours missing from the source record; no rows synthesised.")

    daily = _daily(config, rows)
    complete_days = sum(day["quality_flag"] == "ok" for day in daily)
    _check(checks, "daily_completeness", "warning" if complete_days < len(daily) else "pass",
           f"{complete_days} of {len(daily)} local days have ≥{config['daily_min_valid_hours']} valid hours "
           "(US EPA 75% completeness convention); other days have a blank daily mean.")
    if complete_days < len(daily):
        _decision(log, checked_at, issue="insufficient_valid_hours", severity="warning", decision="FLAG",
                  action="daily_mean_left_blank",
                  reason=f"{len(daily) - complete_days} days below {config['daily_min_valid_hours']} valid hours.")

    latest = rows[-1]["datetime_to_utc"] if rows else ""
    age_days = (now - _parse_utc(latest)).days if latest else None
    _check(checks, "freshness", "warning",
           f"Monitor's last published hour is {latest} ({age_days} days ago); OpenAQ lists no newer data, so this is a "
           "closed historical record.")
    _decision(log, checked_at, issue="source_not_current", severity="warning", decision="FLAG", action="disclosed",
              reason=f"Latest observation {latest}; not used as a current reading.")

    atomic_csv(root / "data" / "cleaned" / "us_consulate_karachi_hourly_pm25.csv", CLEAN_FIELDS, rows)
    atomic_csv(root / "data" / "processed" / "gold_us_consulate_karachi_hourly.csv", HOURLY_GOLD_FIELDS,
               ({field: row[field] for field in HOURLY_GOLD_FIELDS} for row in rows))
    atomic_csv(root / "data" / "processed" / "gold_us_consulate_karachi_daily.csv", DAILY_GOLD_FIELDS, daily)
    atomic_csv(root / "data" / "manifests" / "us_consulate_raw_manifest.csv", PROVENANCE_FIELDS,
               ({"source_id": config["source_id"], "raw_file": month.path.relative_to(root).as_posix(),
                 "sha256": month.sha256, "bytes": month.path.stat().st_size, "record_count": month.record_count,
                 "request_url": month.request_url, "fetched_at_utc": month.fetched_at_utc,
                 "acquisition": month.acquisition} for month in months))

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
        "raw_record_count": raw_records,
        "hourly_gold_rows": len(rows),
        "hourly_numeric_rows": sum(row["pm25_ug_m3"] != "" for row in rows),
        "daily_gold_rows": len(daily),
        "daily_complete_rows": complete_days,
        "first_observation_utc": rows[0]["datetime_from_utc"] if rows else "",
        "last_observation_utc": latest,
        "source_age_days": age_days,
        "quality_flag_counts": dict(sorted(flag_counts.items())),
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
        "decision_log": [entry for entry in log if not entry["source_row_id"]],
        "record_level_decisions": sum(bool(entry["source_row_id"]) for entry in log),
    }
    atomic_json(report_path, report)
    from pipeline.data_quality_agent import append_quality_log

    append_quality_log(root / "data" / "quality" / "us_consulate_quality_log.csv", log, run_id=run_id)
    return (1 if status == "failure" else 0), report


def main() -> int:
    code, report = run_source_pipeline(run_id=utc_text().replace(":", "").replace("-", ""))
    print(json.dumps({key: report.get(key) for key in ("status", "hourly_gold_rows", "daily_complete_rows",
                                                       "quality_flag_counts", "counts", "errors")},
                     indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
