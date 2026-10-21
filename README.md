# HackInsight '26 — Karachi Air Quality (Team Haseen)

**Track:** Air quality · **Primary user:** Karachi residents and the people who advise them (school heads, clinic staff, journalists) who need to know how polluted the air has been and is, without being misled.

- **Live dashboard:** https://hackinsight-air-quality-pakistan.onrender.com/
- **Hugging Face Space:** Gradio app in `app.py` (Space card: `README_HF.md`)
- **Release:** tag `v1.0-final`

The project builds a three-source PM2.5 warehouse for Karachi, rebuilt with one command. A deterministic Data Quality Agent decides to FIX, FILL or FLAG each issue and explains why. A next-day model is evaluated against persistence with uncertainty and errors by group. An Insight Agent answers with citations and says "I don't know" when the evidence cannot answer. An hourly Prefect flow keeps the warehouse and dashboard fresh.

## Sources

| Source | Original publisher | Access | Licence | Resolution | Gold rows | Coverage |
|---|---|---|---|---|---|---|
| PAQI Karachi daily PM2.5 | Pakistan Air Quality Initiative (Abid, Butt, Naveed) | [Zenodo DOI 10.5281/zenodo.15845428](https://doi.org/10.5281/zenodo.15845428) | CC BY 4.0 | daily | 3,009 | 2016-10-06 → 2024-12-31 |
| U.S. Consulate General Karachi monitor | U.S. Department of State, disseminated through U.S. EPA AirNow | [OpenAQ location 8156](https://api.openaq.org/v3/locations/8156) (provider AirNow) | US Public Domain | hourly | 46,937 | 2019-05-22 → 2025-03-04 (monitor stopped publishing) |
| Urban Unit AirGradient network | The Urban Unit (owner) with AirGradient sensors | OpenAQ v3 hourly aggregates, 8 locations listed in `config/openaq_urban_unit_karachi.json` | CC BY 4.0 | hourly | 65,200 | 2025-06-19 → updated every hour |

**Total: 115,146 gold rows.** None of the data is synthetic, AI-generated or personal. Licences are read from OpenAQ location metadata on every run, and the pipeline fails if they change. OpenAQ is the access platform only; each table names the original publisher. PAQI is the hackathon-track candidate. The U.S. Consulate monitor and the Urban Unit network come from publishers outside that list. Check them against the organisers' official track list before declaring.

**Independence.** PAQI does not document which monitors feed its series, so we don't assume measurement-level independence. We measure agreement instead. On 1,399 days with both a PAQI value and a complete Consulate daily mean, **Pearson r = 0.87**, PAQI averages **3.43 µg/m³ higher** (mean absolute difference 11.12), and **63 days are flagged** for large disagreement (outside Q1 − 3·IQR to Q3 + 3·IQR). See `data/quality/warehouse_quality_report.json` and `data/processed/gold_karachi_daily_cross_source.csv`.

## Rebuild everything

```sh
export OPENAQ_API_KEY=...            # free key: https://explore.openaq.org/register (first run only)
make data                            # raw → cleaned → gold for all three sources + cross-source checks
make forecast                        # model vs persistence, uncertainty, errors by group
make test                            # 81 unit tests (synthetic software fixtures only)
pip install -r requirements-pipeline.txt && make flow   # the same steps as one Prefect flow run
```

On Windows without GNU Make, use `python -m pipeline.warehouse`, `python -m pipeline.forecasting`, `python -m unittest discover -s tests` and `python prefect_flow.py`. The pipeline itself uses only the Python 3.12 standard library.

The first `make data` downloads about 94 MB of raw OpenAQ JSON, roughly 210 requests at 1.1 s spacing (about 5 minutes). Later runs reuse raw files after re-checking their SHA-256. Without a key, `make data` rebuilds from verified cached raw files and fails with a clear message if any are missing.

## Warehouse layers and lineage

| Layer | PAQI | U.S. Consulate | Urban Unit network |
|---|---|---|---|
| raw (never overwritten) | `data/raw/paqi…/` CSV, MD5 + size checked against Zenodo | `data/raw/us_consulate_karachi_pm25/…/<YYYY-MM>.json` + `.provenance.json` (URL without key, fetch time, SHA-256, record count), `location.json`, `flags.json` | `data/raw/urban_unit…/sensor_<id>/<YYYY-MM>.json` + sidecar; the current month is `<YYYY-MM>.partial.json`, replaced each hour until the month closes |
| cleaned | `data/cleaned/paqi_karachi_daily_pm25.csv` | `data/cleaned/us_consulate_karachi_hourly_pm25.csv` | `data/cleaned/urban_unit_karachi_hourly_pm25.csv` |
| gold | `data/processed/gold_air_quality.csv` | `gold_us_consulate_karachi_hourly.csv`, `…_daily.csv` | `gold_urban_unit_karachi_hourly.csv`, `…_sensor_daily.csv`, `…_network_daily.csv` |

Every gold row has a stable `row_id`, which is the SHA-256 of the source ID, sensor or version, and source timestamp or record. Every row also carries the SHA-256 of the raw file it came from. Daily means use Asia/Karachi local days and require at least 18 valid hours (the US EPA 75% completeness convention); otherwise the mean is left blank.

## Data Quality Agent

These are deterministic rules, with no LLM involved. They run inside `make data`, and every decision is written to the source's quality report and appended to its quality log with a reason and row count.

| Source | Checks (pass / warning / fail) | FIX | FILL | FLAG |
|---|---|---|---|---|
| PAQI | 11 / 4 / 0 | 305 (`22.0` → `22`; exact value kept in `source_value_raw`) | 6 missing days, not imputed | 12 |
| U.S. Consulate | 5 / 5 / 0 | 0 | 10,519 null hours and gap hours, not imputed | 13 decisions: 1 hour at 985 µg/m³ (BAM-1020 upper-limit/error value, excluded from daily means), 8 hours > 500 kept for review, 973 hours inside OpenAQ "limits exceeded" windows kept, 590 days below 18 valid hours |
| Urban Unit | 5 / 3 / 0 | 0 | 27,294 absent sensor-hours, not imputed | 6 hours > 500 kept for review, plus rules for frozen values (≥ 6 identical hours), hours with < 75% coverage, stale sensors (> 48 h) and the uncorrected low-cost-sensor caveat |

FILL is never applied: the agent will not invent exposure. Critical problems fail the run with a nonzero exit:
- schema change
- conflicting duplicates
- a raw file whose SHA-256 no longer matches its sidecar
- a changed licence or provider

## Model

The target is the next-day PAQI value. The model is ordinary least squares on exact 1-, 2- and 7-day lags. The declared baseline is persistence (the latest prior valid reading). Splits are chronological and frozen: train 2016-10-06 → 2022-07-12, validation 2022-07-13 → 2023-10-06, test 2023-10-07 → 2024-12-31.

| Held-out test (n = 436) | MAE µg/m³ | RMSE µg/m³ |
|---|---|---|
| Linear model | **9.90** | **16.33** |
| Persistence | 10.15 | 16.94 |

The model has about 2.5% lower MAE. No significance test is claimed. **Uncertainty:** an empirical interval from the validation residuals' 5th–95th percentiles (−23.8 to +29.5 µg/m³) covers 91.5% of test days (399 of 436). **Errors by group** (test split, model vs persistence MAE):

| Group | n | Model | Persistence |
|---|---|---|---|
| Winter (Dec–Feb) | 106 | 17.46 | 18.63 |
| Pre-monsoon (Mar–May) | 92 | 7.19 | 7.55 |
| Monsoon (Jun–Sep) | 122 | 3.56 | 3.22 |
| Post-monsoon (Oct–Nov) | 116 | 11.81 | 11.75 |
| Previous day ≤ 35 µg/m³ | 235 | 4.54 | 4.43 |
| Previous day 35–75 µg/m³ | 97 | 13.29 | 13.35 |
| Previous day > 75 µg/m³ | 104 | 18.86 | 20.10 |

The gain comes from polluted winter days. On clean monsoon days, persistence is slightly better. All figures are in `data/reports/forecast_metrics.json`. This is a historical backtest; the model is not run as a live forecast.

## Insight Agent (RAG) and generative layer

`python -m pipeline.insight_agent "Do PAQI and the US Consulate monitor agree?"` (or the dashboard chat widget).

1. **Retrieval and facts (deterministic).** The agent routes the question and computes every number at query time from the gold tables and reports. It returns `answer`, `status` (`answered`, `partially_answered` or `abstained`), `evidence` (file, locator, values, row IDs), `limitations` and `data_as_of`. It abstains on causal questions ("did traffic cause…"), off-topic questions, and anything else the evidence cannot answer. For "current air quality" it reports the latest warehouse hour across the Urban Unit sensors, and explicitly refuses a citywide index.
2. **Generative explanation (optional).** `pipeline/llm_explainer.py` sends only the verified answer, its evidence and limitations to an LLM. The LLM rewrites them in plain English or Urdu with `[E1]` citations. The output is **discarded** if it contains any number not present in the evidence (Urdu digits are normalised first), drops the required "I don't know based on the available evidence.", cites evidence that doesn't exist, or runs too long. Set `GEMINI_API_KEY` (Gemini 3.5 Flash-Lite) or `GROQ_API_KEY`, or `LLM_API_KEY` + `LLM_API_BASE` + `LLM_MODEL` for any OpenAI-compatible provider. Without a key, nothing is sent and the deterministic answer is shown.

## Automation, dashboard and Space

- **Hourly flow:** `.github/workflows/hourly-pipeline.yml` runs at minute 7 of every hour. It runs the unit tests and then the Prefect flow in `prefect_flow.py` (warehouse + quality agents, then forecast evaluation). It commits the refreshed gold, report files and `prefect_runs.csv`. Prefect state hooks append one row per flow run, including failed runs, with the Prefect flow-run ID. Nobody edits that file by hand. Add `PREFECT_API_URL` and `PREFECT_API_KEY` repository secrets to also see the runs in Prefect Cloud.
- **Dashboard** (`python -m pipeline.dashboard`, deployed on Render via `render.yaml`) shows:
  - data freshness for each source
  - quality status
  - the cross-source agreement
  - forecast evaluation
  - the Insight Agent
  - the live AirGradient cards
- **Hugging Face Space** (`app.py`, Gradio) shows the Insight Agent, the last and last-successful Prefect run, per-source freshness and quality status.

## Limitations

- PAQI does not publish its monitor set, day boundary or QA procedure. These remain flagged in its quality report.
- The U.S. Consulate monitor stopped publishing on 2025-03-04, so it serves as a historical reference series.
- The Urban Unit sensors are uncorrected low-cost optical sensors. A median of a few sensors is not a citywide or regulatory value.
- Outputs are informational, not medical or regulatory advice.
