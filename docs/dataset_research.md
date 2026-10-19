# HackInsight '26 — Air-quality dataset feasibility and source audit

**Research checked:** 2026-10-20  
**Phase 1 scope:** Source feasibility and official-document review only. During the initial PAQI inspection, an un-ranged request to the public Zenodo daily-file endpoint was inadvertently made; the tool displayed only a truncated portion and no local copy was saved then. Phase 2 later intentionally acquired the pinned PAQI file under the verified CC BY 4.0 licence and performed a complete quality pass; see the dated addendum below. No model was trained.

## Executive finding

The evidence reviewed establishes a credible primary candidate but does **not** establish two independent, reusable sources of compatible Pakistan city-level PM2.5 observations.

- PAQI's Karachi daily PM2.5 series is the strongest verified primary dataset candidate. Its Zenodo record/repository provide CC BY 4.0 metadata, declared date/value schema and stated daily 24-hour network averages. Exact row quality, daily completeness, sensor lineage, and aggregation remain unresolved.
- Pakistan EPA's official Islamabad monthly reports are the strongest second-source candidate found: example PDFs show daily PM2.5 tables. Reuse rights, monitoring provenance, independence from PAQI/OpenAQ, exact historical coverage and co-location remain unverified.
- The World Bank indicator verified here is a **national, population-weighted annual exposure estimate**, not a daily city measurement product. The World Bank API identifies its upstream source as IHME's Global Burden of Disease (GBD) 2023 estimates. Its granularity and modelled nature make it unsuitable as a daily city target or independent ground truth for another model.
- OpenAQ's official country registry includes Pakistan, and its documentation explains how to retrieve station and sensor data. However, a key is required; the unauthenticated Pakistan API request returned HTTP 401. No Pakistan station, city, PM2.5 sensor, date range, count, original provider, or applicable record-level licence was inspected.
- The reachable Punjab AQI portal advertises real-time AQI updates through an app. The reviewed page did not establish a downloadable historical measurement dataset, a documented API, pollutant-specific station records, methodology, or data-reuse licence.
- A genuinely independent second source is therefore **UNVERIFIED**. The World Bank and OpenAQ must not be counted as an independent pair based only on different platform names.

**Current decision:** **CONDITIONAL GO** for the PAQI-based Air Quality data plan, but implementation remains blocked on source-lineage/data-quality checks and the two-source interpretation. Do not claim two-source compliance, city-wide representativeness, or model superiority until the gates in [the feasibility decision](feasibility_decision.md) are met.

> **Prompt 1.6 update (2026-10-20):** The PAQI Karachi dataset is now directly verified as the strongest primary target candidate. Pakistan EPA's monthly Islamabad PM2.5/AQI reports are the strongest independent-source candidate found, but their sensor lineage and reuse licence are not verified. This addendum supersedes the earlier statement that no daily Pakistan city dataset had been identified; it does **not** clear the two-source requirement.
>
> **Prompt 1.7 update (2026-10-20):** PAQI's immutable Zenodo version metadata provides a file size and checksum, but not a verified row count or completeness summary. No row count is inferred from GitHub diff statistics. The official Pak-EPA site exposes a general webmaster email/phone, not a named monitoring-data owner. Islamabad reports are not Karachi forecast labels. OpenAQ public documentation confirms its provenance/licence metadata fields and API-key requirement; no authenticated Pakistan metadata was available.
>
> **Phase 2 update (2026-10-20):** The pinned PAQI CSV was intentionally acquired and fully parsed. It contains 3,009 rows for 3,009 consecutive dates from 2016-10-06 to 2024-12-31; six PM2.5 values are blank and were retained as flagged nulls. No duplicate dates or malformed/non-finite/negative values were found. The prior endpoint date 2024-12-30 was incomplete; full-file evidence establishes 2024-12-31.

## Evidence and terminology

- **Verified** means the linked official publisher material or bounded official API response directly supports the specific claim.
- **Partially verified** means some product/access/coverage facts are official, but at least one required aspect (such as a Pakistan record-level licence or usable PM2.5 history) is not established.
- **Unverified** means the evidence reviewed does not establish the claim. It does not mean the source or data do not exist.
- Search-result snippets and third-party summaries were not used as proof. A live site/API response is evidence of the response at research time, not a guarantee of future availability.

## Candidate 1 — World Bank WDI PM2.5 indicator

### Product actually verified

The World Bank Indicators API identifies `EN.ATM.PM25.MC.M3` as **“PM2.5 air pollution, mean annual exposure (micrograms per cubic meter)”**. Its official source note defines this as population-weighted exposure to ambient PM2.5 across urban and rural population. The API identifies the series source organization as **Global Burden of Disease Study 2023 (GBD 2023) Air Pollution Exposure Estimates and Risk Curves 1990–2023**, published by IHME, and says the underlying IHME record requires an account to retrieve.

A bounded API request for Pakistan returned annual entries for 2025 and 2024 with null values and a non-null 2023 value. The series response metadata reported 66 rows; that is not a count of usable observations, and the full series was not downloaded or counted. The World Bank chart displays annual years beginning at 1990. These are national annual estimates, not city-level measurements.

This review did **not** identify or verify a World Bank daily city-level PM2.5 estimates dataset. The verified WDI series should not be relabelled as one.

### Licence and source lineage

World Bank's data terms state that CC BY 4.0 generally applies unless data/indicator metadata says otherwise, require attribution to the Bank and data providers, prohibit implying Bank endorsement, and warn that third-party data may have additional restrictions or may not be reusable without the original provider's consent. The indicator metadata names IHME as its source and points to an IHME record whose data require an account. The exact terms permitting reuse and redistribution of that upstream GBD data in this project were not established. Therefore, the general World Bank terms alone are **not** sufficient to mark this indicator's complete source chain as cleared for republication.

### Feasibility

Useful as optional national annual context if the source-specific reuse terms and attribution are resolved. Not suitable for a city-day training target, daily freshness claims, or independent validation of models whose upstream inputs may overlap with GBD. The indicator metadata does not establish whether its upstream monitor inputs include any specific OpenAQ providers or stations.

## Candidate 2 — OpenAQ API v3

### Product and coverage verified

OpenAQ's official countries documentation says its country list contains countries with monitoring locations from which OpenAQ ingests data. That list includes Pakistan (`PK`, internal country ID 109). This establishes a country-level presence in OpenAQ's registry, **not** a Pakistan PM2.5 sensor, named city, active location, date coverage, or usable volume.

OpenAQ documents:

- Location metadata including locality, provider, owner, coordinates, instruments, sensors, operating status, and licence periods.
- Original measurements as reported by upstream sources, plus API-derived hourly/daily/yearly aggregates. Its documented daily aggregate is calculated from hourly averages in local time.
- API key authentication using the `X-API-Key` request header. Its published free rate limit is 60 requests/minute and 2,000 requests/hour; it documents HTTP 429 and rate-limit headers.

The bounded unauthenticated request to `https://api.openaq.org/v3/locations?country=PK&limit=1` returned HTTP 401. No authenticated request or data download was made.

### Licence and source lineage

OpenAQ's API exposes source-level licences and attribution details, including whether commercial use, modification, redistribution, or share-alike is allowed. The licence documentation gives a CC BY 4.0 example for a particular example location; that example is **not** evidence that every OpenAQ record, or any Pakistan record, has that licence. The exact applicable licence and its effective period must be checked for each chosen location/sensor and its upstream owner/provider. OpenAQ attribution, API terms, and the source licence all need to be respected.

OpenAQ is an aggregator for these purposes, not proof of the original instrument operator. The actual provider/owner chain and whether the readings are government, embassy, university, or community-monitor data must be inspected for Pakistan records.

### Feasibility

Promising candidate for station-level observations if an API key can be obtained and the authenticated metadata confirms adequate PM2.5 coverage and legally reusable records. At present its Pakistan pollutant/date/site coverage, sample volume, and exact licence are unverified.

## Candidate 3 — Punjab AQI portal

The page at [aqi.punjab.gov.pk](https://aqi.punjab.gov.pk/) was reachable and advertises an app for real-time AQI updates, forecasts, and health advisories. The reviewed public page did not identify a downloadable historical observations dataset, documented public API, measurement stations and operators, pollutant values/units, quality-control methodology, update history, or licence/redistribution terms.

This is evidence that a Punjab AQI-facing portal exists, not evidence that its displayed values are legally reusable training observations. Contact the responsible Punjab authority for the original records, provenance, methodology, archive, and written reuse permission before considering it a dataset.

## Candidate 4 — Pakistan EPA website (unverified)

The candidate URL [pak-epa.gov.pk](https://www.pak-epa.gov.pk/) could not be resolved during this check. No official dataset, API, licence, monitoring coverage, history, or source-owner information was verified from that site. The URL is recorded as a lead only; no Pakistan EPA data are claimed to have been found.

## Candidate 5 — U.S. EPA AirNow (scope check; not Pakistan data)

Official AirNow API documentation describes public API access through an account and real-time observations from over 2,500 monitoring stations, principally across the United States, Canada, and Mexico. Its FAQ recommends file products for historical/site-oriented databases rather than repeatedly polling end-user services. The same official material warns AirNow data are preliminary and must not be used for regulatory/trend/public decision-making purposes.

The reviewed AirNow material does not establish Pakistan coverage, and no Pakistan AirNow monitor records or reuse licence were found. It is not a suitable Pakistan source on this evidence and is not counted toward the source requirement. Its documented geographic and usage limitations are included to avoid treating a credible but irrelevant service as a second source.

## Independence and compatibility assessment

**Two-source independence: UNVERIFIED; not defensible on current evidence.**

1. The verified World Bank series is annual, national, population-weighted, and modelled/estimated from the upstream GBD program. It is not the same observation type or spatial/temporal unit as a monitor-level OpenAQ reading.
2. The official World Bank indicator metadata names GBD as the source, but the reviewed metadata does not enumerate the individual input monitors/providers. OpenAQ's actual Pakistan providers are also unknown until authenticated location/sensor metadata can be inspected.
3. It is therefore not possible to exclude overlap between monitor observations in OpenAQ and ground-monitor inputs used in GBD, nor to claim independent derivation. Different publishers are not sufficient evidence of independent sources.
4. There are no verified paired city/day observations for cross-source comparison. Using GBD's estimate as ground truth for a model trained on measurements, or the reverse, would be methodologically unjustified without a proven independent lineage and compatible resolution.
5. The Punjab portal could potentially be a separate official source, but the raw provider, source method, historical record access, licence, and relationship to OpenAQ remain unknown.

Independence can be reconsidered only after obtaining original-provider/methodology documentation for both sources and comparing station/provider identifiers, measurement dates, geographic locations, and source lineage. For a true independent evaluation, reserve one source as an untouched external validation set only if it supplies compatible measured target observations; do not tune on it.

## Data sufficiency and ML feasibility

**Enough compatible real records for a meaningful held-out test: not established.**

- The WDI series is annual at national scale; it cannot supply daily city rows. The API's 66-row series count includes null values and is not an evaluated sample count.
- OpenAQ's country registry confirms Pakistan is listed, but does not show how many Pakistan locations have PM2.5, which cities they represent, their period, regularity, record volume, calibration, or licences. These decisive facts could not be inspected without a key.
- Punjab's visible portal page does not expose the raw historical records needed to assess test-set size.
- No training/evaluation records, quality rates, model results, metrics, or feasibility record counts were generated.

### Provisional target (not approved until source gate passes)

If a legally reusable OpenAQ PM2.5 sensor has sufficiently regular Pakistan history, the most defensible 72-hour pilot is **next-local-calendar-day PM2.5 (µg/m³) for one fixed monitoring sensor**, not a city-wide ambient estimate. A fixed-site target avoids silently changing a city aggregate when its contributing sensors change. Label the prediction as a monitor reading, not a city exposure or health forecast.

If the project specifically requires a city target, define a city-day aggregation before analysis (stable site set, time zone, minimum contributing sensors and hours, aggregation rule), retain contributing sensor/record IDs, and report changes in site composition. Do not assert representativeness of all residents.

### Proposed evaluation (conditional, not performed)

- **Inputs:** only information available at the forecast cutoff: the same sensor's previous-day PM2.5, lagged values (for example, days 2 and 7), rolling summaries computed strictly from earlier observations, and calendar features. Missingness/availability indicators may be used; future or same-target-day measurements may not.
- **Baseline:** persistence, `next-day prediction = latest available prior-day measurement`. Compare candidate models against this baseline on identical dates.
- **Split:** sort by local date; train on earliest 70%, validate on the next 15%, and reserve the latest 15% as a final untouched test. Use validation for model/threshold choice and uncertainty calibration, never the final test. If a rolling-origin design is used instead, specify cutoffs before evaluating.
- **Metrics:** MAE as primary, with RMSE and a scaled error measure as additional context. Report paired model-minus-baseline results on the exact same test dates, sample counts, and missingness. Claim “beats baseline” only if measured held-out results support it.
- **Uncertainty:** calibrate prediction intervals from validation residuals (for example, split-conformal intervals), then report test-set coverage and interval width. Do not describe these as guaranteed coverage under distribution shift.
- **Error analysis:** report errors and coverage by station/sensor, city only if a defensible aggregation exists, season/month, and target concentration range. Show group sample counts; suppress or qualify groups too small for inference.
- **Precondition:** inspect coverage and a small permitted sample first. A short or discontinuous time series may make the holdout too small or unrepresentative. If there are insufficient valid dates, do not train or substitute synthetic/modelled observations.

## Compliance checklist

| Requirement | Status | Evidence / action |
|---|---|---|
| Two genuinely independent sources | **UNVERIFIED / blocker** | OpenAQ's Pakistan provider lineage and GBD's monitor inputs are not known; different publishers do not prove independence. |
| At least one credible source outside track sources, if applicable | **Needs organizer confirmation** | The event's official list of track sources was not supplied or verified. |
| Original publishers and source URLs | **Partial** | World Bank WDI endpoint and IHME upstream record identified; OpenAQ is an aggregator and specific original Pakistan publishers remain unknown; Punjab portal's underlying data owner is not established. |
| Exact licence and permitted public reuse | **UNVERIFIED / blocker** | World Bank terms contain third-party exceptions; OpenAQ requires record-level/source-level licence inspection; Punjab portal terms absent from reviewed page. |
| No synthetic/AI-generated training or evaluation observations | **Commitment; no data used** | No observations were acquired for training/evaluation. |
| No personal or identifiable data | **Commitment** | Only environmental monitoring measurements are in scope; do not collect user or account personal data into project datasets. |
| Reproducible acquisition and provenance | **Not implemented in this research-only phase** | Obtain API key through normal signup, document source query and licence, then test reproducible bounded fetches before any bulk acquisition. Never log credentials. |
| Pakistan-specific usefulness and honest limitations | **Conditional** | OpenAQ registry lists Pakistan; city PM2.5 coverage, continuity and representativeness remain unverified. |
| Dataset declaration deadline and format | **Organizer confirmation required** | Obtain the exact deadline/time zone, approved source list and required declaration format, especially if a deadline may have passed. |
| `Dataset_Proposal.pdf` requirement | **Organizer confirmation required** | Confirm whether a proposal PDF is required before source verification and what evidence/format it must contain. Do not generate a PDF that implies unverified sources or claims. |

## Official evidence links

1. [World Bank WDI indicator metadata API](https://api.worldbank.org/v2/indicator/EN.ATM.PM25.MC.M3?format=json) — indicator description, source note, named GBD/IHME source.
2. [World Bank Pakistan indicator API (bounded sample endpoint)](https://api.worldbank.org/v2/country/PAK/indicator/EN.ATM.PM25.MC.M3?format=json&per_page=5) — country-series metadata and a small page of annual records; no bulk data download.
3. [World Bank indicator data page](https://data.worldbank.org/indicator/EN.ATM.PM25.MC.M3?locations=PK) — annual indicator display.
4. [IHME GHDx GBD 2023 air-pollution exposure record](https://ghdx.healthdata.org/record/ihme-data/gbd-2023-air-pollution-exposure-estimates-1990-2023) — upstream record referenced by the World Bank metadata; account requirement is stated in that metadata.
5. [World Bank data summary terms](https://data.worldbank.org/summary-terms-of-use) — general CC BY 4.0 terms, attribution and third-party exception.
6. [Creative Commons Attribution 4.0 deed](https://creativecommons.org/licenses/by/4.0/) — attribution and other core licence terms; not a substitute for dataset-specific conditions.
7. [World Bank Indicators API documentation](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation) — API access and v2.
8. [OpenAQ countries resource](https://docs.openaq.org/resources/countries) — explains registry coverage and lists Pakistan (`PK`, ID 109).
9. [OpenAQ locations resource](https://docs.openaq.org/resources/locations) — documented location/provider/owner/sensor/licence metadata.
10. [OpenAQ measurements resource](https://docs.openaq.org/resources/measurements) — original versus aggregated observations and aggregation definitions.
11. [OpenAQ licences resource](https://docs.openaq.org/resources/licenses) — source-level permissions and licence fields.
12. [OpenAQ API-key documentation](https://docs.openaq.org/using-the-api/api-key) — key requirement and `X-API-Key` header.
13. [OpenAQ rate-limit documentation](https://docs.openaq.org/using-the-api/rate-limits) — free and custom request limits and API terms.
14. [Punjab AQI portal](https://aqi.punjab.gov.pk/) — public-facing AQI/app claims; not a raw-data or reuse licence.
15. [Pakistan EPA candidate URL](https://www.pak-epa.gov.pk/) — did not resolve during this check.
16. [AirNow API documentation](https://docs.airnowapi.org/) and [AirNow FAQ](https://docs.airnowapi.org/faq) — scope, preliminary-data warning, and file-product guidance.

## Prompt 1.6 addendum — PAQI, Pakistan EPA, and air-quality-only decision

**Research checked:** 2026-10-20. This addendum supplements, and where explicitly stated supersedes, the earlier audit. No application was built, dependencies were not installed, and no model was trained. Research was limited to official repository/DOI metadata, README/licence text, line-change metadata, first/last byte ranges, and official government report pages/documents.

### Primary candidate — PAQI Karachi PM2.5 daily dataset

#### Identity, files, access, and licence

- **Original publisher:** Pakistan Air Quality Initiative (PAQI), as identified in the repository description, README, and Zenodo record.
- **Repository:** [PakAirQuality/Unveiling-Karachi-Air](https://github.com/PakAirQuality/Unveiling-Karachi-Air), public, at inspected main-branch commit `164cdeff238db112137d593cfe9ffd0952346989`.
- **DOI/versioned record:** [10.5281/zenodo.15845428](https://doi.org/10.5281/zenodo.15845428); Zenodo API reports record publication date 2025-06-03, record ID 15845428, and licence ID `cc-by-4.0`.
- **Licence:** The repository's `LICENSE` and README explicitly state Creative Commons Attribution 4.0 International. This permits sharing and adapting subject to attribution, licence link, and indication of changes; do not imply PAQI endorsement. See [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Daily file at the inspected DOI/repository version:** `PAQI_Daily_PM2.5_Data_2016-2024_in_Karachi.csv`; Zenodo reports 51,387 bytes and MD5 `b3fe95e0550702ed7562687ea2e8a219`. The README describes the file with a *different name* (`PAQI_Karachi_Daily_PM2.5_Data_2016-2024.csv`), so a reproducible pipeline must use the actual listed DOI file name and pin the record/version or Git commit.
- **Other files:** the DOI record lists annual and monthly PM2.5 summaries, air-quality category day counts, annual and short-term standards tables, the README, and the PAQI report PDF. The annual/monthly and standards files are not substitutes for the daily target. The DOI monthly file has the unusual name suffix `.csv.csv`, while README aliases also differ.
- **Download/reproducibility:** DOI file content endpoints and GitHub raw/contents URLs are public and require no API credential. Pin the exact DOI/version or commit, verify checksum and attribution, and record actual fetched bytes/timestamp in a future manifest. The DOI is more stable than an unpinned branch URL.

#### Schema, time range, count, and missingness

- **Schema verified from README and bounded file sample:** two columns: `date` (`YYYY-MM-DD`) and `pm25_concentration_ug_per_m3` (number, µg/m³). The sample has date/value rows and no station identifier, source instrument identifier, QA flag, or explicit timezone.
- **Measurement definition from PAQI README:** daily **24-hour average** PM2.5 concentration, described as coming from the “PAQI monitoring network.” The README does not specify the sensor count, station list, network-to-city aggregation rule, calibration, completeness threshold, averaging time convention, or how missing days are handled. We therefore cannot establish whether each row is one sensor, a fixed panel/network aggregate, a selected station, or another summary. This is a material limitation for interpreting a “Karachi” prediction.
- **Observed date bounds:** the initial bounded samples showed `2016-10-06` and `2024-12-30`; the Phase 2 full-file parse established the actual last date as `2024-12-31`.
- **Phase 2 full-file quality result:** 3,009 CSV data records, 3,009 distinct consecutive calendar dates, 2016-10-06 to 2024-12-31 inclusive, zero duplicate dates, zero absent calendar dates within the observed span, and six blank PM2.5 values (0.20% of rows). All other rows had parseable ISO dates and finite nonnegative PM2.5 values. No rows were silently removed: all 3,009 dates appear in cleaned and gold outputs; the six blank measurements are flagged and excluded only from numeric use.
- **Date semantics:** each record is a date-only value. Do not infer timezone or sampling interval beyond PAQI's daily 24-hour average description.
- **Caveat on the file endpoint:** During inspection, an un-ranged request to the public Zenodo daily-file content endpoint was made. The tool displayed only a truncated portion, and no local copy was saved, but the request may have transferred the full 51,387-byte file to the tool. This was unintended given the instruction not to download the full dataset. No full-file statistical scan was performed; subsequent PAQI content inspection used bounded ranges and metadata only.

#### Methodology and source lineage

The PAQI README associates the data with the report *Unveiling Karachi's Air: A Scientific Foundation for a Clean Air City*, and calls them the foundational “on-the-ground” monitoring data from the PAQI monitoring network. This verifies PAQI's stated origin, but does not disclose the original instrument owner/operator for every value or the exact network aggregation method. The accompanying report and README need to be reviewed for sensor provenance, locations, temporal coverage/QA rules, and the daily statistic before making city-level or regulatory claims.

The GitHub repository and Zenodo DOI are two publication routes for the **same PAQI dataset**, not two independent sources.

### Strongest independent-source candidate — Pakistan EPA Islamabad monthly reports

- **Original publisher:** Pakistan Environmental Protection Agency (Pak-EPA), an official Government of Pakistan agency site.
- **Official page:** [Ambient Air Quality Reports](https://environment.gov.pk/Detail/ZjU5NDM3YjItNTdiOS00NTk5LWExYzUtMjI2NzE5YjdlOGM5). At audit time it listed monthly PDF reports from at least 2022 through September 2026.
- **Example report:** [Ambient Air Quality Data with AQI of Islamabad, September 2026 (PDF)](https://environment.gov.pk/SiteImage/Misc/files/AQR/AQI2026/September%2C%202026%20Air%20Quality%20Data%20with%20AQI%20(2).pdf). The three-page PDF's first page was visually inspected: it tabulates daily dates and values for SO₂, CO, NO₂, and PM₂.₅ in µg/m³, alongside AQI/category and a NEQS reference row. The December 2025 report was also visually inspected and presents the same daily Islamabad table format.
- **Coverage and frequency verified:** Islamabad, daily pollutant/AQI rows presented in monthly PDFs. The latest listed September 2026 example visibly includes dates 1–10 September across page 1; the PDF has three pages. Exact counts across all reports and pollutant/date completeness were not calculated.
- **Access:** Direct public PDF links from the Pak-EPA report index; no credentials observed. PDF tables require extraction/normalization if used in a reproducible pipeline. This is not yet a verified machine-readable historical dataset.
- **Licence/reuse:** No data licence, redistribution permission, or open-data terms were identified on the report index or in the reviewed report pages. Public accessibility does not establish permission to republish or use the tables for model training. **Unverified; blocker.**
- **Method / original instruments:** The PDF demonstrates published daily pollutant readings for Islamabad but does not identify (in the inspected page) monitoring station IDs, instrument owner/operator, number/location of stations, QA procedures, or how city/month data are aggregated. **Unverified; blocker.**
- **Independence relative to PAQI:** The reports are issued by Pak-EPA and report Islamabad, while PAQI's daily dataset is Karachi and attributed to the PAQI network. Distinct publisher and city make Pak-EPA the strongest independent-source *candidate* located. However, separate underlying monitor ownership, source chain, data providers, calibration, and any shared upstream inputs have not been demonstrated. It is therefore **not yet verified as a genuinely independent source**. It is geographically different, so it can inform Pakistan-wide context or an explicitly out-of-city generalization test, but it is not a paired Karachi observation and cannot by itself validate Karachi's next-day error.

### OpenAQ provenance and overlap

OpenAQ's official documentation says location metadata includes provider, owner, sensor, and source-specific licence periods; provider and owner can be the same or different. OpenAQ's API key is required for v3 access. An unauthenticated Pakistan location query returned HTTP 401, and no OpenAQ key was configured in the inspected environment. Consequently:

- No Pakistan OpenAQ location IDs, owner/provider IDs, sensor IDs, measurement timestamps, or licences were inspected in this phase.
- OpenAQ is an aggregator/access platform, not automatically an independent original publisher.
- If an OpenAQ location is owned by PAQI or reports PAQI-origin measurements, it is the same source lineage and must not count as the independent second source. Even a different owner name would require record/provenance verification.
- No OpenAQ overlap analysis with the PAQI CSV was done. Need owner/provider metadata plus date/value/site-level comparison before any overlap or independence statement.

### ML feasibility — conditional, not evaluated

The PAQI file's advertised date span suggests a daily forecasting experiment may be worth evaluating, but usable data volume is unknown. A chronological split size cannot be estimated from the metadata or bounded samples inspected; exact rows, unique dates, gaps and valid values remain to be established through a later full quality pass or publisher-provided summary.

**Preferred target:** next-day PM₂.₅ in µg/m³ for the published PAQI Karachi daily series. The data do not contain a sensor ID, so until PAQI explains aggregation, define this only as “next-day value of the published PAQI Karachi series,” not a single monitor or representative city-wide concentration. Use the date/value series and strictly lagged features available before prediction time. No future weather observation, target-day measurement, or derived information that uses the target may enter predictors.

**Baseline:** persistence: predict the next day's value from the latest available previous-day series value. Evaluate a candidate model only on the same target dates as persistence.

**Split:** chronological ordered dates, train earliest 70%, validation next 15%, final test latest 15%; freeze dates before model selection. But resolve the possible extra/duplicate date, exact missing dates, value validity, and temporal aggregation before assigning a split. If observation gaps are material, do not forward-fill labels; define the forecast protocol around actual forecast issuance and use only observations available at that time. Compare MAE and RMSE, paired against persistence; calibrate prediction intervals on validation and report held-out coverage/width and test sample counts. No model was trained, and no improvement is claimed.

**Smallest valid alternative if daily forecasting fails:** use the verified monthly PAQI summary as an explicitly PAQI-derived descriptive trend and seasonal anomaly/threshold-monitoring product, not supervised ML with a tiny annual series. If a predictive model is mandatory, retain daily observations but treat the project as a one-source Karachi forecast pilot and ask organizers whether a one-source ML track is acceptable; do not invent an independent validation source.

### Compliance and questions requiring organizer confirmation

1. Does the two-independent-source rule require both sources to contain the same target variable, or can the second source be independent contextual evidence? If both need target observations, can the Islamabad government PM2.5 records count despite the Karachi/Islamabad spatial mismatch?
2. Is PAQI an eligible primary source and does the track-source list require a second source outside the listed set?
3. What is the precise dataset declaration deadline, time zone, late-submission policy, and required content/format for Dataset_Proposal.pdf? The prior audit could not verify these organizer rules.
4. Does the event permit the Pak-EPA monthly PDF data to be used/reproduced, or is written permission required? No licence was found in reviewed material.
5. Does the event accept PAQI's self-described network daily series without the sensor-level aggregation method, or must the primary publisher clarify this?

### Updated evidence links

- [PAQI public GitHub repository](https://github.com/PakAirQuality/Unveiling-Karachi-Air) — repo publisher and contents.
- [PAQI README](https://github.com/PakAirQuality/Unveiling-Karachi-Air/blob/164cdeff238db112137d593cfe9ffd0952346989/README.md) and [repository licence](https://github.com/PakAirQuality/Unveiling-Karachi-Air/blob/164cdeff238db112137d593cfe9ffd0952346989/LICENSE) — schema, stated daily 24-hour statistic/network origin, filenames/description and CC BY 4.0.
- [Zenodo versioned record](https://zenodo.org/records/15845428) and [Zenodo API metadata](https://zenodo.org/api/records/15845428) — DOI, licence ID, dates, exact filenames, sizes, checksums and file endpoints.
- [PAQI daily CSV in GitHub at inspected commit](https://github.com/PakAirQuality/Unveiling-Karachi-Air/blob/164cdeff238db112137d593cfe9ffd0952346989/PAQI_Daily_PM2.5_Data_2016-2024_in_Karachi.csv) — file existence/size; bounded first and last byte ranges inspected.
- [GitHub daily-file commit history](https://api.github.com/repos/PakAirQuality/Unveiling-Karachi-Air/commits?path=PAQI_Daily_PM2.5_Data_2016-2024_in_Karachi.csv&per_page=5) — repository history only; diff statistics are not used to estimate data rows.
- [Pak-EPA Ambient Air Quality Reports index](https://environment.gov.pk/Detail/ZjU5NDM3YjItNTdiOS00NTk5LWExYzUtMjI2NzE5YjdlOGM5) — official monthly report listing.
- [Pak-EPA Islamabad September 2026 example report](https://environment.gov.pk/SiteImage/Misc/files/AQR/AQI2026/September%2C%202026%20Air%20Quality%20Data%20with%20AQI%20(2).pdf) and [December 2025 example](https://environment.gov.pk/SiteImage/Misc/files/AQR/AQI2025/AQI%20December%202025.pdf) — visually inspected daily pollutant/AQI table examples.
- [OpenAQ locations](https://docs.openaq.org/resources/locations), [providers](https://docs.openaq.org/resources/providers), [owners](https://docs.openaq.org/resources/owners), [licences](https://docs.openaq.org/resources/licenses), and [API-key instructions](https://docs.openaq.org/using-the-api/api-key) — metadata required to assess source ownership and rights; no authenticated Pakistan response was available.

## Prompt 1.7 — remaining blocker audit (2026-10-20)

### PAQI: verified metadata versus properties that require full inspection

Zenodo API metadata identifies version DOI `10.5281/zenodo.15845428` (record 15845428; concept DOI `10.5281/zenodo.15845427`), publication date 2025-06-03, licence `cc-by-4.0`, file `PAQI_Daily_PM2.5_Data_2016-2024_in_Karachi.csv`, size 51,387 bytes, and MD5 `b3fe95e0550702ed7562687ea2e8a219`. Creators listed are Omar Abid, Dawar Hameed Butt, and Mahad Naveed. The inspected GitHub commit is `164cdeff238db112137d593cfe9ffd0952346989`. Pin the immutable version DOI and record file checksum; do not rely on the mutable default branch.

The README and bounded edge samples support the declared two-column `date` / `pm25_concentration_ug_per_m3` schema, units µg/m³, and publisher-described daily 24-hour network averages. Bounded beginning/end regions show dates 2016-10-06 and 2024-12-30, respectively. These do not establish continuous coverage, total rows, uniqueness, missingness, or all-row validity. Public record metadata has no row-count or quality summary. Without a full-file read or publisher-supplied validated summary, exact row count, duplicate dates, nulls/invalid values, missing-date intervals, and usable ML sample size **cannot be determined**. GitHub diff line counts are not used to estimate them. No full-file download or scan was performed in this phase.

CC BY 4.0 requires credit to the creators, title/source, a link to the licence, and identification of changes; do not imply PAQI endorsement. Zenodo lists Omar Abid, Dawar Hameed Butt, and Mahad Naveed as creators. Suggested attribution: “Omar Abid, Dawar Hameed Butt, and Mahad Naveed / Pakistan Air Quality Initiative (PAQI), *Unveiling Karachi's Air: A Scientific Foundation for a Clean Air City*, version DOI 10.5281/zenodo.15845428, CC BY 4.0. Changes, if any, are identified in this work.”

The README still does not define whether each daily value is one monitor, a fixed network aggregate, or another summary. Sensor/site IDs, averaging window/time convention, calibration/QA and missing-day rules require publisher clarification.

### Pakistan EPA contact and second-source fitness

The official [Pak-EPA reports index](https://environment.gov.pk/Detail/ZjU5NDM3YjItNTdiOS00NTk5LWExYzUtMjI2NzE5YjdlOGM5) links Islamabad monthly PDFs containing daily PM2.5, AQI and other pollutant columns. The official [homepage](https://environment.gov.pk/) lists **webmaster@environment.gov.pk** and **051-9250715**. These are general site contacts, not a verified monitoring-data owner's details; no named data owner or direct data-unit email was found on the inspected official pages. Address the message to the webmaster and request routing to the responsible air-quality monitoring/data unit.

Islamabad EPA observations cannot be target labels or direct held-out validation for a Karachi-only next-day forecast. At best, after written reuse permission and provenance checks, they can support contextual comparison or an explicitly out-of-city generalization analysis. Such analysis is not an evaluation of Karachi forecast error. Different city/publisher alone does not establish independent source lineage.

Reuse licence, station identifiers, monitoring operator/instruments, QA/calibration, daily aggregation, and overlap with PAQI/OpenAQ are still **UNVERIFIED**. Do not extract or republish values or claim EPA source independence until those questions are answered.

### OpenAQ documentation and access blocker

OpenAQ's official [Locations documentation](https://docs.openaq.org/resources/locations) says location metadata can include provider, owner, coordinates, instruments, sensors, timezone and licence periods. Its [API-key instructions](https://docs.openaq.org/using-the-api/api-key) require an `X-API-Key`; documented [rate limits](https://docs.openaq.org/using-the-api/rate-limits) apply. This documentation confirms platform metadata capabilities, not Pakistan station records or permissions.

No key was configured; the earlier unauthenticated Pakistan request returned HTTP 401. No Pakistan location/provider/owner/sensor records, measurement dates, licence periods, or PAQI overlap were inspected. Do not request, expose, or assume credentials. OpenAQ is not verified as an independent source and remains a provenance blocker.

### Draft inquiries — not sent

**Pak-EPA email**

To: `webmaster@environment.gov.pk` (general contact; request routing to air-quality monitoring/data owner)  
Telephone listed by agency: `051-9250715`  
Subject: Reuse and provenance inquiry — Islamabad ambient air-quality reports

> Dear Pakistan EPA team,  
> We are preparing a student research project on Pakistan air quality and are considering the daily PM2.5 tables in your Islamabad monthly Ambient Air Quality Reports. May we use and publish derived analysis of these values in a non-commercial student project and public dashboard? Please identify the applicable licence/attribution requirements and whether redistribution of extracted values is permitted. Could you share the monitoring station/site IDs, instrument/operator, QA/calibration procedures, daily averaging/timezone and aggregation method, and confirm whether these readings are supplied by PAQI, appear in OpenAQ, or otherwise overlap those sources? If this is not your unit, please forward us to the responsible data owner.  
> Thank you.

**Organizer clarification message**

> Our finalized project is Air Quality Intelligence for Pakistan, with PAQI's Karachi daily PM2.5 series as the proposed forecast target. Must both independent sources provide PM2.5 target labels, or may an independent meteorological source count as a feature source? Does a source covering another Pakistani city, such as Islamabad, qualify? May government-report data without an explicit open licence be used for analysis, and is written permission required? Please confirm the dataset proposal/declaration deadline, timezone, late-submission rule, and required Dataset_Proposal.pdf format/template.

### Smallest defensible scope for the four-person team

Keep one Karachi-focused task: forecast the next published PAQI-series PM2.5 value, compare against persistence, and report only a chronological held-out evaluation after a full quality validation. Until PAQI explains aggregation, label it as a prediction of the *published series*, not a sensor-specific or citywide exposure forecast. Split work across provenance/licensing, data-quality/pipeline, evaluation, and evidence-grounded dashboard/insights.

Use Pak-EPA only for contextual/out-of-city analysis after provenance, written reuse permission, and organizer acceptance; it cannot validate Karachi next-day errors. If EPA permission/source independence is unresolved, omit its measurements and state that the two-source requirement is unmet unless organizers approve another interpretation. Do not claim two-source compliance. OpenAQ is optional investigative work only, not a dependency until authenticated metadata establish source lineage, terms, and usefulness.

## Phase 2 — acquisition and warehouse execution result

The root `Makefile`, source configuration, standard-library Python pipeline, tests, `.gitignore`, `.env.example`, and root README implement the Phase 2 data path. The pipeline acquired PAQI by a versioned Zenodo metadata GET followed by the versioned file GET, and verified Zenodo's record DOI, CC BY 4.0 identifier, file name, byte size and MD5 before accepting it. Raw content is retained locally and excluded from Git; a provenance sidecar and append-only manifest capture UTC time, URLs/request description, licence, version, size and checksums.

**First execution:** `python -m pipeline.run` downloaded and checksum-verified the source but exited 1 because the initial validator treated blank PM2.5 observations as critical invalid values. The pipeline was corrected to retain dated blank measurements in cleaned/gold with `missing_pm25_value` flags, while keeping structurally invalid, invalid-date, negative, or non-finite records in an explicit rejected table.  
**Final execution:** after a corrected cached rerun at `2026-10-19T21:40:17Z`, the latest `python -m pipeline.run` at `2026-10-19T21:44:02Z` returned 0 with `success_with_warnings`, reusing the checksum-verified cache. It revalidated live Zenodo metadata and raw MD5/SHA-256, then produced 3,009 cleaned and gold rows, zero rejected records, and six flagged blank measurements. There were no duplicate dates or absent calendar dates. Warnings remain for missing measurements, absent station identity/timezone/aggregation documentation, and stale observations. Latest observation date 2024-12-31 was 657 days old relative to the pipeline's UTC run date 2026-10-19.

The raw CSV is 51,387 bytes; MD5 `b3fe95e0550702ed7562687ea2e8a219`; SHA-256 `2359a11850df9d5798c446e1013c09f22914426ffc1e1d928c2ec9824502debf`. The pipeline stores cleaned data, gold data, manifest, quality report, rejected-record/record-issue tables, and execution status under `data/`. No EPA or OpenAQ data were acquired or joined; cross-source independence remains `not_run`.

The requested shell command `make data` could not be run on this Windows host because GNU Make is not installed (`make` was not recognized). The equivalent target command `python -m pipeline.run` was run and succeeded with warnings. No package was installed. All 11 automated software tests passed; they use tiny synthetic CSVs only as test fixtures, never as project observations or model data.
