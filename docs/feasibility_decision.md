# Feasibility decision — HackInsight '26 air quality project

**Decision: CONDITIONAL GO — source verification sprint only.**  
**Research checked:** 2026-10-20

## Rationale

The project is not currently ready for full ingestion, ML, or two-source claims. One official World Bank product and an OpenAQ Pakistan country-registry entry were verified, but:

- The World Bank WDI product is annual, national and population-weighted, not daily city-level; upstream reuse terms for its IHME data are unresolved.
- OpenAQ requires an API key, and its Pakistan city/site, PM2.5, dates, volume, original providers and source-level licences have not been inspected.
- The Punjab AQI portal page does not establish a reusable raw historical dataset.
- The independence of any compatible Pakistan source pair is unverified.
- A valid held-out ML test set cannot be justified from the evidence currently available.

This is a **conditional** rather than unconditional GO because OpenAQ officially lists Pakistan and may provide usable licensed observations after authenticated inspection. No assumption is made that it will meet the gates. Under the current evidence, the full two-source and independently evaluated ML project is **not yet a GO**.

## Stop/go gates

Proceed beyond research only when all the following are documented:

1. **Source one:** an authenticated, bounded inspection confirms Pakistan PM2.5 sensor(s), actual city/site, original provider/owner, usable time span, units, coverage and non-fabricated records.
2. **Legal use:** the source-level licence and applicable terms allow the intended processing, publication, attribution and dashboard/repository use.
3. **Independent source:** a second credible original source has compatible Pakistan measurements and documented distinct provenance. Check actual provider/station/time/location overlap; if lineage cannot be resolved, record it as UNVERIFIED and do not claim independence.
4. **Held-out feasibility:** enough real, quality-usable, chronological observations exist to reserve a meaningful final test period and compare against a declared baseline. Establish sample thresholds before model fitting; do not use synthetic data or modelled estimates as substitute labels.
5. **Organizer rules:** confirm source eligibility, whether an outside-track source is required, declaration deadline/time zone, and PDF requirements.

If a gate is not met within the available 72-hour schedule, narrow or stop the affected claim rather than representing an unverified feature as complete.

## Fastest honest resolution path

1. Request/register an OpenAQ key through its official signup. Make only the small metadata/sample requests needed to identify Pakistan locations and sensors. Observe documented rate limits; do not commit the key.
2. For each candidate sensor, record the returned owner/provider, location, pollutant, units, sensor measurement dates, licence/attribution data and record IDs. Check one small permitted sample and a bounded coverage summary before any bulk download.
3. Contact the Punjab environmental authority or Pakistan EPA for the original station feed, source methodology, historical access, explicit licence/permission, and clarification of whether its records appear in OpenAQ.
4. Inspect the IHME GBD source record's current account and reuse terms if the World Bank series is to be redistributed; do not infer a dataset-specific licence from generic World Bank terms alone.
5. Compare source identifiers, providers, dates and coordinates. If source lineage is incomplete or records are duplicated, mark independence **UNVERIFIED** and ask organizers whether a single-source pilot is acceptable.
6. Ask the organizers now about track-source eligibility and deadline/PDF details, since a passed dataset-declaration deadline could invalidate the submission independently of technical feasibility.

## Requirement status at this audit

| Requirement | Status |
|---|---|
| Two independent, credible sources | **Not demonstrated; blocker** |
| Legal, attributable reuse | **Not demonstrated for a compatible pair; blocker** |
| Pakistan city-level PM2.5 coverage | **Not demonstrated** |
| Compatible real records for held-out evaluation | **Unknown; no full data or training performed** |
| Defensible target and baseline | **Provisional plan only; see [proposal](dataset_proposal.md)** |
| Dataset-declaration deadline / PDF | **Organizer confirmation required** |
| Full project feasibility within 72 hours | **Conditional; depends on source and organizer gates** |

## Prompt 1.5 addendum — alternative-track comparison

**Checked:** 2026-10-20. The original Air Quality findings above are preserved. This addendum records additional bounded climate and food-price research; it does not revoke the original source audit or authorize implementation.

### Recommended track to verify first: Food Price / Food Security

Food prices are the strongest current candidate, but **not yet approved for implementation**. HDX metadata for “Pakistan - Food Prices” names the WFP Price Database as its source, assigns a CC BY-IGO licence identifier, and lists a 1,637,040-byte Pakistan CSV. Two bounded HTTP Range samples (not a full download) showed Pakistan retail market prices: first-sample records dated 2004-01-15 and tail-sample records dated 2026-08-15. PBS's official price-statistics page separately documents monthly collection from 68 urban markets in 35 cities and 27 rural centers, and links to published price-statistics files.

The potential WFP/PBS pair is **not verified as independent**. The WFP extract's exact underlying Pakistan market-price providers are not identified in the inspected metadata/sample, and may include PBS prices. PBS reuse terms for a machine-readable historic market/item series were not established. The HDX licence metadata should also be confirmed as applying to the original WFP data before redistributing raw or derived extracts.

### Other tracks

- **Climate / Heat Intelligence:** A bounded NASA POWER sample returned daily satellite-derived surface shortwave irradiance at the same Karachi coordinates as a bounded NOAA NCEI station sample returning daily temperature/precipitation fields. NASA documents solar satellite lineage; NOAA documents a merged GHCN-Daily source lineage. This is a promising distinct measurement-method pair for a station-specific heat/weather pilot, but exact ancillary/source overlap, NOAA international-record reuse terms, NASA product reuse terms and station continuity remain unresolved. Do not call the sources independent ground-truth replications.
- **Air Quality:** No OpenAQ key/token is configured in the inspected environment; values were not read. Authenticated Pakistan metadata and samples therefore remain unavailable. Existing World Bank/AQI limitations and source-independence blocker are unchanged.

The evidence, per-category scores, provisional task outlines, and official source links are in [track_comparison.md](track_comparison.md). Scores are feasibility judgments, not model results.

### Current decision

**CONDITIONAL GO for research only; Food Price is the recommended first verification target. No track currently meets the full minimum evidence bar.** No data/model implementation should start until the team establishes an eligible, reusable and independent source pair with sufficient matching historical observations and confirms the organizer's source/declaration rules.

### Exact evidence required before implementation

1. **WFP source terms/provenance:** Written or official documentation from WFP/HDX confirming the applicable CC BY-IGO terms for the selected Pakistan rows, source owners/providers, price-collection method, update meaning, and whether PBS is an upstream contributor.
2. **PBS data and terms:** A public or authorized historical item/market-level price file with explicit terms permitting intended processing/public display; its methodology, frequency, units, market/item identifiers, and source lineage must be documented.
3. **Independent compatible observations:** Match provider IDs, item, market, dates, unit, price type and currency between WFP and PBS. Demonstrate the selected sources are not republications of the same upstream records; if not established, mark independence UNVERIFIED and do not claim compliance.
4. **Evaluation sufficiency:** After permission, count actual usable rows and temporal gaps for a fixed market/commodity series; freeze target, baseline, chronological train/validation/test periods, and minimum test sample before any model selection.
5. **Organizer decision:** Obtain the approved track-source list, the meaning of the two-source/outside-track requirement, declaration deadline/time zone, and Dataset_Proposal.pdf requirements.

### Single next action for the team

**Contact PBS's responsible price-statistics/data owner and request the historical market/item-level price extract, explicit reuse licence, source/collection methodology, and a direct answer on whether PBS records feed the WFP Price Database.** This is the highest-value verification because it can resolve the food track's independent-source and legal-use blockers together. Until that evidence is returned and organizer rules are confirmed, remain in research-only status.

## Prompt 1.6 addendum — Air Quality is the finalized project

**Checked:** 2026-10-20. This current decision supersedes the Prompt 1.5 alternative-track recommendation above: the team has finalized Air Quality Intelligence for Pakistan. The earlier food/climate comparison is retained as historical research, not a current recommendation. No dataset ingestion, model training, dependency installation, application build, or PDF generation was performed for this audit.

### Current decision: CONDITIONAL GO — research gates remain

Proceed with Air Quality as the project direction, with the PAQI Karachi daily series as the primary candidate. Do **not** begin full ingestion or claim two-source compliance until the evidence gates below are resolved.

| Requirement | Current evidence/status |
|---|---|
| Strongest primary dataset | PAQI Karachi daily PM2.5, Zenodo DOI `10.5281/zenodo.15845428`. Publisher, declared date/value schema, µg/m³ units, stated 24-hour network-average description, file size and CC BY 4.0 are verified from the repository/Zenodo evidence. |
| Exact data quality | Not verified. Exact rows, unique dates, duplicates, missingness and valid split sizes cannot be established from the DOI metadata and bounded samples; perform a later authorized full-file validation or obtain a publisher-verified summary. |
| Methodology / representativeness | Not verified. Sensor count/IDs, site panel, network aggregation, time convention, QA/calibration and missing-day rule are undocumented in inspected material. Avoid single-sensor or citywide exposure claims. |
| Independent second source | None verified. Pakistan EPA's official Islamabad monthly reports are the strongest candidate; daily PM2.5 tables were visually confirmed, but reuse licence, station/instrument provenance and relationship to PAQI/OpenAQ remain unknown. Islamabad is not a co-located Karachi series. |
| OpenAQ | Not verified for Pakistan records or PAQI overlap; an API key was unavailable and an unauthenticated request returned 401. Do not count PAQI-origin OpenAQ observations as independent. |
| Held-out ML feasibility | Unknown. A daily forecast is a candidate task, but no row count or usable sample size is established; chronology and data quality must be checked before deciding whether a held-out evaluation is meaningful. No model or metric exists. |
| PAQI licensing | CC BY 4.0 verified. Credit listed creators and PAQI, identify title/source, link the DOI/licence and note changes; do not imply endorsement. |
| Pak-EPA licensing | Unverified. Publicly accessible PDF reports do not establish republication/training permission. |
| Organizer rules | Unresolved: same-target requirement for second source, different-city eligibility, approved source list, dataset declaration deadline/time zone/late policy, and Dataset_Proposal.pdf requirements. |

### Evidence required before implementation

1. **PAQI methodology:** written publisher documentation identifying sensor/site provenance, number of contributing monitors, aggregation rule, daily averaging/timezone convention, QA/calibration and missing-day policy.
2. **PAQI data quality:** in the implementation phase only, fetch a pinned DOI version/commit and verify its checksum, then validate exact record count, date bounds, duplicate dates, missing dates, null/invalid values and year-by-year usable coverage. Bounded ranges and GitHub commit diff statistics are not substitutes for this full-file quality pass.
3. **Independent, reusable second source:** Pak-EPA (or another original publisher) must provide an explicit reuse licence/permission and documentation for station/operator, measurement and source lineage. Verify it is not a PAQI/OpenAQ republication. If the organizer requires two compatible target datasets, a different-city Islamabad series may not qualify; do not assume it does.
4. **OpenAQ provenance, if considered:** obtain API access through the official process, inspect location/provider/owner/sensor, dates and applicable licence, and compare records to PAQI. Do not expose or commit credentials.
5. **Organizer confirmation:** ask whether two sources need the same pollutant/target and compatible geography, whether Pak-EPA Islamabad data qualify, source-list/outside-track rules, the declaration deadline/time zone and late policy, and proposal PDF format.
6. **Evaluation:** only after quality validation, predeclare chronological train/validation/test dates; compare a next-day PAQI-series forecast to persistence on identical test dates, reporting MAE/RMSE, uncertainty coverage/width and group errors. Never imply a baseline win before actual held-out results.

### Compliance and scope

PAQI's CC BY 4.0 permission supports use with attribution and change indication, subject to the licence and dataset's stated provenance limitations. For Pak-EPA, do not redistribute extracted measurements until reuse permission is established. Follow each provider's access controls and rate limits. Do not substitute weather data as an independent air-quality source. The final Dataset_Proposal.pdf must wait until organizer requirements and source evidence are settled.

### Single next action

**Send one written request to the Pakistan EPA owner of the Ambient Air Quality Reports asking for (a) explicit reuse permission/licence for the daily Islamabad PM2.5 tables, (b) station/operator and instrument/QA/aggregation provenance, and (c) confirmation whether the records are sourced from PAQI or OpenAQ.** This is the highest-value source action because one reply can resolve the second-source legal and independence blockers. Separately, the team must obtain organizer clarification before relying on cross-city data for formal compliance.

## Prompt 1.7 addendum — bounded verification and minimum scope

**Checked:** 2026-10-20. This addendum supersedes earlier row-count estimates and the Prompt 1.6 proposed next action; it does not authorize ingestion or claim compliance.

### Current evidence and decision

- **PAQI:** Version DOI `10.5281/zenodo.15845428` is pinned; the Zenodo metadata identifies the 51,387-byte daily CSV and MD5 `b3fe95e0550702ed7562687ea2e8a219`, CC BY 4.0 and creators. Bounded edge samples and the README support the declared daily PM2.5 schema, µg/m³ units and publisher-described 24-hour network average. Exact row count, usable date range, duplicate/missing dates and null/invalid values cannot be established from metadata or bounded samples. No GitHub diff line count is used as a row-count estimate.
- **Attribution:** Credit listed creators Omar Abid, Dawar Hameed Butt and Mahad Naveed; identify PAQI/title/source, link DOI and CC BY 4.0, identify changes and do not imply endorsement. The inspected GitHub commit is `164cdeff238db112137d593cfe9ffd0952346989`.
- **Pakistan EPA:** Daily Islamabad PM2.5 report tables are verified in official PDFs. The official homepage lists `webmaster@environment.gov.pk` and `051-9250715`; this is generic website contact information, not a confirmed monitoring-data owner's contact. No explicit reuse licence, named station/operator/instrument, QA/aggregation methodology, or PAQI/OpenAQ overlap confirmation was found.
- **Forecast suitability:** Islamabad reports are not appropriate target labels or direct held-out validation for a Karachi-only next-day forecast. If permission and independence are confirmed, they can support contextual comparison or an explicitly out-of-city analysis only; that is not Karachi forecast validation.
- **OpenAQ:** Documentation describes provider/owner/sensor/licence metadata and requires an API key. No key was available; the earlier unauthenticated request returned HTTP 401. No Pakistan-specific metadata or PAQI overlap is verified.
- **Verdict:** **CONDITIONAL GO** for a PAQI-series pilot only. Two-source compliance remains unverified. Forecasting feasibility remains unproven until the real file's chronology and quality are checked. No model result is available.

### Minimum four-person scope

Keep one target: next-day forecast of the published PAQI Karachi daily series, compared against persistence with frozen chronological validation/test dates after data-quality validation. Avoid describing the target as a single sensor or citywide exposure until PAQI clarifies aggregation. Split team work across source/provenance, data-quality pipeline, held-out evaluation, and evidence-grounded dashboard/insights. EPA values should be omitted unless written reuse permission and organizer acceptance are obtained; if omitted, disclose the unresolved two-source criterion rather than treating it as satisfied.

### Draft organizer message — not sent

> Our finalized project is Air Quality Intelligence for Pakistan, with PAQI's Karachi daily PM2.5 series as the proposed forecast target. Must both independent sources provide PM2.5 target labels, or may an independent meteorological source count as a feature source? Does a source covering another Pakistani city, such as Islamabad, qualify? May government-report data without an explicit open licence be used for analysis, and is written permission required? Please confirm the dataset proposal/declaration deadline, timezone, late-submission rule, and required Dataset_Proposal.pdf format/template.

The Pak-EPA permission/provenance email draft and general contact evidence are in [dataset_research.md](dataset_research.md). No email or organizer message has been sent.

### Single next action

**Send the organizer clarification message above now** to confirm source eligibility and the submission deadline/format before relying on the cross-city EPA candidate or spending the remaining time on an ineligible data plan.

## Phase 2 addendum — PAQI acquisition and warehouse result

**Checked:** 2026-10-20. Air Quality remains the project. This phase acquired only the CC BY 4.0 PAQI version; EPA and OpenAQ remain excluded pending their reuse/provenance gates. No model development was started.

### Implemented pipeline

Added a root `Makefile` (`data` and `test` targets), Python standard-library pipeline, pinned `config/sources.json`, `.env.example`, `.gitignore`, tests, and root `README.md`. Local generated outputs live under `data/raw/`, `cleaned/`, `processed/`, `manifests/`, `quality/`, and `reports/`; these data paths are Git-ignored. The raw CSV is immutable in place and accompanied by provenance; each execution appends a manifest event.

The pipeline fetches Zenodo's pinned metadata each time, validates record/version/licence/file name/size/MD5, reuses a cached file only after rechecking source checksums and its provenance sidecar, computes SHA-256, parses date-only values without inventing timezone, preserves µg/m³ without conversion, records stable row IDs and source-file lineage, flags blank measurements in cleaned/gold, and saves rejection/quality/execution reports. It performs no imputation, duplicate resolution, aggregation, cross-source join, or feature construction.

### Actual acquisition and validation

- Pinned source: Zenodo version DOI `10.5281/zenodo.15845428`; metadata HTTP 200; CC BY 4.0; CSV size 51,387 bytes; MD5 `b3fe95e0550702ed7562687ea2e8a219`; SHA-256 `2359a11850df9d5798c446e1013c09f22914426ffc1e1d928c2ec9824502debf`.
- First acquired at `2026-10-19T21:39:21Z`. Subsequent runs revalidated metadata and reused the cache (`reused_cached_file`); the latest verified run was `2026-10-19T21:44:02Z`. The append-only manifest contains the original download plus three cache-reuse events.
- Full CSV: 3,009 source rows, 3,009 unique consecutive date-only records, 2016-10-06 through 2024-12-31; 3,003 numeric PM2.5 values and 6 blank measurements; 0 malformed rows, invalid dates, non-finite/negative values, duplicate dates, or missing calendar dates. The six blanks remain in cleaned/gold with `missing_pm25_value`; there was no imputation or silent row drop.
- Pipeline quality status: `passed_with_warnings`; warnings cover six blank measurements, absent station ID, unspecified timezone/aggregation, and staleness. The latest observation (2024-12-31) was 657 days old on the pipeline's UTC run date (2026-10-19). This is a historical static dataset, not fresh/hourly observations.
- Final run outputs: 3,009 rows in cleaned and gold; row IDs are unique and linked to source record ordinals and source SHA-256. No EPA/OpenAQ observations are in the warehouse; cross-source independence check is `not_run`.

### Commands and failures actually observed

- `python -m unittest discover -s tests -v` — **11 tests passed**. Synthetic data exist only in small software-test fixtures, not pipeline outputs or model inputs.
- `python -m py_compile pipeline\run.py tests\test_pipeline.py` — passed.
- `python -m pipeline.run` — first attempt exited 1 when blank PM2.5 cells were initially treated as critical invalid values. The transformation was corrected to retain and flag those dated rows. The final verification at `2026-10-19T21:44:02Z` returned exit code 0 with `success_with_warnings` using verified cached bytes.
- `make data` — could not execute because GNU Make is not installed on this Windows host (`make` not recognized). Its standard Makefile target is defined; the equivalent Python entry point above was exercised. No packages were installed.

The pipeline command succeeding does not clear the source-independence requirement or establish that the series is a single stable monitor/network. No model was trained, no forecast score exists, and EPA/OpenAQ remain unverified for reuse and independent provenance.
