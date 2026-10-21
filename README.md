# HackInsight '26 — Air Quality Intelligence for Pakistan

Evidence-grounded historical PAQI Karachi PM2.5 research **plus** optional public AirGradient neighbourhood live sensors.

**🎯 Hackathon Submission:**
- **Hugging Face Space:** (deployment in progress)
- **GitHub:** https://github.com/UzairAhmed87/HackInsight-TeamHaseen
- **Tag:** v1.0-final
- **Track:** Air Quality

Live demo: https://hackinsight-air-quality-pakistan.onrender.com/

## What the dashboard shows

- **Historical PAQI gold table** (2016-10-06 → 2024-12-31): coverage, missingness, charts, quality audit.
- **Live Sensor Monitoring**: public AirGradient outdoor locations (The Urban Unit) for Karachi neighbourhoods. Point readings only — **not** citywide AQI. Orangi Pilot Project is documented as unavailable on the public API until verified.
- **Forecast evaluation**: chronological backtest vs persistence (not a live forecast).
- **Insight Agent**: deterministic, evidence-cited answers; abstains on citywide “current Karachi air quality”.

## Phase 2 data pipeline

This repository implements a reproducible **PAQI historical data pipeline**. Phase 1 verified PAQI's versioned Karachi PM2.5 dataset and CC BY 4.0 licence. Independent two-source warehouse compliance for competition dataset rules is still tracked separately and must not be claimed solely because live sensors exist. OpenAQ still requires an API key for authenticated discovery.

### Run

From the repository root:

```sh
make data
```

This requires Python 3.12+ and uses only the standard library. On Windows without GNU Make, run the equivalent:

```powershell
python -m pipeline.run
```

Tests use tiny synthetic **software fixtures only**; those fixtures are never emitted as project data or used for model training/evaluation:

```sh
make test
```

Windows equivalent:

```powershell
python -m unittest discover -s tests -v
```

After acquisition, run the read-only raw/cleaned/gold lineage and forecasting-readiness audit:

```sh
make readiness
```

On Windows without GNU Make, use:

```powershell
python -m pipeline.readiness
```

### Data layout

The pipeline creates these local generated directories:

```text
dashboard/
  index.html
  app.js
  styles.css
data/
  raw/<source_id>/<pinned-version>/<publisher-filename>
  cleaned/paqi_karachi_daily_pm25.csv
  processed/gold_air_quality.csv
  manifests/manifest.csv
  quality/quality_report.json
  quality/quality_log.csv
  quality/rejected_records.csv
  quality/record_issues.csv
  reports/execution_status.json
```

Generated data are ignored by Git. Raw acquisition files and their adjacent provenance sidecars are never overwritten. The manifest is an append-only acquisition/run ledger: cache reuse adds an event with the original fetch timestamp and current recorded timestamp.

### Acquisition and transformations

1. Parse and validate `config/sources.json`. Only the approved, pinned PAQI source can be enabled.
2. Fetch Zenodo's version metadata on each run and validate DOI, CC BY 4.0 licence, exact filename, byte size, and publisher MD5.
3. Reuse a cached raw file only after rechecking byte size and MD5 and requiring its provenance sidecar. Otherwise fetch the pinned CSV over HTTPS, verify size/MD5, calculate SHA-256, and save without replacing existing evidence.
4. Append publisher, source/metadata URLs, request/query, licence, version, UTC fetch time, filename, hash, size, and acquisition status to `manifest.csv`.
5. Normalize the date as a **date-only** ISO value; no timezone or timestamp is invented. PM2.5 remains in the publisher's µg/m³ unit; no conversion, imputation, aggregation, or deduplication is applied.
6. Preserve rejected parsed records and reasons in `quality/rejected_records.csv`; preserve blank measurements in cleaned/gold as flagged nulls and document them in `quality/record_issues.csv`. Critical schema/date/range/duplicate failures make `make data` exit nonzero.
7. Emit a gold row for each date-valid source record, retaining missing measurements as blank numeric values with an explicit quality flag. Its stable `row_id` is SHA-256 of source ID, pinned version, and source record ordinal; source file SHA-256 and source record key provide lineage.
8. Run the deterministic Data Quality Agent against the raw, cleaned, gold, rejected-record, and manifest artifacts. It checks source/warehouse schemas, row shape, date parsing/continuity, duplicate dates, invalid and missing readings, stable gold IDs, raw-to-cleaned-to-gold preservation, source hash/manifest linkage, staleness, and documented methodology/compliance limits.
9. Write aggregate checks and decision counts to `quality/quality_report.json` and row-level decisions to `quality/quality_log.csv`. Since only one source is approved, independent-source compliance is flagged as unresolved.

Execution status records source metadata validation and acquisition outcome before parsing begins. Therefore a network/metadata acquisition failure is distinguishable from a successfully fetched but empty/malformed CSV.

The source record contains no station identifier. `station_id` remains blank, and `city=Karachi` reflects the publisher's dataset label only. The publisher describes a 24-hour network average but does not document the network aggregation, sensor set, timezone/window, QA or missing-day rule. These limitations are retained in the quality report. The pipeline does not construct forecast features or train a model.

### Data Quality Agent rules and decisions

The agent is deterministic, uses no LLM/API, and runs inside `python -m pipeline.run` (`make data`). It does not mutate raw source files or repair lineage inconsistencies.

- `FIX`: only a numeric text normalization already performed by the cleaner when parsing to a canonical finite numeric string; the exact publisher string remains in `source_value_raw` and the log records the reason.
- `FILL`: missing PM2.5 target values are never imputed. The log records `decision=FILL`, `action_taken=not_applied`, and a separate unresolved `FLAG`; the source row remains blank in cleaned/gold.
- `FLAG`: unresolved missing readings, invalid/rejected rows, duplicates, calendar gaps, schema/lineage errors, stale observations, unknown methodology, and unverified second-source status are recorded without silent correction or fabricated values.

Each quality-log row includes the pipeline `run_id`, UTC check time, stable source row ID when a source record exists, source-record key, date when known, issue, severity, decision, action, reason, and raw-file SHA-256. The log is append-only across pipeline runs; source-level issues (such as staleness and unknown methodology) have no row ID. Existing pre-run-ID logs are migrated once by adding a `legacy:<checked_at_utc>` identifier while preserving their issue fields. Critical schema, invalid-record, duplicate, or lineage failures produce `failure` and a nonzero pipeline exit; unresolved warnings produce `success_with_warnings`. The report marks its decision counts as `current_run_only`; the quality log is the cumulative `append_only_history`.

Safe FIX events document the cleaner's canonical numeric representation step; exact source text remains in `source_value_raw`, and an event is emitted only when a changed textual representation parses to the exact same `Decimal` value. The cleaner uses decimal arithmetic for canonical text rather than binary floating-point rounding; negative, non-finite, malformed, overflow, and underflow values remain rejects. In the pinned PAQI file, the 305 FIX events audited in Phase 6B were all integer-valued readings written with a trailing `.0` (for example `22.0` to `22`); exact decimal comparison found no changed numeric value. There were 2,698 unchanged numeric strings and six blank readings. The agent itself does not rewrite observations. This phase does not impute, deduplicate, interpolate missing dates, or alter gold row IDs. The agent cannot verify sensor-level QA or determine why PAQI values are blank. It does not establish two-source compliance or make the historical dataset live/current or representative of all Karachi exposure.

### Licensing, freshness, and release

PAQI is identified as CC BY 4.0. Attribute the listed creators (Omar Abid, Dawar Hameed Butt, Mahad Naveed), PAQI, dataset title and DOI; link the licence and identify modifications; do not imply endorsement. This pipeline keeps all generated data out of public commits by default. Review attribution and any deployment redistribution separately before publishing.

This is a static historical dataset. A new fetch timestamp records acquisition time, **not new observations or hourly freshness**. The report compares the latest observation date with the current UTC date and flags stale coverage.

EPA data are excluded until written reuse permission and provenance are established. OpenAQ is excluded until a team-managed API key is provided through its official flow and source-specific owner/provider/licence and overlap are verified. No secret is required or read by the current pipeline.

### Configuration and environment

`config/sources.json` pins source identity, metadata URL, file URL, licence, filename, expected byte size/MD5, schema and semantic fields. `.env.example` documents that no credentials are used for this source. Do not put API keys or tokens in source configuration or commits.

### Data validity gate before forecasting

Run `make data`, inspect `data/quality/quality_report.json` and `data/reports/execution_status.json`, and require a zero exit code. Resolve critical quality failures before any gold-table use. Review missing-date and freshness warnings and verify full raw-file SHA-256 and lineage. The model's permitted target scope and methodology limitations are documented in `docs/forecasting_readiness.md`.

## Historical next-day forecasting experiment

The first reproducible forecasting experiment uses only the pinned PAQI gold table and the frozen chronological split documented in `docs/forecasting_readiness.md`:

| Split | Dates |
|---|---|
| Train | 2016-10-06–2022-07-12 |
| Validation | 2022-07-13–2023-10-06 |
| Test | 2023-10-07–2024-12-31 |

Run the existing data pipeline first (`make data`, or `python -m pipeline.run` on Windows without GNU Make), then run:

```sh
make forecast
```

Windows equivalent:

```powershell
python -m pipeline.forecasting
```

The command independently checks raw/cleaned/gold preservation and lineage, then reports persistence and ordinary least-squares linear regression metrics. The linear model uses only exact 1-, 2-, and 7-calendar-day PM2.5 lags. A sample is omitted from model fitting/evaluation if any required lag is blank or unavailable; target labels are never imputed. Persistence uses the latest valid reading strictly before the target and records the input age. Candidate-vs-baseline differences are paired on the same model-eligible dates. No model selection or tuning uses the test set.

Outputs are written locally (and ignored by Git):

- `data/reports/forecast_metrics.json` — validation/test MAE and RMSE, matched baseline comparisons, year breakdowns, input-age counts, and validation-residual empirical interval/test coverage.
- `data/reports/forecast_predictions.csv` — one row per gold observation with target, baseline/model predictions, residuals, lag inputs, split, evaluation status (including in-sample training rows), and gold `row_id`.
- `data/reports/forecast_linear_model.json` — fitted coefficients, intercept, training period/count, source version, and raw checksum.

The interval is an empirical 5th–95th percentile of validation residuals, not a guaranteed probabilistic forecast. Test metrics are a historical backtest ending 2024-12-31, not current air-quality conditions. The target is only the published PAQI Karachi series; station/network aggregation and measurement stability remain unresolved, and two-source compliance is not established.

Tests use synthetic values only in isolated software fixtures. They do not create project observations and are never used for model training or evaluation.

## Evidence-grounded Insight Agent

The local Insight Agent answers supported questions from the existing gold table, latest quality report, pinned source register and forecast metrics/predictions. It is a deterministic question router with structured evidence retrieval, not an LLM. Historical/quality/forecast answers use only local artifacts and need no credentials. Questions that specifically ask for a **live sensor** reading may call the public AirGradient world API (no API key) through `pipeline/live_sensors.py`; set `HACKINSIGHT_DISABLE_LIVE=1` to force an offline unavailable state.

From the repository root, ask a question in readable text:

```powershell
python -m pipeline.insight_agent "How did the model compare with persistence on the held-out test set?"
```

Use `--format json` (or `--json`) to print the complete structured response:

```powershell
python -m pipeline.insight_agent "How many PM2.5 readings are missing?" --format json
```

Each response contains `answer`, `status`, evidence file locators and relevant gold row IDs or date ranges, limitations, `generated_at`, and `data_as_of` (latest historical observation date for gold-backed answers, or the live observation timestamp when answering a live-sensor question). Numeric summaries are calculated from the gold table at query time. Forecast claims use the machine-readable test split metrics and are cross-checked against the scored prediction rows. Citywide “current Karachi air quality” and unsupported causal claims abstain; explicit live-sensor questions may report a neighbourhood point reading with freshness and attribution, never a citywide index. Methodology questions identify what is known and what remains undocumented. The agent does not establish two-source compliance or a health-warning service.

## Air Quality Intelligence dashboard

The dashboard uses only Python's standard library on the backend and local HTML/CSS/JavaScript assets on the frontend; no package installation, paid API, or browser chart CDN is required. It serves the gold series, quality report, latest execution status, forecast artifacts and source register without changing them. The optional live panel and `/api/live` endpoint fetch public AirGradient current measures server-side (not from browser JavaScript).

Run locally from the repository root on Windows:

```powershell
python -m pipeline.dashboard
```

Then open `http://127.0.0.1:8000/`. GNU Make users can run `make dashboard`. The app honors the host-provided `PORT` environment variable and can bind publicly with `python -m pipeline.dashboard --host 0.0.0.0`.

The dashboard provides the observation range/counts and computed freshness, daily history with missing records shown as chart gaps, annual summaries, current-run quality counts (separate from append-only log history), validation/test comparisons against matched persistence, and links/disclosures for source and licence limitations. Its Insight Agent form calls the existing local agent directly in-process through a fixed JSON endpoint—no shell or subprocess execution. The endpoint accepts only a bounded JSON question string, has no arbitrary command/path interface, and returns the agent's evidence references and limitations. Public API errors are generic and do not include local file paths. Historical metrics are not presented as current readings or an operational forecast.

### Free public hosting on Render

The repository includes [`render.yaml`](./render.yaml) for a native Python Web Service on Render's Free plan. It starts the standard-library server on `0.0.0.0:$PORT`, uses `/api/dashboard` as its health check, and deploys from Git. The dashboard is read-only and uses static, versioned files checked into the application repository; it does not depend on ephemeral local writes, data ingestion, or forecast retraining at startup or per request.

Render currently documents free Web Services for Python apps and Git-provider-based deploys. Its Free services sleep after 15 minutes without inbound traffic and can take about a minute to wake. Free service filesystems are ephemeral, so only checked-in application/evidence files are relied on. Free web service usage is limited to 750 instance hours per workspace per month, shared with other free web services; running out suspends the services until the next month. If outbound bandwidth/build usage is exhausted and no payment method has been added, Render documents suspension rather than billing for overage. Free instances are explicitly intended for hobby/testing use, not production. Review the current [free-instance limitations](https://render.com/docs/free), [Web Service setup and port binding](https://render.com/docs/web-services), and [Blueprint setup](https://render.com/docs/infrastructure-as-code) before publishing. Render's free-service documentation describes operation without an attached payment method for overage handling; if account creation or verification asks for a credit card, stop rather than enter one.

#### Git-based setup

1. Push this repository to a GitHub account/repository you control. Before publishing, verify permission to redistribute the PAQI CC BY 4.0 dataset and provide the attribution shown on the dashboard. The project software code has no declared code licence; choose and add an appropriate code licence before inviting reuse.
2. In Render, sign up/connect the Git provider, choose **New → Blueprint**, select the repository and branch containing `render.yaml`, review the single `hackinsight-air-quality-pakistan` Web Service and its `Free` plan, then deploy the Blueprint. No Docker installation is needed locally.
3. If Render prompts for a payment method or a paid plan, do not proceed. If the requested service name is unavailable, edit the `name` field in `render.yaml` to an unused name before deploying.
4. Once the deploy is healthy, verify the assigned public `onrender.com` URL, the dashboard page, `/api/dashboard`, and `/api/ask`. No public deployment is claimed until these checks are performed.

The generated warehouse and report directories are ignored by default. `.gitignore` selectively allows only the dashboard's required gold table, quality report, execution status, forecast metrics, and forecast predictions to be committed. The raw file, acquisition manifest, append-only quality history, rejected records, and fitted model are not required by the deployed dashboard and remain ignored.
