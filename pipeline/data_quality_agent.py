from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pipeline import readiness
from pipeline.run import CLEAN_FIELDS, GOLD_FIELDS, sha256_file


LOG_FIELDS = [
    "run_id",
    "checked_at_utc",
    "source_row_id",
    "source_record_key",
    "observed_date",
    "issue",
    "severity",
    "decision",
    "action_taken",
    "reason",
    "source_file_sha256",
]
LEGACY_LOG_FIELDS = LOG_FIELDS[1:]


class DataQualityAgentError(Exception):
    """Raised when quality auditing cannot complete with trustworthy evidence."""


def _row_id(source: dict[str, Any], source_record_key: str) -> str:
    identity = "|".join(
        (source["source_id"], source["version"], source_record_key)
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames is None:
                raise DataQualityAgentError(f"{path} has no header.")
            return reader.fieldnames, list(reader)
    except (OSError, csv.Error) as exc:
        raise DataQualityAgentError(f"Cannot inspect {path}: {exc}") from exc


def append_quality_log(
    path: Path, issues: list[dict[str, str]], *, run_id: str
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    if exists:
        fields, rows = _read_csv(path)
        if fields == LEGACY_LOG_FIELDS:
            _rewrite_legacy_log(path, rows)
        elif fields != LOG_FIELDS:
            raise DataQualityAgentError(
                f"Existing quality log schema differs from the expected contract: {path}"
            )
    try:
        with path.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=LOG_FIELDS, extrasaction="raise")
            if not exists:
                writer.writeheader()
            writer.writerows({"run_id": run_id, **issue} for issue in issues)
    except (OSError, csv.Error) as exc:
        raise DataQualityAgentError(f"Cannot append quality decisions to {path}: {exc}") from exc


def _rewrite_legacy_log(path: Path, rows: list[dict[str, str]]) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=LOG_FIELDS)
            writer.writeheader()
            for row in rows:
                checked_at = row.get("checked_at_utc", "")
                writer.writerow(
                    {
                        "run_id": f"legacy:{checked_at}" if checked_at else "legacy:unknown",
                        **row,
                    }
                )
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise DataQualityAgentError(
            f"Cannot migrate legacy quality log schema at {path}: {exc}"
        ) from exc


def _issue(
    *,
    checked_at: str,
    row_id: str,
    record_key: str,
    observed_date: str,
    issue: str,
    severity: str,
    decision: str,
    action: str,
    reason: str,
    source_hash: str,
) -> dict[str, str]:
    return {
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


def _append(
    issues: list[dict[str, str]],
    source: dict[str, Any],
    source_hash: str,
    checked_at: str,
    *,
    record_key: str = "",
    observed_date: str = "",
    issue: str,
    severity: str,
    decision: str,
    action: str,
    reason: str,
) -> None:
    issues.append(
        _issue(
            checked_at=checked_at,
            row_id=_row_id(source, record_key) if record_key else "",
            record_key=record_key,
            observed_date=observed_date,
            issue=issue,
            severity=severity,
            decision=decision,
            action=action,
            reason=reason,
            source_hash=source_hash,
        )
    )


def _manifest_fetch_time(path: Path, source_hash: str) -> str | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream, strict=True))
    except (OSError, csv.Error) as exc:
        raise DataQualityAgentError(f"Cannot inspect manifest {path}: {exc}") from exc
    matching = [
        row for row in rows
        if row.get("sha256") == source_hash
        and row.get("source_id") == "paqi_karachi_daily_pm25"
    ]
    return matching[-1].get("fetch_timestamp_utc") if matching else None


def _base_checks(base_quality: dict[str, Any]) -> dict[str, str]:
    checks = base_quality.get("checks", {})
    return {
        name: str(check.get("status", "fail"))
        for name, check in checks.items()
        if isinstance(check, dict)
    }


def audit_data_quality(
    *,
    raw_path: Path,
    cleaned_path: Path,
    gold_path: Path,
    rejected_path: Path,
    base_quality: dict[str, Any],
    source: dict[str, Any],
    warning_days: int,
    manifest_path: Path,
    run_id: str = "",
    now: datetime | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    checked_at = (
        (now or datetime.now(timezone.utc))
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    raw_header, raw_rows = _read_csv(raw_path)
    cleaned_header, cleaned = _read_csv(cleaned_path)
    gold_header, gold = _read_csv(gold_path)
    rejected_header, rejected = _read_csv(rejected_path)
    source_hash = sha256_file(raw_path)
    issues: list[dict[str, str]] = []
    checks: dict[str, dict[str, Any]] = {}
    base = _base_checks(base_quality)

    def check(name: str, status: str, detail: str) -> None:
        checks[name] = {"status": status, "detail": detail}

    expected_source_header = source["expected_header"]
    if raw_header != expected_source_header:
        check(
            "required_columns_and_schema",
            "fail",
            f"Raw header {raw_header!r} differs from pinned schema {expected_source_header!r}.",
        )
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            issue="schema_change",
            severity="critical",
            decision="FLAG",
            action="pipeline_failure",
            reason="Unexpected source columns cannot be safely interpreted; original raw file is preserved.",
        )
    else:
        check("required_columns_and_schema", "pass", "Raw header matches pinned source schema.")

    required_clean = set(CLEAN_FIELDS)
    required_gold = set(GOLD_FIELDS)
    clean_schema_ok = required_clean.issubset(cleaned_header)
    gold_schema_ok = required_gold.issubset(gold_header)
    check(
        "warehouse_schema",
        "pass" if clean_schema_ok and gold_schema_ok else "fail",
        "Cleaned and gold columns match the required data contracts."
        if clean_schema_ok and gold_schema_ok
        else "Cleaned or gold columns are missing required contract fields.",
    )
    if not clean_schema_ok or not gold_schema_ok:
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            issue="warehouse_schema_change",
            severity="critical",
            decision="FLAG",
            action="pipeline_failure",
            reason="Required cleaned/gold columns are missing; no schema coercion is attempted.",
        )

    base_status = base.get("date_parse", "pass")
    invalid_date_count = sum(
        "invalid date" in row.get("rejection_reason", "").lower()
        for row in rejected
    )
    check(
        "date_parsing",
        "fail" if base_status == "fail" else "pass",
        f"{invalid_date_count} invalid source dates; records remain in rejected_records.csv."
        if invalid_date_count
        else "All retained source dates parse as ISO calendar dates.",
    )
    malformed_rows = [
        row for row in rejected
        if "columns" in row.get("rejection_reason", "").lower()
    ]
    for row in malformed_rows:
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            record_key=row.get("source_record_key", ""),
            issue="malformed_source_row",
            severity="critical",
            decision="FLAG",
            action="preserved_in_rejected_records; pipeline_failure",
            reason=row.get("rejection_reason", "Unexpected source row shape."),
        )
    check(
        "source_row_shape",
        "fail" if malformed_rows else "pass",
        f"{len(malformed_rows)} source rows have a shape different from the declared schema.",
    )

    date_groups: dict[str, list[dict[str, str]]] = {}
    for row in cleaned:
        date_groups.setdefault(row["observed_date"], []).append(row)
    duplicate_rows = [
        row for group in date_groups.values() if len(group) > 1 for row in group
    ]
    for row in duplicate_rows:
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            record_key=row["source_record_key"],
            observed_date=row["observed_date"],
            issue="duplicate_observation_date",
            severity="critical",
            decision="FLAG",
            action="preserved_without_deduplication; pipeline_failure",
            reason="No source-authorized rule establishes which duplicate measurement to retain.",
        )
    check(
        "duplicate_dates",
        "fail" if duplicate_rows else "pass",
        f"{len(duplicate_rows)} records belong to duplicated dates; no rows were deduplicated.",
    )

    missing_rows = [row for row in cleaned if row.get("quality_flag") == "missing_pm25_value"]
    for row in missing_rows:
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            record_key=row["source_record_key"],
            observed_date=row["observed_date"],
            issue="missing_pm25_fill_not_applied",
            severity="warning",
            decision="FILL",
            action="not_applied",
            reason="No PM2.5 value is imputed because doing so would fabricate a target observation.",
        )
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            record_key=row["source_record_key"],
            observed_date=row["observed_date"],
            issue="unresolved_missing_pm25",
            severity="warning",
            decision="FLAG",
            action="retained_as_blank_in_cleaned_and_gold",
            reason="Publisher supplied a dated row with no measurement; meaning of blank is undocumented.",
        )
    check(
        "missing_measurements",
        "warning" if missing_rows else "pass",
        f"{len(missing_rows)} blank PM2.5 values retained; fill was not applied.",
    )

    invalid_value_records = [
        row for row in rejected
        if any(
            term in row.get("rejection_reason", "").lower()
            for term in ("negative", "non-finite", "invalid pm2.5", "invalid value")
        )
    ]
    for row in invalid_value_records:
        key = row.get("source_record_key", "")
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            record_key=key,
            issue="invalid_pm25_value",
            severity="critical",
            decision="FLAG",
            action="preserved_in_rejected_records; excluded_from_gold; pipeline_failure",
            reason=row.get("rejection_reason", "Invalid PM2.5 value."),
        )
    invalid_value_count = len(invalid_value_records)
    check(
        "nonnegative_finite_pm25",
        "fail" if invalid_value_count else "pass",
        f"{invalid_value_count} negative, non-finite, or invalid PM2.5 values are preserved as rejects.",
    )

    invalid_rows = [
        row for row in rejected
        if "invalid date" in row.get("rejection_reason", "").lower()
    ]
    for row in invalid_rows:
        key = row.get("source_record_key", "")
        if "invalid date" in row.get("rejection_reason", "").lower():
            _append(
                issues,
                source,
                source_hash,
                checked_at,
                record_key=key,
                issue="invalid_source_date",
                severity="critical",
                decision="FLAG",
                action="preserved_in_rejected_records; excluded_from_gold; pipeline_failure",
                reason=row.get("rejection_reason", "Invalid date."),
            )

    for row in cleaned:
        raw_value = row.get("source_value_raw", "")
        normalized = row.get("value", "")
        if raw_value and normalized:
            try:
                numerically_equal = Decimal(raw_value) == Decimal(normalized)
            except InvalidOperation:
                numerically_equal = False
            if numerically_equal and raw_value != normalized:
                _append(
                    issues,
                    source,
                    source_hash,
                    checked_at,
                    record_key=row["source_record_key"],
                    observed_date=row["observed_date"],
                    issue="numeric_representation_normalized",
                    severity="info",
                    decision="FIX",
                    action="normalized_numeric_value; exact_source_value_preserved",
                    reason="Deterministic numeric parsing changes only textual representation; source_value_raw preserves the publisher string.",
                )
    fix_count = sum(row["decision"] == "FIX" for row in issues)
    check(
        "safe_normalization",
        "warning" if fix_count else "pass",
        f"{fix_count} deterministic numeric text normalizations; raw strings remain in source_value_raw.",
    )

    parse_stats = base_quality
    observed_dates = sorted(
        row.get("observed_date", "") for row in cleaned if row.get("observed_date")
    )
    expected_gaps: list[str] = []
    if observed_dates:
        first = date.fromisoformat(observed_dates[0])
        last = date.fromisoformat(observed_dates[-1])
        known = set(observed_dates)
        current = first
        while current <= last:
            if current.isoformat() not in known:
                expected_gaps.append(current.isoformat())
            current = date.fromordinal(current.toordinal() + 1)
    reported_gaps = base_quality.get("missing_dates_within_observed_span", [])
    gaps = sorted(set(expected_gaps) | set(reported_gaps))
    if gaps:
        for missing_date in gaps:
            _append(
                issues,
                source,
                source_hash,
                checked_at,
                observed_date=missing_date,
                issue="missing_calendar_date",
                severity="warning",
                decision="FLAG",
                action="not_filled",
                reason="No source observation exists for this date; no observation was fabricated.",
            )
    check(
        "date_continuity",
        "warning" if gaps else "pass",
        f"{len(gaps)} absent calendar dates inside the observed bounds; none were filled.",
    )

    try:
        readiness.audit_warehouse_layers(raw_path, cleaned_path, gold_path)
        lineage_status = "pass"
        lineage_detail = "Raw, cleaned, and gold values, row IDs, record keys, and file hashes agree."
    except readiness.ReadinessAuditError as exc:
        lineage_status = "fail"
        match = re.search(r"record (\d+)", str(exc))
        record_key = ""
        observed_date = ""
        if match:
            row_index = int(match.group(1)) - 1
            if 0 <= row_index < len(cleaned):
                record_key = cleaned[row_index].get("source_record_key", "")
                observed_date = cleaned[row_index].get("observed_date", "")
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            record_key=record_key,
            observed_date=observed_date,
            issue="raw_cleaned_gold_lineage_mismatch",
            severity="critical",
            decision="FLAG",
            action="pipeline_failure; no lineage repair attempted",
            reason=str(exc),
        )
        lineage_detail = str(exc)
    check("raw_cleaned_gold_lineage", lineage_status, lineage_detail)

    row_ids = [row.get("row_id", "") for row in gold]
    unique_row_ids = len(row_ids) == len(set(row_ids)) and all(row_ids)
    check(
        "gold_row_id_uniqueness",
        "pass" if unique_row_ids else "fail",
        "All gold row IDs are present and unique."
        if unique_row_ids
        else "Gold row IDs are missing or duplicated.",
    )
    if not unique_row_ids and lineage_status == "pass":
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            issue="gold_row_id_uniqueness_failure",
            severity="critical",
            decision="FLAG",
            action="pipeline_failure",
            reason="Stable row IDs are required for lineage; no IDs are invented or rewritten.",
        )

    latest_date_text = max(observed_dates) if observed_dates else None
    today = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    age_days = (today - date.fromisoformat(latest_date_text)).days if latest_date_text else None
    stale = age_days is None or age_days > warning_days
    check(
        "source_freshness",
        "warning" if stale else "pass",
        f"Latest observation {latest_date_text}; age {age_days} days against {warning_days}-day warning threshold."
        if latest_date_text
        else "No observation date is available.",
    )
    if stale:
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            issue="stale_source_observations",
            severity="warning",
            decision="FLAG",
            action="no_substitution_or_backfill",
            reason="The source ends before the configured freshness threshold; acquisition time does not make old observations current.",
        )

    check(
        "measurement_methodology_documentation",
        "warning",
        "PAQI station identity, aggregation, exact timezone/window, QA, and blank-value meaning remain unresolved.",
    )
    for issue_name, reason in (
        (
            "station_identity_unresolved",
            "The source schema contains no station identifier, coordinates, or instrument identifier.",
        ),
        (
            "measurement_aggregation_unresolved",
            "PAQI describes a monitoring network but does not specify per-day monitor count or aggregation rule.",
        ),
        (
            "daily_time_convention_unresolved",
            "The source has date-only values; the exact 24-hour window and timezone are not specified.",
        ),
        (
            "measurement_qa_unresolved",
            "Calibration, validation, QA/QC thresholds, and maintenance history are not documented in inspected source materials.",
        ),
        (
            "missing_value_semantics_unresolved",
            "The publisher does not explain what blank PM2.5 cells mean or how incomplete days were handled.",
        ),
    ):
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            issue=issue_name,
            severity="warning",
            decision="FLAG",
            action="disclosed; no measurement correction",
            reason=reason,
        )
    check(
        "cross_source_independence",
        "warning",
        "Only PAQI is approved for this pipeline; independent second-source compliance is not established.",
    )
    _append(
        issues,
        source,
        source_hash,
        checked_at,
        issue="independent_second_source_unverified",
        severity="warning",
        decision="FLAG",
        action="not_claimed",
        reason="EPA reuse/provenance and OpenAQ source overlap are unresolved; the PAQI republication routes are not independent sources.",
    )

    fetch_timestamp = _manifest_fetch_time(manifest_path, source_hash)
    if fetch_timestamp is None:
        check("acquisition_manifest_lineage", "fail", "No manifest record matches the raw source hash.")
        _append(
            issues,
            source,
            source_hash,
            checked_at,
            issue="manifest_provenance_missing",
            severity="critical",
            decision="FLAG",
            action="pipeline_failure",
            reason="The raw artifact has no matching acquisition manifest record.",
        )
    else:
        check(
            "acquisition_manifest_lineage",
            "pass",
            f"Manifest includes the raw source hash; fetch timestamp {fetch_timestamp}.",
        )

    check_statuses = [value["status"] for value in checks.values()]
    passed_checks = check_statuses.count("pass")
    warning_checks = check_statuses.count("warning")
    failed_checks = check_statuses.count("fail")
    fixes = sum(row["decision"] == "FIX" for row in issues)
    fills = sum(
        row["decision"] == "FILL" and row["action_taken"] != "not_applied"
        for row in issues
    )
    flags = sum(row["decision"] == "FLAG" for row in issues)
    status = (
        "failure" if failed_checks else "success_with_warnings" if warning_checks else "success"
    )
    report = {
        "agent": "deterministic_data_quality_agent",
        "agent_version": 1,
        "run_id": run_id,
        "checked_at_utc": checked_at,
        "source_id": source["source_id"],
        "source_version": source["version"],
        "source_file_sha256": source_hash,
        "source_observation_latest_date": latest_date_text,
        "source_age_days": age_days,
        "freshness_warning_days": warning_days,
        "status": status,
        "checks": checks,
        "counts": {
            "passed_checks": passed_checks,
            "warning_checks": warning_checks,
            "failed_checks": failed_checks,
            "issues": len(issues),
            "fixes": fixes,
            "fills_applied": fills,
            "fills_not_applied": sum(
                row["decision"] == "FILL" and row["action_taken"] == "not_applied"
                for row in issues
            ),
            "flags": flags,
            "record_level_issues": sum(bool(row["source_row_id"]) for row in issues),
            "source_level_issues": sum(not row["source_row_id"] for row in issues),
        },
        "count_scope": "current_run_only",
        "audit_log_scope": "append_only_history",
        "source_level_issues": [
            row for row in issues if not row["source_row_id"]
        ],
        "record_level_issue_count": sum(bool(row["source_row_id"]) for row in issues),
        "two_source_compliance": "not_established",
        "decisions": {
            "FIX": "Apply only a deterministic representation normalization while preserving the exact original value.",
            "FILL": "No target imputation in this phase; record not_applied and preserve the missing label.",
            "FLAG": "Retain the issue for review; do not silently correct, drop, or fabricate data.",
        },
    }
    return report, issues


def schema_failure_result(
    *,
    raw_path: Path,
    source: dict[str, Any],
    run_id: str = "",
    checked_at: datetime | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    timestamp = (checked_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    checked_text = timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        with raw_path.open(encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream, strict=True), [])
    except (OSError, csv.Error) as exc:
        raise DataQualityAgentError(f"Cannot inspect source schema: {exc}") from exc
    source_hash = sha256_file(raw_path)
    issue = _issue(
        checked_at=checked_text,
        row_id="",
        record_key="",
        observed_date="",
        issue="schema_change",
        severity="critical",
        decision="FLAG",
        action="pipeline_failure; raw source preserved",
        reason=f"Received columns {header!r}; expected {source['expected_header']!r}. No reinterpretation attempted.",
        source_hash=source_hash,
    )
    return (
        {
            "agent": "deterministic_data_quality_agent",
            "agent_version": 1,
            "run_id": run_id,
            "checked_at_utc": checked_text,
            "source_id": source["source_id"],
            "source_version": source["version"],
            "source_file_sha256": source_hash,
            "status": "failure",
            "checks": {
                "required_columns_and_schema": {
                    "status": "fail",
                    "detail": issue["reason"],
                }
            },
            "counts": {
                "passed_checks": 0,
                "warning_checks": 0,
                "failed_checks": 1,
                "issues": 1,
                "fixes": 0,
                "fills_applied": 0,
                "fills_not_applied": 0,
                "flags": 1,
                "record_level_issues": 0,
                "source_level_issues": 1,
            },
            "count_scope": "current_run_only",
            "audit_log_scope": "append_only_history",
            "source_level_issues": [issue],
            "record_level_issue_count": 0,
            "two_source_compliance": "not_established",
        },
        [issue],
    )
