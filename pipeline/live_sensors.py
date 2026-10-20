"""Fetch and normalize public AirGradient live outdoor readings (no secrets)."""
from __future__ import annotations

import json
import os
import ssl
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = Path("config/live_sensors.json")
USER_AGENT = "HackInsight26-live-sensors/1.0"

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {"expires_at": None, "payload": None}


class LiveSensorError(Exception):
    """Raised for configuration problems (not upstream outages)."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _load_config(root: Path) -> dict[str, Any]:
    path = root / CONFIG_RELATIVE
    try:
        with path.open(encoding="utf-8") as stream:
            config = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise LiveSensorError(f"Cannot load live sensor config: {exc}") from exc
    if not isinstance(config, dict) or "sensors" not in config:
        raise LiveSensorError("live_sensors.json must contain a sensors list.")
    return config


def _parse_timestamp(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_pkt(value: datetime | None, tz_name: str) -> str | None:
    if value is None:
        return None
    try:
        zone = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - fall back to fixed offset label
        zone = timezone(timedelta(hours=5), name="PKT")
    return value.astimezone(zone).isoformat(timespec="seconds")


def _freshness_state(
    observed_at: datetime | None,
    *,
    now: datetime,
    offline: bool,
    fresh_max_minutes: int,
    stale_max_minutes: int,
    has_pm25: bool,
) -> str:
    if offline or observed_at is None or not has_pm25:
        return "unavailable"
    age = now - observed_at
    if age < timedelta(0):
        # Clock skew: treat as fresh but still show the raw timestamp.
        return "fresh"
    minutes = age.total_seconds() / 60.0
    if minutes <= fresh_max_minutes:
        return "fresh"
    if minutes <= stale_max_minutes:
        return "delayed"
    return "stale"


def _http_get_json(
    url: str,
    *,
    timeout: float,
    opener: Callable[..., Any] | None = None,
) -> tuple[int | None, dict[str, Any] | list[Any] | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request, context=ssl.create_default_context(), timeout=timeout) as response:
            body = response.read()
            status = getattr(response, "status", None) or response.getcode()
            try:
                parsed = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return status, None, "Response was not valid JSON."
            if not isinstance(parsed, (dict, list)):
                return status, None, "Unexpected JSON payload type."
            return status, parsed, None
    except urllib.error.HTTPError as exc:
        detail = None
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:  # noqa: BLE001
            detail = str(exc)
        return exc.code, None, detail
    except Exception as exc:  # noqa: BLE001 - surface upstream failures to UI
        return None, None, f"{type(exc).__name__}: {exc}"


def _normalize_reading(
    sensor_cfg: dict[str, Any],
    payload: dict[str, Any] | None,
    *,
    http_status: int | None,
    error: str | None,
    fetched_at: datetime,
    config: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    freshness_cfg = config.get("freshness") or {}
    tz_name = str(config.get("display_timezone") or "Asia/Karachi")
    observed_at = _parse_timestamp((payload or {}).get("timestamp")) if payload else None
    offline = bool((payload or {}).get("offline")) if payload else True
    pm25 = (payload or {}).get("pm02")
    pm1 = (payload or {}).get("pm01")
    pm10 = (payload or {}).get("pm10")
    temperature = (payload or {}).get("atmp")
    humidity = (payload or {}).get("rhum")
    particle_count = (payload or {}).get("pm003Count")

    def _finite(value: Any) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number != number or number in (float("inf"), float("-inf")) or number < 0:
            return None
        return number

    pm25_n = _finite(pm25)
    state = _freshness_state(
        observed_at,
        now=now,
        offline=offline if payload is not None else True,
        fresh_max_minutes=int(freshness_cfg.get("fresh_max_age_minutes", 30)),
        stale_max_minutes=int(freshness_cfg.get("stale_max_age_minutes", 360)),
        has_pm25=pm25_n is not None,
    )
    if error or payload is None:
        state = "unavailable"

    location_name = (
        (payload or {}).get("publicLocationName")
        or (payload or {}).get("locationName")
        or sensor_cfg.get("label")
    )
    return {
        "location_id": sensor_cfg.get("location_id"),
        "configured_label": sensor_cfg.get("label"),
        "area": sensor_cfg.get("area"),
        "primary": bool(sensor_cfg.get("primary")),
        "location_name": location_name,
        "latitude": (payload or {}).get("latitude"),
        "longitude": (payload or {}).get("longitude"),
        "offline": offline if payload is not None else None,
        "pm25_ug_m3": pm25_n,
        "pm1_ug_m3": _finite(pm1),
        "pm10_ug_m3": _finite(pm10),
        "temperature_c": _finite(temperature),
        "relative_humidity_pct": _finite(humidity) if humidity is not None else None,
        "pm03_count": int(particle_count) if isinstance(particle_count, (int, float)) and particle_count == particle_count else None,
        "model": (payload or {}).get("model"),
        "contributor": (payload or {}).get("publicContributorName"),
        "observation_time_utc": observed_at.isoformat(timespec="seconds").replace("+00:00", "Z") if observed_at else None,
        "observation_time_pkt": _format_pkt(observed_at, tz_name),
        "fetched_at_utc": fetched_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "fetched_at_pkt": _format_pkt(fetched_at, tz_name),
        "freshness": state,
        "http_status": http_status,
        "error": error,
        "source_endpoint": (
            f"{str(config['provider']['base_url']).rstrip('/')}/world/locations/"
            f"{sensor_cfg.get('location_id')}/measures/current"
        ),
    }


def fetch_live_snapshot(
    root: Path = ROOT,
    *,
    now: datetime | None = None,
    use_cache: bool = True,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Return a dashboard-safe live snapshot. Upstream failures never raise."""
    root = root.resolve()
    now = now or _utc_now()
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware.")

    config = _load_config(root)
    if os.environ.get("HACKINSIGHT_DISABLE_LIVE", "").strip().lower() in {"1", "true", "yes"}:
        return {
            "generated_at_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "provider": config.get("provider") or {},
            "coverage_disclaimer": config.get("coverage_disclaimer"),
            "unavailable_targets": config.get("unavailable_targets", []),
            "freshness_thresholds_minutes": {
                "fresh_max": int((config.get("freshness") or {}).get("fresh_max_age_minutes", 30)),
                "stale_after": int((config.get("freshness") or {}).get("stale_max_age_minutes", 360)),
            },
            "display_timezone": config.get("display_timezone", "Asia/Karachi"),
            "sensors": [],
            "primary_sensor": None,
            "available_pm25_sensor_count": 0,
            "status": "unavailable",
            "cache_hit": False,
            "notes": [
                "Live network fetch disabled by HACKINSIGHT_DISABLE_LIVE (used for offline tests).",
            ],
            "error": "Live network fetch disabled for this process.",
        }
    ttl = int(config.get("cache_ttl_seconds", 90))
    if use_cache:
        with _CACHE_LOCK:
            expires = _CACHE.get("expires_at")
            payload = _CACHE.get("payload")
            if (
                isinstance(expires, datetime)
                and payload is not None
                and now < expires
            ):
                cached = dict(payload)
                cached["cache_hit"] = True
                return cached

    provider = config.get("provider") or {}
    base = str(provider.get("base_url") or "").rstrip("/")
    timeout = float(config.get("request_timeout_seconds", 12))
    sensors = [s for s in config.get("sensors", []) if s.get("enabled", True)]
    readings: list[dict[str, Any]] = []
    fetched_at = _utc_now()

    def _fetch_one(sensor: dict[str, Any]) -> dict[str, Any]:
        location_id = sensor.get("location_id")
        if not isinstance(location_id, int):
            return _normalize_reading(
                sensor,
                None,
                http_status=None,
                error="Invalid location_id in config.",
                fetched_at=fetched_at,
                config=config,
                now=now,
            )
        url = f"{base}/world/locations/{location_id}/measures/current"
        status, body, err = _http_get_json(url, timeout=timeout, opener=opener)
        payload = body if isinstance(body, dict) else None
        if payload is None and err is None:
            err = "Unexpected response shape."
        return _normalize_reading(
            sensor,
            payload,
            http_status=status,
            error=err,
            fetched_at=fetched_at,
            config=config,
            now=now,
        )

    # Preserve configured order while fetching in parallel for demo latency.
    indexed: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(sensors)))) as pool:
        futures = {pool.submit(_fetch_one, sensor): idx for idx, sensor in enumerate(sensors)}
        for future in as_completed(futures):
            indexed[futures[future]] = future.result()
    readings = [indexed[idx] for idx in range(len(sensors))]

    available = [row for row in readings if row.get("freshness") != "unavailable" and row.get("pm25_ug_m3") is not None]
    primary = next((row for row in readings if row.get("primary")), readings[0] if readings else None)
    if primary and primary.get("pm25_ug_m3") is None:
        primary = available[0] if available else primary

    snapshot = {
        "generated_at_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "provider": {
            "name": provider.get("name"),
            "publisher": provider.get("publisher"),
            "docs_url": provider.get("docs_url"),
            "attribution": provider.get("attribution"),
            "license_note": provider.get("license_note"),
        },
        "coverage_disclaimer": config.get("coverage_disclaimer"),
        "unavailable_targets": config.get("unavailable_targets", []),
        "freshness_thresholds_minutes": {
            "fresh_max": int((config.get("freshness") or {}).get("fresh_max_age_minutes", 30)),
            "stale_after": int((config.get("freshness") or {}).get("stale_max_age_minutes", 360)),
        },
        "display_timezone": config.get("display_timezone", "Asia/Karachi"),
        "sensors": readings,
        "primary_sensor": primary,
        "available_pm25_sensor_count": len(available),
        "status": "ok" if available else "unavailable",
        "cache_hit": False,
        "notes": [
            "Live readings are separate from the frozen PAQI historical gold table (ends 2024-12-31).",
            "Freshness compares the sensor observation timestamp to application clock, not page refresh count.",
        ],
    }

    if use_cache:
        with _CACHE_LOCK:
            _CACHE["expires_at"] = now + timedelta(seconds=ttl)
            _CACHE["payload"] = dict(snapshot)
    return snapshot


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE["expires_at"] = None
        _CACHE["payload"] = None
