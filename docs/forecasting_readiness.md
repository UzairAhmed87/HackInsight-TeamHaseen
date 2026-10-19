# Forecasting readiness — PAQI Karachi PM2.5

**Audit date:** 2026-10-20  
**Scope:** Data/methodology readiness and reproducible historical modeling gate. The Phase 5 model was fit on train dates and evaluated once on the frozen validation/test periods; detailed results are in [forecasting_results.md](forecasting_results.md).

## Final modeling gate

**GO for a narrowly scoped historical experiment predicting the next reported value in the published PAQI Karachi daily series.** The target is operationally identifiable in a pinned publisher dataset: one date and one stated daily 24-hour average PM2.5 value in µg/m³ per row. This is sufficient to test whether a model forecasts that *published series* on a chronological holdout, against persistence, without asserting what physical monitor or citywide exposure the value represents.

This GO is limited to that historical series-level question. It does **not** validate station-level or representative citywide air quality, prove that the measurement process was stable across the full period, establish present-day conditions, or clear the hackathon's two-source requirement. The unresolved collection/aggregation history could produce a measurement-definition break; disclose this as a material validity limitation, inspect performance over time, and do not interpret any forecast as environmental evidence beyond the reported series. If the team's research question requires a stable sensor or fixed network estimand, pause that interpretation pending PAQI clarification.

The dataset has 3,003 numeric daily targets over more than eight years, no absent dates in the published sequence, and six blank measurements. A historical chronological holdout is feasible by count, but meaningful predictive skill is not established until the specified backtest is run. There are no model metrics or measured baseline comparisons. The latest target date is 2024-12-31, so no current-air-quality forecast is supported.

Before fitting, freeze the target wording, split dates, persistence rules, metrics and leakage controls below. Train/evaluate only on the existing real PAQI observations. The PAQI methodology inquiry in [paqi_methodology_inquiry.md](paqi_methodology_inquiry.md) is recommended, but a reply is not a prerequisite for the narrow series-prediction experiment; it is required before making station/network, representativeness, or stable-measurement claims.

Do not claim a baseline win, current-air-quality forecast, representative Karachi exposure estimate, or two-source compliance.

## Evidence and independently verified data statistics

The audit reads the locally checksum-verified raw CSV and checks cleaned/gold row counts, order, values, lineage fields, source-file SHA-256, and recomputed gold row IDs. It is reproducible with `python -m pipeline.readiness` after `python -m pipeline.run`.

| Property | Verified result |
|---|---:|
| Source/version | PAQI, Zenodo version DOI [10.5281/zenodo.15845428](https://doi.org/10.5281/zenodo.15845428), CC BY 4.0 |
| Raw file | 51,387 bytes; MD5 `b3fe95e0550702ed7562687ea2e8a219`; SHA-256 `2359a11850df9d5798c446e1013c09f22914426ffc1e1d928c2ec9824502debf` |
| Source rows | 3,009 |
| Distinct dates / observed bounds | 3,009 consecutive date-only dates; 2016-10-06 through 2024-12-31 |
| Numeric PM2.5 values | 3,003 |
| Blank PM2.5 values | 6; 0.20% of source rows |
| Negative / non-finite numeric values | 0 / 0 |
| Duplicate dates / absent dates within observed bounds | 0 / 0 |
| Minimum / maximum | 1.3 / 242.1 µg/m³ |
| Median | 35.8 µg/m³ |
| Mean | 48.157742 µg/m³ |
| Standard deviation | 33.392841 µg/m³ sample; 33.387280 µg/m³ population |

The six blank measurements occur on 2023-12-13, 2023-12-14, 2023-12-15, 2023-12-16, 2023-12-27 and 2023-12-28. They remain in cleaned and gold tables with blank normalized values and `missing_pm25_value` flags. No target values were imputed.

### Repetition and range checks

The 3,003 numeric readings contain 1,020 distinct magnitudes. Of those magnitudes, 622 occur more than once; 2,605 rows (86.75%) have a magnitude that appears elsewhere, and the most frequent magnitude occurs 15 times. All readings are represented to one decimal place; the longest run of consecutive, identical daily values is two days, and there are no exact zero readings.

Repeated magnitudes are not, by themselves, evidence of frozen sensors or fabricated observations: one-decimal reporting naturally causes repeats. The observed precision and repetition warrant asking PAQI about instrument/reporting precision, but the available data do not establish an anomaly. The maximum is reported descriptively, not judged against an unverified instrument or regulatory validity threshold.

## Raw, cleaned, gold, and lineage verification

For every ordered record, the raw source date and exact source value string match cleaned and gold. The six blank source values remain blank in both outputs. Numeric normalized values parse back to the exact raw numeric magnitude, with units retained as µg/m³ and no conversion. Cleaned/gold semantic lineage fields match; source-record ordinals and file SHA-256 match the raw artifact; all gold `row_id` values recompute as SHA-256 of source ID, pinned version and source-record key. All 3,009 gold IDs are unique.

The source schema has no record ID or station ID. Stable `source_record_key` values therefore identify CSV data-row ordinals, not publisher-issued observation identifiers. The source does not contain station coordinates; `Karachi` is the publisher's dataset label. These are data lineage keys, not claims of station identity.

## PAQI methodology evidence and status

Status terms apply to the specific claim: **verified** means explicit publisher material or the inspected file supports it; **partially documented** means publisher material supports a limited statement but leaves important detail unspecified; **unknown** means no supporting methodology detail was found. These statements describe what is documented, not independent validation of PAQI's measurement process.

| Question | Status | Direct evidence and boundary |
|---|---|---|
| Who published/collected the series? | **Partially documented** | Zenodo's [version API record](https://zenodo.org/api/records/15845428) lists Omar Abid, Dawar Hameed Butt, and Mahad Naveed as creators, title *Unveiling Karachi's Air: A Scientific Foundation for a Clean Air City*, publication date 2025-06-03, and `cc-by-4.0`. The [README at pinned repository commit `164cdeff238db112137d593cfe9ffd0952346989`](https://github.com/PakAirQuality/Unveiling-Karachi-Air/blob/164cdeff238db112137d593cfe9ffd0952346989/README.md) says the dataset accompanies a report published by PAQI and describes “on-the-ground monitoring.” The report says “Measurements from the PAQI air quality monitoring network…” (PDF p. 16; printed p. 3). This establishes PAQI's stated publication/network attribution, but not the legal owner/operator of each monitor or who collected each daily record. |
| One monitor, several monitors, or network aggregate? | **Partially documented** | README file description: “Contains the complete daily 24-hour average PM2.5 concentrations from the PAQI monitoring network.” The report's “Measurements from the PAQI air quality monitoring network…” (PDF p. 16; printed p. 3) is consistent with a network origin. Neither source specifies monitor count or whether a daily value is a single selected monitor, average across monitors, or another network statistic. “Network” must not be rephrased as a verified multi-monitor average. |
| Station identities / changing contributors? | **Unknown** | The declared daily CSV schema has only `date` and `pm25_concentration_ug_per_m3`; it has no station ID, coordinates, instrument ID, or per-day source field. No station list or date-by-date contributor history is given in the inspected README, Zenodo metadata, or extracted report text. Whether sites/contributors changed during 2016–2024 is unknown. |
| Daily averaging window and timezone | **Partially documented** | The README calls the measure a “daily 24-hour average” and defines the concentration unit as µg/m³. The report refers to Sindh's “legal 24-hour limit” (PDF p. 16; printed p. 3), but does not specify the measurement window. The CSV contains date-only strings. Start/end hours, local-time convention, timezone and aggregation/completeness formula are unknown. A standards comparison does not itself establish the sampling window. |
| Calibration and QA | **Unknown** | No calibration, collocation, validation, maintenance, instrument accuracy, QA threshold, or quality-flag method was found in the inspected sources. The report PDF text inspection was partial, so absence here means “not established in the material inspected,” not proof that PAQI has no such procedures. |
| Blank values and missing observations | **Partially documented** | The CSV itself contains six blank PM2.5 cells on dated rows; the pipeline retained them as missing and did not impute them. The README's word “complete” is not a missing-data rule and conflicts with interpreting every date as a numeric observation. No source explanation was found for blanks, outages, invalid days, exclusion criteria, or whether blank dates were aggregated differently. |
| Method changes during 2016–2024 | **Unknown** | The pinned README describes the file as covering 2016–2024 and the report labels daily analysis over 2017–2024 (Exhibit 1, PDF p. 7), but neither gives versioned station/instrument/aggregation history or states that methods were unchanged. The report's statement that 2024 had “only three days in the entire year” meeting its stated WHO safety criterion (PDF p. 7) is not evidence of method stability. |
| Version, schema, licence | **Verified** | [Zenodo version 10.5281/zenodo.15845428](https://doi.org/10.5281/zenodo.15845428) lists the daily CSV as 51,387 bytes with MD5 `b3fe95e0550702ed7562687ea2e8a219`, and licence ID `cc-by-4.0`. The pinned README gives the two-column schema and µg/m³ unit. Attribution remains required under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). |

**Publisher report inspection note:** The versioned Zenodo record links [*Unveiling Karachi's Air: A Scientific Foundation for a Clean Air City*](https://zenodo.org/api/records/15845428/files/Unveiling-Karachi-Air_PAQI.pdf/content). Text was extractable only in part. Relevant direct excerpts above are located at PDF p. 16 (printed p. 3) and p. 7; no conclusion about the uninspected portions is made. The README's filename aliases differ from the actual Zenodo daily filename, so use the pinned Zenodo filename/version and checksum for reproducibility.

The PAQI repository and Zenodo DOI are publication routes for the same dataset, not independent sources. The project currently has no verified independent second air-quality source. The organizer clarification recorded in the research documents must determine whether two sources must both supply target PM2.5 labels, whether a different-city source can qualify, and whether a meteorological source can count. Until then, keep the PAQI-only experiment distinct from a claim of full two-source compliance. The best compliant path is to secure an original independent Pakistani air-quality dataset with explicit reuse terms and provenance, then establish whether it is relevant to the required source count; Islamabad EPA reports remain contextual/out-of-city only unless organizers accept that role and permission/provenance are resolved.

## Frozen chronological holdout and Phase 5 evaluation

Partition the 3,009 calendar rows in strict chronological order, using floor(70%) for training, floor(15%) for validation, and the remainder for final test. Dates are fixed from the audited sequence; do not shuffle:

| Partition | Dates, inclusive | Calendar rows | Numeric target labels |
|---|---|---:|---:|
| Train | 2016-10-06 – 2022-07-12 | 2,106 | 2,106 |
| Validation | 2022-07-13 – 2023-10-06 | 451 | 451 |
| Test | 2023-10-07 – 2024-12-31 | 452 | 446 |

The test has six blank target labels; those are excluded from numeric scoring, never filled. These boundaries were frozen before model fitting and test evaluation. The first model's measured results and sample counts are documented in [forecasting_results.md](forecasting_results.md).

## Persistence baseline and missing-data rules

For target date *t*, forecast the latest finite, nonnegative PM2.5 reading whose observation date is strictly earlier than *t*. Use only data available at the forecast cutoff. Store the predictor's observation date and age in days for every scored pair.

- If the target value for *t* is blank, retain its row and flag it, but do not score or impute that target.
- If no prior valid PM2.5 value exists (the series' first date), no persistence forecast is available and the target is not part of baseline scoring.
- If the immediately preceding date's value is blank, use the latest earlier valid reading as the requested persistence rule specifies, record its age, and report it as a stale-predictor case. Never substitute the missing target or use a future reading.
- In the proposed test partition, all 446 numeric targets have an earlier valid observation; 444 have a valid immediately preceding-day value. Two persistence predictors are stale: target 2023-12-17 uses the valid 2023-12-12 reading (5-day-old input), and target 2023-12-29 uses the valid 2023-12-26 reading (3-day-old input). Report those cases separately and optionally provide a strict previous-calendar-day sensitivity result; do not silently change the primary baseline.
- For any candidate model, leave blank target labels out of fitting/scoring. Do not forward-fill targets. A feature may use trailing historical readings only; record missing lag values/ages rather than using future information.

## Metrics and leakage controls

MAE is the primary error metric and RMSE secondary. The Phase 5 experiment compares persistence and the candidate on identical test target dates, reports missing labels, stale-predictor cases, paired differences, and year groups with sample counts. It also reports validation-residual interval coverage descriptively; no statistical significance is claimed. See [forecasting_results.md](forecasting_results.md) for measured values and caveats.

Prevent leakage by:

1. Creating each feature for date *t* only from observations dated before *t*; rolling windows must be trailing and shifted so the target day's value is excluded.
2. Fitting imputation (if justified for predictors only), scaling, feature selection, and model parameters on training data only; use validation for selection/calibration.
3. Keeping the final test period untouched until one final evaluation. Do not use it to select features, thresholds, split dates, or models.
4. Using a walk-forward test simulation: after forecasting date *t*, a real observed PM2.5 value for *t* may enter the information set for a later forecast only after that observation would have become available. Never use the target before its simulated forecast.
5. Evaluating candidate and baseline on identical numeric target dates and publishing the lineage IDs for any aggregate insight.

## Historical backtest versus current forecast

The source endpoint is 2024-12-31, so the proposed test is a historical backtest ending then. At the audit date (2026-10-20 local; 2026-10-19 UTC), the latest observation is about 657 days old. The file does not support a current Karachi condition estimate, live next-day forecast, or hourly freshness statement. A current forecast would require newly acquired, legally reusable, independently attributable current observations, with a documented update schedule and validation.

## Supplementary-source and compliance status

- **Pakistan EPA Islamabad monthly reports:** official PDFs show daily PM2.5 tables, but reuse permission/licence, station/instrument provenance, QA and overlap with PAQI/OpenAQ remain unresolved. Islamabad is not Karachi and cannot be treated as labels for Karachi forecast errors. Do not download/extract or incorporate the values until permissions and organizer acceptance are established.
- **OpenAQ:** public documentation exposes provider/owner/sensor/licence metadata, but an API key is required and no key was available. Pakistan location records, source-level terms and overlap with PAQI have not been verified. A PAQI mirror on OpenAQ would not be independent.
- **World Bank WDI PM2.5:** previously verified as an annual national modelled exposure indicator with IHME GBD provenance; incompatible with daily Karachi labels and not independent validation.

No independent second source is currently approved or verified. Weather observations may be useful predictors only if legally cleared and available strictly before forecast time; they do not automatically satisfy an independent-air-quality-source requirement. Organizer confirmation remains necessary about whether both sources must supply PM2.5 labels, whether meteorology qualifies, and whether another-city reports count.

## Open questions and scope limits

The following methodology questions limit scientific interpretation and should be sent to PAQI using [the draft inquiry](paqi_methodology_inquiry.md); they do not block the narrow forecast of the published series itself:

1. What monitoring stations, instruments, coordinates and number of sensors contributed to each date, and did the contributing panel change?
2. Is each value one monitor, a fixed-panel average, or another network statistic? What are the inclusion/completeness rules?
3. What local timezone and exact averaging window define a date? What QA, calibration, validation and maintenance procedures were applied, and were these consistent over the series?
4. What do the six blank cells mean, and are there other quality flags or excluded observations not represented in this CSV?

Separate project-compliance questions remain unresolved:

5. Does the organizer accept a clearly labeled single-source PAQI-series historical forecasting pilot if no independent second air-quality source is verified? Do meteorology or different-city EPA reports satisfy any source-count rule?
6. May EPA's public report data be used for analysis or republication without an explicit open licence, or is written permission required?

These unresolved items prohibit claims of station/network representativeness, method stability, or two-source compliance. If organizer rules require two independent sources before model work, that requirement takes precedence over this scientific GO and the team must obtain approval or an eligible second source before proceeding.

## Reproducibility and test status

Run the read-only data audit and historical forecast:

```powershell
python -m pipeline.readiness
python -m pipeline.forecasting
```

Focused automated tests use only tiny software fixtures. After Phase 5, `python -m unittest discover -s tests -v` passed **19 tests**, including data lineage and forecasting lag, missingness, persistence-age, fitting, and metric checks. The experiment fit coefficients on 2,099 complete training examples and evaluated validation/test periods; it did not alter or reacquire the PAQI source data.
