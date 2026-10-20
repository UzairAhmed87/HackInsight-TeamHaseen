# Stage A — Live monitoring audit & implementation plan

**Repo used:** `D:\Courses\Hackathons\HackInsight\HackInsight-TeamHaseen`  
(Note: `D:\HackInsight` does not exist on this machine.)  
**Live dashboard today:** https://hackinsight-air-quality-pakistan.onrender.com/  
**Audit time (UTC):** 2026-10-20 ~17:20–17:22  
**Evidence dump:** `docs/live_source_audit_stage_a.json`

This is **Stage A only**. No live UI was implemented yet.

---

## 1. Current repository (what exists)

| Area | Finding |
|------|---------|
| Server | `pipeline/dashboard.py` — stdlib `ThreadingHTTPServer`, binds `PORT` |
| Routes | `GET /`, static assets; `GET /api/dashboard`; `POST /api/ask` |
| Data | Frozen PAQI gold table through **2024-12-31** (~3009 daily rows) |
| Forecast | Historical backtest only (linear vs persistence); not live |
| Insight Agent | Evidence-bound; abstains on “current AQ” without live evidence |
| Deploy | Render Free via `render.yaml`; disk ephemeral |
| Secrets | `.env.example` states no credentials; OpenAQ not approved yet |
| Two-source rule | Still **not** met (PAQI only in pipeline) |

Historical charts / forecast metrics / Insight Agent must stay intact.

---

## 2. Orangi / OpenAQ / AirGradient verification

### OpenAQ

| Check | Result |
|-------|--------|
| API | v3 only; `X-API-Key` required |
| Unauthenticated PK query | **HTTP 401** (unchanged) |
| Explorer listings | Urban Unit / AirGradient sensors appear (e.g. location pages with **CC BY 4.0**, PM1/PM2.5/RH/temp/PM0.3) |
| Orangi via OpenAQ API | **UNVERIFIED** without key — cannot confirm location ID or latest measurements from here |

### AirGradient public API (verified live)

| Check | Result |
|-------|--------|
| Endpoint | `GET https://api.airgradient.com/public/api/v1/world/locations/measures/current` |
| Auth | **None** (`security: []` in official swagger) |
| Live test | **HTTP 200**, ~2926 public locations |
| Place-token endpoints | Need `token` query param → **422** without token (not usable for us) |
| Single public location | `GET .../world/locations/{locationId}/measures/current` works when ID is public |

**Official swagger:** https://api.airgradient.com/public/docs/api/v1/swagger.json  

Fields observed: `locationId`, `locationName`, `latitude`, `longitude`, `pm01` (PM1), `pm02` (PM2.5), `pm10`, `pm003Count`, `atmp`, `rhum`, `timestamp` (UTC ISO), `offline`, `publicContributorName`, `model`, etc.

### Orangi Pilot Project specifically

| Claim | Evidence |
|-------|----------|
| Listed on AQICN as Orangi Pilot Project / “The Urban Unit **162802**” | https://aqicn.org/station/validation/@545503/ |
| AirGradient public world list name match `orangi` / `pilot` / `site town` | **0 hits** at audit time |
| `GET .../world/locations/162802/measures/current` | **HTTP 404** |
| Conclusion | Orangi is **not currently fetchable** via the public AirGradient world API. Do **not** hardcode a fake Orangi reading. |

### What *is* available in Karachi right now (public AirGradient)

Bounding box ~24.7–25.2 N, 66.8–67.4 E found **7** Urban Unit / O-1PST sensors, including:

| locationId | Name | PM2.5 (`pm02`) at audit | Timestamp (UTC) |
|------------|------|-------------------------|-----------------|
| 162753 | Asif Gulistan-e-Johar | 45.7 | 2026-10-20T17:21:43Z |
| 162364 | Climate Action Center | ~37.8→40.0 | ~17:21–17:22Z |
| 162379 | Urban Resource Center | 46.7 | 2026-10-20T17:21:27Z |
| 162732 | NED Main Campus | 35.7 | 2026-10-20T17:21:23Z |
| 162762 | Engr Muzaffar Malir Cantonment, Askari 5 | 48.8 | 2026-10-20T17:21:16Z |
| 206703 | Maqsood Memon Clifton | 36.5 | 2026-10-20T17:19:44Z |
| 162672 | Aga khan University Main Campus | **null** PM (temp/RH present) | 2026-10-20T17:22:32Z |

All `publicContributorName`: **The Urban Unit**; `offline`: false in sample.

**Critical product rule:** these are **point sensors**, not “Karachi city AQI”.

### Licensing

- OpenAQ Explorer shows Urban Unit / AirGradient listings as **CC BY 4.0** (attribute OpenAQ + original provider when using OpenAQ).
- AirGradient public world feed: redistributable public location data per product use; keep **provider, location name, link, timestamp**; do not imply AirGradient/Urban Unit endorsement.
- Exact legal text for AG world feed beyond swagger “public to the world”: treat as **public read-only**; document attribution in UI + `docs/source_register.csv`.

### Rate limits / deploy

- Full world dump is **~1.5 MB** — too heavy to pull on every page load.
- Prefer **pinned `locationId`(s)** via single-location URL (small JSON).
- Timeout ≤10–15s; cache in memory for e.g. 60–120s (Render Free; no paid DB required for “latest reading”).
- No aggressive background polling while idle.

### Double-counting

OpenAQ and AirGradient often expose the **same** Urban Unit hardware. Pick **one primary** for live panel (recommend **AirGradient public** — no key). If OpenAQ is added later, mark as alternate feed of the same sensor, not a second independent measurement.

---

## 3. Recommended primary source (Stage B)

**Primary:** AirGradient public world API, **pinned Karachi locationId(s)** from the verified table above.  

**Default first sensor (proposed):** `162753` — Asif Gulistan-e-Johar (non-null PM2.5 at audit).  
**Config-driven:** allowlist in `config/live_sensors.json` so Orangi can be added when public ID is confirmed.

**Orangi:** keep as **target / unresolved** until:
1. `162802` (or true ID) returns 200 on public AG API, **or**
2. OpenAQ key resolves the Orangi location and licence fields.

**Do not** label any reading as citywide Karachi AQ.

---

## 4. Freshness definition (to implement)

| State | Rule (proposed) |
|-------|-----------------|
| **Live/Recent** | `offline=false` and measurement `timestamp` age ≤ **30 minutes** |
| **Stale** | measurement age > 30 min and ≤ **6 hours**, or fetch succeeded but data old |
| **Unavailable** | HTTP error/timeout, empty body, `offline=true`, missing PM2.5 when required, or age > 6 hours |

Always show separately:
- **Observation timestamp** (sensor) — display in **Asia/Karachi (PKT)**
- **Last successful application fetch** (UTC + PKT)

Page refresh ≠ new observation unless upstream timestamp advanced.

---

## 5. Forecasting (Stage B scope)

**Out of MVP.** Keep existing historical forecast panel unchanged.  
Live short-term forecast only after enough sensor history exists and chronological eval vs persistence is documented. Until then Insight Agent must abstain on “live forecast” claims.

---

## 6. Architecture (smallest reliable change)

```
AirGradient public GET /world/locations/{id}/measures/current
        ↓
pipeline/live_sensors.py  (fetch, validate, freshness, normalize)
        ↓
in-memory cache (+ optional data/live/*.json best-effort, not relied on for Render persistence)
        ↓
GET /api/live   + extend /api/dashboard payload with live block
        ↓
dashboard Live Sensor Monitoring section
        ↓
Insight Agent: optional read of /api/live evidence for “latest Orangi/Johar reading” only
```

Do **not** mutate `data/processed/gold_air_quality.csv` or historical forecast artifacts.

---

## 7. Files expected to change (Stage B)

| File | Change |
|------|--------|
| `config/live_sensors.json` | **New** — pinned IDs, labels, attribution URLs, freshness thresholds |
| `pipeline/live_sensors.py` | **New** — fetch + validate + freshness |
| `pipeline/dashboard.py` | Add `GET /api/live`; include live summary in dashboard payload (fail-soft) |
| `dashboard/index.html` | “Live Sensor Monitoring” section |
| `dashboard/styles.css` | Styles for live panel / states |
| `dashboard/app.js` | Render live panel; never invent numbers |
| `pipeline/insight_agent.py` | Optional: answer latest-reading questions from live evidence; still abstain if unavailable |
| `docs/source_register.csv` | Add AirGradient / Urban Unit live candidate row |
| `tests/test_live_sensors.py` | **New** — mocked success/stale/error/null PM |
| `tests/test_dashboard.py` | Extend for `/api/live` fail-soft |
| `.env.example` | Note: no key required for AG public; optional `OPENAQ_API_KEY` later |
| `docs/live_monitoring.md` | Operator notes + freshness rules |

**Unchanged unless needed:** `pipeline/run.py` gold pipeline, `forecasting.py` artifacts, PAQI raw hashes.

---

## 8. Test plan

```text
python -m unittest discover -s tests -v
python -m py_compile pipeline/*.py
node --check dashboard/app.js
```

Mocks only for live HTTP — no dependency on upstream uptime in CI.

---

## 9. Remaining risks / manual steps

1. Confirm with team: **default sensor** (propose `162753`) vs wait for Orangi.  
2. Optional: obtain OpenAQ key to locate Orangi location ID + licence fields.  
3. After merge: push → Render autoDeploy; cold start may delay first live fetch.  
4. Two-source warehouse compliance remains a **separate** hackathon gate (Open-Meteo / OpenAQ historical) — live panel does not by itself close that gate.

---

## 10. Stage B go / no-go

| Gate | Status |
|------|--------|
| Public API without paid infra | **PASS** (AirGradient world) |
| Real Karachi live PM2.5 obtainable | **PASS** (multiple IDs) |
| Exact Orangi Pilot Project ID public | **FAIL / UNVERIFIED** right now |
| Compatible with Render stdlib server | **PASS** |
| Honest labeling (not citywide) | Required in UI copy |

**Recommendation:** **GO for Stage B** with pinned public Karachi sensor(s) + explicit Orangi “not yet available on public API” disclosure.  
**NO-GO** for claiming Orangi live readings until ID returns 200.

---

## Decision needed from you before coding

Reply with one option:

1. **Implement now** with default sensor `162753` (Asif Gulistan-e-Johar), config allowlist for other Karachi IDs, Orangi marked unavailable until verified.  
2. **Wait** until OpenAQ key finds Orangi specifically.  
3. **Multi-sensor panel** for all 7 verified Karachi public sensors (still not citywide aggregate).
