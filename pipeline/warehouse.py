"""`make data`: rebuild every source's raw/cleaned/gold layers, then run warehouse-level cross-source checks.

Outputs
  data/processed/gold_karachi_daily_cross_source.csv   PAQI daily value next to the U.S. Consulate daily mean
  data/quality/warehouse_quality_report.json          per-source status, row counts, agreement statistics
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline import run as paqi
from pipeline import urban_unit, us_consulate
from pipeline.run import atomic_csv, atomic_json, utc_text

ROOT = Path(__file__).resolve().parents[1]
CROSS_FIELDS = [
    "date",
    "paqi_pm25_ug_m3",
    "us_consulate_daily_mean_ug_m3",
    "us_consulate_valid_hours",
    "difference_paqi_minus_consulate",
    "quality_flag",
    "paqi_row_id",
    "us_consulate_row_id",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs)
    syy = sum((y - mean_y) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def cross_source(root: Path = ROOT) -> dict[str, Any]:
    paqi_rows = {row["observed_date"]: row for row in _read_csv(root / "data" / "processed" / "gold_air_quality.csv")}
    consulate_rows = {
        row["local_date"]: row
        for row in _read_csv(root / "data" / "processed" / "gold_us_consulate_karachi_daily.csv")
    }

    merged = []
    for day in sorted(set(paqi_rows) & set(consulate_rows)):
        paqi_value = paqi_rows[day]["value"]
        consulate_value = consulate_rows[day]["pm25_daily_mean_ug_m3"]
        both = paqi_value != "" and consulate_value != ""
        merged.append(
            {
                "date": day,
                "paqi_pm25_ug_m3": paqi_value,
                "us_consulate_daily_mean_ug_m3": consulate_value,
                "us_consulate_valid_hours": consulate_rows[day]["valid_hours"],
                "difference_paqi_minus_consulate": f"{float(paqi_value) - float(consulate_value):.2f}" if both else "",
                "quality_flag": "paired" if both else "unpaired_missing_value",
                "paqi_row_id": paqi_rows[day]["row_id"],
                "us_consulate_row_id": consulate_rows[day]["row_id"],
            }
        )
    paired = [row for row in merged if row["quality_flag"] == "paired"]
    xs = [float(row["paqi_pm25_ug_m3"]) for row in paired]
    ys = [float(row["us_consulate_daily_mean_ug_m3"]) for row in paired]
    diffs = [x - y for x, y in zip(xs, ys)]
    outliers = 0
    if len(diffs) >= 4:
        q1, _, q3 = statistics.quantiles(diffs, n=4)
        low, high = q1 - 3 * (q3 - q1), q3 + 3 * (q3 - q1)
        for row in paired:
            if not low <= float(row["difference_paqi_minus_consulate"]) <= high:
                row["quality_flag"] = "paired_large_disagreement"
                outliers += 1
    atomic_csv(root / "data" / "processed" / "gold_karachi_daily_cross_source.csv", CROSS_FIELDS, merged)
    r = _pearson(xs, ys)
    return {
        "overlap_days": len(merged),
        "paired_days": len(paired),
        "first_paired_date": paired[0]["date"] if paired else None,
        "last_paired_date": paired[-1]["date"] if paired else None,
        "pearson_r": round(r, 3) if r is not None else None,
        "mean_difference_paqi_minus_consulate": round(statistics.fmean(diffs), 2) if diffs else None,
        "mean_absolute_difference": round(statistics.fmean(abs(d) for d in diffs), 2) if diffs else None,
        "paqi_mean_on_paired_days": round(statistics.fmean(xs), 2) if xs else None,
        "consulate_mean_on_paired_days": round(statistics.fmean(ys), 2) if ys else None,
        "large_disagreement_days": outliers,
        "large_disagreement_rule": "difference outside [Q1 - 3·IQR, Q3 + 3·IQR] of paired daily differences; flagged, not removed",
        "date_alignment_caveat": "PAQI does not publish its day boundary/timezone; Consulate days are Asia/Karachi local days.",
    }


def _paqi_latest_date(root: Path) -> str | None:
    try:
        return json.loads((root / "data" / "quality" / "quality_report.json").read_text(encoding="utf-8")).get(
            "last_observation_date"
        )
    except (OSError, json.JSONDecodeError):
        return None


def run_warehouse(root: Path = ROOT, *, now: datetime | None = None) -> tuple[int, dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    paqi_code, paqi_status = paqi.run_pipeline(root)
    run_id = paqi_status.get("run_id", "")
    consulate_code, consulate_report = us_consulate.run_source_pipeline(root, run_id=run_id, now=now)
    network_code, network_report = urban_unit.run_source_pipeline(root, run_id=run_id, now=now)

    checks: dict[str, Any] = {}
    agreement: dict[str, Any] = {}
    if paqi_code == 0 and consulate_code == 0:
        agreement = cross_source(root)
        r = agreement["pearson_r"]
        checks["cross_source_agreement"] = {
            "status": "pass" if r is not None and r >= 0.5 else "warning",
            "detail": (
                f"{agreement['paired_days']} days with both sources; Pearson r = {r}, mean PAQI − Consulate = "
                f"{agreement['mean_difference_paqi_minus_consulate']} µg/m³, {agreement['large_disagreement_days']} "
                "days flagged for large disagreement."
            ),
        }
        checks["two_independent_publishers"] = {
            "status": "pass",
            "detail": (
                "PAQI (Zenodo, CC BY 4.0) and the U.S. Department of State monitor (AirNow via OpenAQ, US Public Domain) "
                "are different original publishers. PAQI does not document its input monitors, so measurement-level "
                "independence is reported as agreement statistics rather than assumed."
            ),
        }
    else:
        checks["source_pipelines"] = {"status": "fail", "detail": "At least one source pipeline failed; see its report."}

    sources = [
        {
            "source_id": paqi_status.get("source_id", "paqi_karachi_daily_pm25"),
            "publisher": "Pakistan Air Quality Initiative (PAQI)",
            "access": "https://doi.org/10.5281/zenodo.15845428",
            "license": "CC BY 4.0",
            "resolution": "daily",
            "gold_rows": paqi_status.get("gold_record_count"),
            "status": paqi_status.get("status"),
            "latest_observation": _paqi_latest_date(root),
            "quality_report": "data/quality/quality_report.json",
        },
        {
            "source_id": consulate_report.get("source_id"),
            "publisher": consulate_report.get("original_publisher"),
            "access": "https://api.openaq.org/v3/locations/8156",
            "license": consulate_report.get("license"),
            "resolution": "hourly (daily means derived)",
            "gold_rows": consulate_report.get("hourly_gold_rows"),
            "daily_gold_rows": consulate_report.get("daily_gold_rows"),
            "status": consulate_report.get("status"),
            "latest_observation": consulate_report.get("last_observation_utc"),
            "quality_report": "data/quality/us_consulate_quality_report.json",
        },
        {
            "source_id": network_report.get("source_id"),
            "publisher": network_report.get("original_publisher"),
            "access": "https://explore.openaq.org/",
            "license": network_report.get("license"),
            "resolution": f"hourly, {network_report.get('sensors')} sensors (daily means derived)",
            "gold_rows": network_report.get("hourly_gold_rows"),
            "daily_gold_rows": network_report.get("sensor_daily_rows"),
            "status": network_report.get("status"),
            "latest_observation": network_report.get("last_observation_utc"),
            "latest_age_hours": network_report.get("latest_age_hours"),
            "quality_report": "data/quality/urban_unit_quality_report.json",
        },
    ]
    statuses = [check["status"] for check in checks.values()]
    failed = paqi_code != 0 or consulate_code != 0 or network_code != 0 or "fail" in statuses
    report = {
        "generated_at_utc": utc_text(now),
        "run_id": run_id,
        "status": "failure" if failed else "success_with_warnings",
        "two_source_compliance": "established" if not failed else "not_established",
        "total_gold_rows": sum(int(source["gold_rows"] or 0) for source in sources),
        "latest_observation_utc": network_report.get("last_observation_utc"),
        "latest_observation_age_hours": network_report.get("latest_age_hours"),
        "sources": sources,
        "checks": checks,
        "cross_source": agreement,
    }
    atomic_json(root / "data" / "quality" / "warehouse_quality_report.json", report)
    return (1 if failed else 0), report


def main() -> int:
    code, report = run_warehouse()
    print(json.dumps({key: report[key] for key in ("status", "two_source_compliance", "total_gold_rows", "checks")},
                     indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
