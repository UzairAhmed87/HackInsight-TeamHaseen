# HackInsight '26 — alternative track feasibility comparison

**Research checked:** 2026-10-20  
**Scope:** Research only. No complete dataset was downloaded, no dependency was installed, no training was run, and no metrics were generated. The WFP price CSV was inspected only through two bounded byte-range samples (2 KB from the start and 2 KB from the end). The NASA and NOAA examples below are bounded API responses.

## Decision in brief

**Strongest candidate to investigate first: Food Price / Food Security.** A public Pakistan-specific WFP Price Database extract is described in HDX metadata, with a published file size of 1,637,040 bytes and a CC BY-IGO licence identifier. Its sampled CSV boundaries contain real Pakistan retail price records dated 2004-01-15 and 2026-08-15. Pakistan Bureau of Statistics (PBS) independently documents monthly price collection for CPI across 68 urban markets in 35 cities and 27 rural centers.

**No track currently meets the full minimum evidence bar.** The WFP/PBS source pair has not been shown to be independent: the WFP extract's original market-price providers and overlap with PBS are unknown, and PBS dataset reuse terms were not verified. Climate has promising public data and clearly different satellite and station measurement modalities, but exact input overlap, applicable reuse terms for both selected products, and continuous Pakistan station history remain unresolved. Air quality remains blocked by unavailable OpenAQ credentials and unverified Pakistan source coverage.

Scores are evidence-based feasibility judgments, not data-quality measurements, model results, or proof of compliance. A high dashboard score does not compensate for a failed source-independence or licence gate. The team's exact submission deadline and remaining hours were not provided, so the timeline scores compare relative effort within a 72-hour project window; they are not a calendar guarantee.

## Score summary

| Track | Availability / volume | Source independence | Licence / compliance | Held-out ML feasibility | Pakistan usefulness | Remaining-time feasibility | Dashboard / grounded insights | Total / 35 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A — Air Quality | 1 | 1 | 1 | 1 | 4 | 2 | 4 | 14 |
| B — Climate / Heat | 4 | 3 | 2 | 3 | 4 | 4 | 5 | 25 |
| C — Food Price / Food Security | 4 | 2 | 3 | 4 | 5 | 4 | 5 | 27 |

## Track A — Air Quality

### Evidence status

- **VERIFIED:** World Bank WDI `EN.ATM.PM25.MC.M3` is national, annual, population-weighted PM2.5 exposure with GBD/IHME provenance; it is not daily city-level monitor data. The World Bank API response included null recent years.
- **VERIFIED:** OpenAQ documentation lists Pakistan in its country registry and requires an API key for v3 requests. The previous bounded unauthenticated Pakistan locations call returned HTTP 401.
- **VERIFIED:** No `OPENAQ_API_KEY` or `OPENAQ_TOKEN` environment variable is configured in the inspected environment. Secret values were not searched or read. Therefore authenticated metadata and sample inspection could not be performed.
- **PARTIALLY VERIFIED:** Punjab's AQI portal advertises real-time public-facing AQI/app functionality. Raw historical measurements, exact owners, methodology and reuse terms were not established.
- **UNVERIFIED:** Pakistan site/sensor counts, PM2.5 history, usable records, per-sensor licensing, independent second-source lineage, and data volume.

### Scores and reasons

- **Availability / volume — 1/5:** World Bank data are available but have the wrong temporal and spatial unit. OpenAQ lists Pakistan, but authenticated inspection was unavailable. No suitable Pakistan city-day series or record count is verified.
- **Source independence — 1/5:** World Bank GBD estimates and OpenAQ monitor readings differ in product type and resolution; GBD input-monitor overlap with OpenAQ is not known. Punjab portal provenance is also unknown.
- **Licence / compliance — 1/5:** World Bank terms warn of third-party exceptions for IHME-sourced data. OpenAQ licences vary by source and time period and could not be inspected. Punjab portal reuse terms were not found.
- **Held-out ML feasibility — 1/5:** No compatible city-day source history has been established. A chronological test set cannot yet be justified.
- **Pakistan usefulness — 4/5:** Air pollution is directly relevant, and Pakistan appears in OpenAQ's registry, but actual coverage and representativeness remain unverified.
- **Remaining-time feasibility — 2/5:** It may be feasible if a key and suitable records are obtained immediately; source/licence/independence verification is an unbounded blocker.
- **Dashboard / grounded insights — 4/5:** City PM2.5 and health-context visualizations could be valuable, but only with verified observations, uncertainty and citation provenance.

**Gate:** Do not select this track unless OpenAQ metadata and a second independently sourced, compatible, legally reusable Pakistan PM2.5 series can be verified.

## Track B — Climate / Heat Intelligence

### Sources and evidence

**NASA POWER Daily API**

- **VERIFIED:** The official Daily API documentation says it provides daily point data, with meteorological daily data available from 1981-01-01 to near real time, and documents supported formats and point requests. The bounded sample request to the official API returned three days of Pakistan data without an authentication challenge.
- **VERIFIED:** At the same coordinates as a NOAA Karachi/Jinnah International station response (24.907 N, 67.161 E), a three-day NASA POWER solar API sample returned `ALLSKY_SFC_SW_DWN` for 2020-01-01 through 2020-01-03, with units `kW-hr/m^2/day` and response source `SYN1DEG`.
- **VERIFIED:** POWER methodology identifies its solar energy-flux products as derived from satellite sources including SRB and CERES. The source-methodology page warns that the solar daily series can combine multiple source products and is not recommended for climate-trend assessment across source changes.
- **PARTIALLY VERIFIED:** The API returned a public sample and documentation describes public API use, but a product-specific licence/redistribution statement was not established in this audit. Solar source temporal start/end details need to be confirmed for the selected parameter.

**NOAA NCEI GHCN-Daily / Access Data Service**

- **VERIFIED:** NOAA describes GHCN-Daily as a quality-controlled, station-based dataset with more than 90,000 stations globally, daily temperature and precipitation elements, and about 30 integrated source datasets. Its methodology documents source matching and merging; it is a composite, not a single original sensor network.
- **VERIFIED:** The official NCEI Access Data Service documents bounded GET queries by dataset, station, date, element and format. A permitted three-day response for station `PKM00041780` returned `JINNAH INTERNATIONAL, PK` at 24.907 N, 67.161 E, including `TAVG` and `PRCP` fields for 2020-01-01 through 2020-01-03.
- **PARTIALLY VERIFIED:** Pakistan relevance and a real Karachi station sample are established; this sample does not establish continuous daily coverage, history length, or the station's full source lineage. The applicable reuse terms for this international composite record were not verified.

**Potential dataset alternative:** ERA5 is global hourly reanalysis from 1940 onward at 0.25-degree regridded resolution; the official catalogue metadata identifies CC BY 4.0 and free access upon accepting the applicable licence. It requires a CDS account and request-based retrieval. It assimilates observations; it is not an independent observed ground truth for NOAA station records. It is not required for the simpler NASA POWER + NOAA pilot.

### Scores and reasons

- **Availability / volume — 4/5:** NASA POWER has a documented daily API and a live Pakistan sample; NOAA has documented station queries and a real Karachi sample. The source catalogues are large, but the specific station's valid history and record count were not checked.
- **Source independence — 3/5:** NASA solar flux is satellite-derived and NOAA GHCN-Daily is a merged surface-station record, so the primary measured modalities and stated data lineages are distinct. However, GHCN itself integrates many sources, NASA products may use ancillary model inputs, and exact overlap/influence for the selected location and periods has not been reconciled. Use the solar series as a predictor, not as independent replicated temperature ground truth; do not claim full statistical independence without a lineage check.
- **Licence / compliance — 2/5:** NASA POWER's product-specific reuse terms and NOAA's applicable terms for international GHCN records were not established. ERA5 has a documented CC BY 4.0 licence if separately selected, but it has account/access requirements and shares the general reanalysis-versus-observation dependence issue.
- **Held-out ML feasibility — 3/5:** Daily data and a real aligned location/date sample are demonstrated, and daily target prediction can be specified. Three days do not establish a long, complete station history or sufficient honest test support.
- **Pakistan usefulness — 4/5:** Local weather and heat-risk views are relevant, but an airport sensor or coarse satellite/reanalysis grid is not a substitute for population exposure or city-wide heat-health evidence.
- **Remaining-time feasibility — 4/5:** Small API requests need no full archive transfer. A one-station pilot is technically plausible, subject to the missing station-history and legal checks.
- **Dashboard / grounded insights — 5/5:** Daily temperature, rainfall and satellite irradiance can support traceable charts, heat-season summaries and station-specific forecasts if each value retains its source/date/record provenance.

### Provisional ML task (not run)

If the full station record is adequate and reuse terms are confirmed: predict next-day observed `TAVG` for the Karachi station using only prior NOAA station observations, calendar fields, and lagged NASA satellite-derived daily solar irradiance. Compare with a persistence baseline using an untouched chronological final period. First inspect station completeness, units, quality flags and source switches; no forecast or performance claim has been produced.

**Gate:** Verify continuous station history and source/terms lineage for both series, and establish whether the different modalities are sufficiently independent under the organizers' interpretation before implementation.

## Track C — Food Price / Food Security Intelligence

### Sources and evidence

**WFP Food Prices for Pakistan, distributed through HDX**

- **VERIFIED:** HDX's public package metadata identifies the title as “Pakistan - Food Prices,” says the records are sourced from the World Food Programme Price Database, assigns licence ID `cc-by-igo` / “Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO),” and links to CC BY 3.0 IGO legal code. The metadata lists a Pakistan CSV resource of 1,637,040 bytes, created 2018-09-26 and last modified 2026-10-18. The metadata's update cadence and global coverage describe the broader WFP database, not necessarily Pakistan's latest observation.
- **VERIFIED:** Two bounded byte-range samples from the public CSV (first 2 KB and final 2 KB; HTTP 206) showed real retail market-price rows: the initial rows include `2004-01-15` observations for Quetta, Peshawar, Lahore, Multan and Karachi; the tail sample contains Karachi/Multan observations dated `2026-08-15`, across named commodities and units in PKR. The file was not downloaded in full and its row count or full-file date range was not computed.
- **PARTIALLY VERIFIED:** HDX's licence metadata is clear enough to identify the assigned licence, but the original WFP data provider's authorization and any source-specific exceptions should be confirmed before republicating the raw CSV or derived extracts. HDX is the distribution/catalogue layer; WFP is named as the price database source.

**Pakistan Bureau of Statistics (PBS) Price Statistics**

- **VERIFIED:** PBS's official price-statistics page says monthly price data are collected from 68 urban markets in 35 cities and 27 rural centers to compute national monthly inflation. The page describes CPI methodology and publishes downloadable price-statistics materials.
- **VERIFIED:** The same page exposed public links to a weekly SPI annex for the week ended 2026-10-15 and a monthly review for September 2026; it also lists an Excel file named “Average Monthly SPI Items Prices.”
- **PARTIALLY VERIFIED:** PBS provides Pakistan-specific price data and public reports/files, but this audit did not retrieve a bounded PBS observation sample, establish a machine-readable historical market/item panel, or find an explicit reuse licence on the reviewed page.
- **UNVERIFIED:** Whether WFP's Pakistan retail-price records are collected independently of, supplied by, or overlapping with PBS prices. The WFP extract's specific original market-by-market provider/method is not documented in the inspected sample/metadata.

**FAO FPMA / GIEWS (additional candidate, not counted)**

- **VERIFIED:** FAO's official FPMA tool is reachable, and FAO's general Statistical Database Terms describe CC BY 4.0 as the default for FAO corporate statistical databases unless dataset metadata says otherwise, with attribution and third-party-data exceptions.
- **UNVERIFIED:** The tool page did not expose usable rendered country records in this check; no Pakistan time series, sample, dataset-specific licence, or provenance was verified. General FAO database terms do not prove that this particular tool dataset is covered by them. It is not counted as a second source.

### Scores and reasons

- **Availability / volume — 4/5:** A Pakistan-specific public file with a recorded 1.64 MB size and real city/commodity rows at both sampled file boundaries is directly demonstrated; PBS also documents its collection network and publishes files. Exact row counts, continuity and overlap remain unchecked.
- **Source independence — 2/5:** WFP and PBS are distinct institutions and collection systems in their public descriptions, but the WFP extract's underlying contributors are not named and could include the same official prices. No true independence finding is justified yet.
- **Licence / compliance — 3/5:** The HDX metadata assigns CC BY-IGO and links the 3.0 IGO legal terms, but WFP/source-owner authority and exceptions should be confirmed. The reviewed PBS material has no explicit dataset licence, blocking its use as the cleared second source.
- **Held-out ML feasibility — 4/5:** The sample-boundary dates span 2004 to 2026 and reveal monthly-style market price observations for repeated city/commodity combinations, making a chronological market-item forecast plausible. The complete file's row count, missing months, stable item/market coverage and any source changes remain unmeasured; feasibility is promising, not proven.
- **Pakistan usefulness — 5/5:** The WFP sample contains Pakistan cities, commodities, quantities/units and PKR prices; PBS explicitly covers urban and rural markets across Pakistan. This can support market-price monitoring, but not household food security, affordability or causal claims without additional evidence.
- **Remaining-time feasibility — 4/5:** The WFP file is small by metadata size, and a bounded public sample is accessible without authentication. A second source still needs licence/provenance clearance; implement only after that and organizer rules are checked.
- **Dashboard / grounded insights — 5/5:** City/market/item trends and price changes can be traced to dated market rows. Any aggregation must list contributing record IDs, normalize units carefully, and distinguish observed nominal prices from inflation-adjusted affordability.

### Provisional ML task (not run)

If an eligible independent second source and data checks pass: predict next-month retail price for a fixed market/commodity series (for example, a named staple, fixed unit and retail price type). Compare persistence to a seasonal-naive baseline using only training/validation periods to select the model, then an untouched latest chronological test period. Report MAE/RMSE, date coverage, uncertainty intervals and errors by city, commodity and season with sample counts. Do not treat CPI as the price truth or equate it to the WFP item/market series without a documented mapping.

**Gate:** Get the PBS source owner to document a reusable historical item/market dataset and licence, and disclose whether those records feed the WFP series. Reconcile matching dates, markets, items, units and provider IDs before claiming independence.

## Cross-track requirements and unresolved organizer rules

- The required number of sources, what “independent” means for this event, any prescribed track-source list, and whether at least one source must be outside that list have not been independently verified.
- Dataset declaration deadline, time zone, late-submission policy and Dataset_Proposal.pdf template/requirements still require organizer confirmation.
- No track has two sources that simultaneously clear original-provider lineage, compatible Pakistan records, legal reuse, and independence.
- No target/model has been trained; there are no model metrics, held-out sample counts, uncertainty results, or performance claims.

## Evidence register

| Evidence | What it establishes |
|---|---|
| [HDX package metadata API — WFP Food Prices for Pakistan](https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-pakistan) | Dataset title, WFP Price Database named as source, HDX-assigned CC BY-IGO licence metadata, file size, resource URL and catalogue dates. |
| [WFP Pakistan price CSV resource](https://data.humdata.org/dataset/125455ff-c8a8-4f4b-9190-bf0e84559dc7/resource/8cf7a8a2-58a1-4c3f-bafe-f38af68d971b/download/wfp_food_prices_pak.csv) | Two bounded HTTP Range samples only; real rows with Pakistan market, commodity, date, currency, price and unit fields. |
| [CC BY 3.0 IGO legal code](https://creativecommons.org/licenses/by/3.0/igo/legalcode) | Attribution, adaptation and redistribution permissions and IGO dispute terms for the licence identified in HDX metadata. |
| [PBS Price Statistics](https://www.pbs.gov.pk/price-statistics/) | Official monthly collection geography and method summary; public reports/Excel links. |
| [FAO FPMA/GIEWS tool](https://fpma.fao.org/giews/fpmat4/global/) | Existence of the official tool only; Pakistan data and dataset-specific licence were not established. |
| [FAO Statistical Database Terms](https://www.fao.org/contact-us/terms/db-terms-of-use/en/) | Default CC BY 4.0 for FAO corporate statistical databases, attribution and third-party exceptions; applicability to FPMA tool not verified. |
| [NASA POWER Daily API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Daily API capabilities and temporal/access specifications. |
| [NASA POWER bounded Karachi solar sample](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude=67.161&latitude=24.907&start=20200101&end=20200103&format=JSON&time-standard=UTC) | Three actual daily Pakistan values returned with source `SYN1DEG`, units, coordinates and requested dates. |
| [NASA POWER data-source methodology](https://power.larc.nasa.gov/docs/methodology/data/sources/) and [data FAQ](https://power.larc.nasa.gov/docs/faqs/data/) | Satellite sources for solar energy flux, source changes and warnings, meteorological source lineage and daily coverage. |
| [NOAA NCEI GHCN-Daily metadata](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C00861/html) | Global station-based data volume, elements and approximately 30 integrated sources. |
| [NOAA NCEI API documentation](https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation) | Bounded station/date/variable API query structure and supported response formats. |
| [NOAA bounded Karachi station sample](https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=PKM00041780&startDate=2020-01-01&endDate=2020-01-03&dataTypes=TAVG,PRCP&includeStationName=true&format=json) | Three actual station-day API records, station name and coordinates for the sample only. |
| [ERA5 catalogue record](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels) | Global hourly reanalysis from 1940, grid/resolution, latency, observation assimilation and structured CC BY 4.0 licence metadata. |
