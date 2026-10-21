> **Superseded on 2026-10-21:** the warehouse now has three sources (PAQI, U.S. Consulate Karachi via OpenAQ/AirNow, Urban Unit AirGradient via OpenAQ) and two-source compliance is established in `data/quality/warehouse_quality_report.json`. This file is kept as the decision history; see `README.md` for the current state.

# Dataset proposal — HackInsight '26 Air Quality Intelligence for Pakistan

**Status:** Phase 2 pipeline operational for PAQI; two-source, aggregation-method, and forecasting-evaluation gates remain open.  
**Research checked:** 2026-10-20

## Proposed question

Can the next-day PM2.5 value in PAQI's published Karachi daily series be forecast using only information available before prediction time, and does a candidate model beat a persistence baseline on a chronological held-out period?

This is a conditional forecasting question, not a claim that the data are fully quality-checked or that any model/performance result exists. PAQI describes its values as daily 24-hour averages from its monitoring network, but the exact sensor count, site coverage, aggregation method, and missing-day handling are not documented in the inspected README. Until PAQI clarifies this, the target is the published PAQI Karachi series—not a single monitor or a validated citywide exposure estimate.

## Proposed sources and evidence status

| Source | Intended role | Verified facts and open limitations |
|---|---|---|
| [PAQI Karachi dataset, Zenodo version DOI 10.5281/zenodo.15845428](https://doi.org/10.5281/zenodo.15845428) | Primary forecasting target | Full pinned CSV was acquired and parsed: 3,009 rows and 3,009 consecutive distinct dates from 2016-10-06 through 2024-12-31. Six rows have blank PM2.5 values; they remain flagged in cleaned/gold. No duplicate dates, missing calendar dates, malformed rows, invalid dates, negative values or non-finite values were found. Raw size 51,387 bytes; MD5 `b3fe95e0550702ed7562687ea2e8a219`; SHA-256 `2359a11850df9d5798c446e1013c09f22914426ffc1e1d928c2ec9824502debf`. |
| [Pakistan EPA Ambient Air Quality Reports](https://environment.gov.pk/Detail/ZjU5NDM3YjItNTdiOS00NTk5LWExYzUtMjI2NzE5YjdlOGM5), Islamabad monthly reports | Candidate independent context, not Karachi target labels | Official example PDFs show daily PM₂.₅ µg/m³ and AQI alongside SO₂, CO and NO₂ in Islamabad. Distinct publisher/city suggests a candidate source, but station/instrument lineage, relationship to PAQI/OpenAQ, QA and reuse permission remain unverified. It cannot validate Karachi next-day forecast errors because it is not co-located or matched to the Karachi target. |
| [OpenAQ v3](https://docs.openaq.org/) | Provenance/overlap investigation only | API key is required. No key was configured; the unauthenticated Pakistan location request returned HTTP 401. Provider/owner/sensor/licence metadata and PAQI overlap were not inspected. PAQI-origin records republished by OpenAQ do not count as independent evidence. |
| World Bank WDI PM2.5 indicator | Optional national annual context only | Previously verified as annual population-weighted national exposure sourced from IHME GBD 2023. It is not a daily city observation or compatible independent target; upstream reuse terms need resolution. |

**Independence status:** PAQI is the verified primary candidate. Pakistan EPA Islamabad is the strongest independent-source candidate located, but no genuinely independent second source is verified yet. Distinct publisher and city are not proof of independent sensor/source lineage. GitHub and Zenodo are two distribution routes for the same PAQI data, not two sources.

## PAQI file identity and quality questions

- At the inspected GitHub main-branch commit `164cdeff238db112137d593cfe9ffd0952346989`, the daily file is `PAQI_Daily_PM2.5_Data_2016-2024_in_Karachi.csv`; Zenodo lists the same daily filename. The README uses a different descriptive filename. The pipeline pins the DOI version and verifies file checksums.
- Zenodo version record 15845428 reports 51,387 bytes and MD5 `b3fe95e0550702ed7562687ea2e8a219` for the daily CSV. The immutable version DOI is `10.5281/zenodo.15845428`; the inspected repository commit is `164cdeff238db112137d593cfe9ffd0952346989`. CC BY 4.0 attribution should credit the listed creators (Omar Abid, Dawar Hameed Butt, Mahad Naveed), the title/source and PAQI; link the licence, identify changes, and do not imply endorsement.
- The dataset has no station/sensor ID, QA flag, or timezone/averaging-window field in its declared schema.
- The full-file pipeline found exactly 3,009 rows with unique consecutive dates from 2016-10-06 to 2024-12-31. Six dates (2023-12-13 through 2023-12-16, 2023-12-27 and 2023-12-28) have blank PM2.5 values. These rows remain in cleaned/gold with a quality flag and blank numeric value; no imputation was done. Other checked records had valid ISO dates and finite nonnegative PM2.5 values.
- PAQI's README says “complete daily 24-hour average” values from a “monitoring network” but does not establish whether each row is one sensor, a fixed network average, a selected monitor, or another aggregate. Ask PAQI for the original sensors/sites, aggregation method, calibration/QA and completeness rule.

## Conditional ML protocol (not run)

- **Target and horizon:** next-day PM2.5 value in the published PAQI Karachi series. Define the forecast cutoff and day convention with PAQI; do not call it a sensor-specific or representative city exposure forecast without that provenance.
- **Baseline:** persistence—predict the next valid day from the most recent value available before forecast time. Compare any model on exactly the same forecast dates.
- **Candidate features:** lagged PAQI series values (e.g., previous day, 2 days, 7 days), rolling statistics computed strictly from past values, and calendar variables. Meteorology may be an optional predictor but does not satisfy the second-air-quality-source rule by itself.
- **Split:** chronological 70% train (2016-10-06–2022-07-12) / 15% validation (2022-07-13–2023-10-06) / 15% final test (2023-10-07–2024-12-31), based on the audited 3,009-date sequence. Freeze cutoffs before model selection; validation can guide model and interval choices, final test is used once. Never randomly split a temporal series or forward-fill target labels. The exact protocol and target counts are documented in [forecasting readiness](forecasting_readiness.md).
- **Sample size:** 3,009 dated rows are present, of which 3,003 have numeric PM2.5 values. This establishes only dataset volume, not that the series represents a single stable sensor/network or that model evaluation will be scientifically adequate. Any train/validation/test counts depend on the declared forecast protocol and must be computed from the cleaned chronology.
- **Metrics:** MAE primary, RMSE secondary; report identical test dates/counts and paired differences from persistence. Claim improvement only if actual held-out measurements demonstrate it.
- **Uncertainty/error analysis:** calibrate prediction intervals on validation residuals, then report test coverage and width; analyze by year/season/concentration band with sample counts. No result exists yet.
- **Leakage risks:** no same-day/future pollutant or weather inputs, full-series preprocessing, test-based selection, duplicate dates crossing splits, or modelled WDI estimate as PAQI ground truth.

### Smallest valid fallback within Air Quality

If PAQI cannot clarify data aggregation or the cleaned chronology is too sparse, keep the project within Air Quality: provide a source-attributed historical trend and standards comparison, and limit ML claims to a valid one-source chronological experiment. Treat Islamabad EPA reports as contextual evidence only, after reuse permission and organizer acceptance; do not use them as Karachi labels or paired forecast validation. If EPA reuse permission is unavailable, omit its measurements and disclose that the two-source requirement remains unmet unless organizers approve another compliant interpretation. Do not relabel an OpenAQ mirror as independent.

## Exact pre-implementation gates

1. Obtain PAQI clarification on sensor/network lineage, aggregation, averaging window/timezone, QA, calibration, and missing-day rules.
2. In the implementation phase, acquire the pinned DOI file under CC BY 4.0, verify its metadata checksum, then compute exact row count, unique-date count, duplicate dates, missing-date intervals, null/invalid values and annual coverage. Bounded ranges cannot establish these full-file properties.
3. Obtain Pak-EPA source/methodology details and explicit reuse permission for the published Islamabad PM2.5 values. Verify underlying monitor operator/site IDs and whether any PAQI/OpenAQ source is involved.
4. Inspect OpenAQ owner/provider/sensor/licence metadata if the team obtains a key through official signup; compare provenance and records against PAQI. Do not use OpenAQ to claim independence until its source chain is clear.
5. Ask organizers whether the second source must carry the same target variable and whether a different-city official PM2.5 report qualifies; confirm eligible-source list, deadline/time zone, late policy, and Dataset_Proposal.pdf requirements.
6. Only after the source and evaluation gates pass, freeze a test period and start training.

## Compliance and citation

The PAQI repository licence and DOI metadata state CC BY 4.0. Attribute the Pakistan Air Quality Initiative, link the DOI and licence, and indicate dataset modifications. Do not imply PAQI endorsement. The Pak-EPA report PDFs are publicly reachable, but no reuse licence was found in the inspected page/report; do not republish their tables until terms or permission are verified. Respect OpenAQ's API key and rate-limit requirements and each underlying provider's licence.

This Markdown is not the final `Dataset_Proposal.pdf`. Confirm the event's declaration deadline, required template, source list and independence rule with organizers before producing a final proposal PDF.

## Smallest defensible four-person scope

1. **Data/provenance:** pin the PAQI version, verify checksum, record attribution and document limitations.
2. **Quality/pipeline:** validate schema, rows, dates, missingness and duplicate handling with an auditable quality log; do not impute target labels silently.
3. **Evaluation:** run one predeclared next-day PAQI-series forecast against persistence using chronological validation/test periods; publish metrics only if the actual holdout supports them.
4. **Dashboard/insight:** show PAQI-only results and provenance; include EPA as contextual material only if written reuse terms and organizer acceptance are obtained. Otherwise mark the second-source criterion as unresolved, not completed.

No EPA measurements should enter the model or be republished while permission and provenance are unresolved. A city-to-city comparison, if later approved, is an out-of-city contextual/generalization analysis—not validation of Karachi's next-day forecast.

## Phase 2 pipeline outcome

The root `Makefile` and Python pipeline implement metadata validation, version-pinned acquisition/cache verification, immutable raw storage, SHA-256 and MD5, append-only `manifest.csv`, cleaned and gold CSVs with stable row IDs/lineage, rejected-record and missing-value issue logs, quality report, and execution status. The final `python -m pipeline.run` completed with exit code 0 and `success_with_warnings` using the cached raw artifact after revalidating Zenodo metadata and checksum. It emitted 3,009 gold rows; 3,003 carry numeric PM2.5 and six are flagged blank. Current observation freshness is stale (latest 2024-12-31; 657 days before UTC run date 2026-10-19). No model was trained.

`make data` is the documented root command, but GNU Make is not installed on the Windows host. The equivalent Python entry point was used for actual execution; the Make target itself was not run here. EPA/OpenAQ remain excluded and two-source compliance remains unresolved.
