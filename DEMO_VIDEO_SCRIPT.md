# Demo video script (≤ 3 minutes) and viva notes

Record the screen at 1080p on the Render dashboard (or the Space) with a terminal beside it. Every number below is on screen; read it from there, not from this script, in case the hourly run has updated it.

## 0:00–0:20 Problem and user
"Karachi residents, and the school heads, clinics and journalists who advise them, need to know how polluted the air is without being misled. Most public numbers come with no source, no quality check, and no 'we don't know'."

## 0:20–0:55 Data: three publishers, one command
- Terminal: run `make data` (it reuses cached raw files, so it takes about 10 s). Point at the `two_source_compliance: established` line and the total of 115,146 gold rows.
- Dashboard → Sources: PAQI (Zenodo DOI, CC BY 4.0), U.S. Consulate Karachi monitor (US Public Domain), Urban Unit AirGradient sensors (CC BY 4.0).
- "PAQI and the Consulate monitor agree, r = 0.87 over 1,399 days, and the 63 days where they disagree are flagged rather than deleted."

## 0:55–1:30 Data Quality Agent
- Open `data/quality/us_consulate_quality_report.json` → `decision_log`.
- "10,519 hours have no value. The agent logs FILL: not applied, because filling them would invent exposure. One hour reads exactly 985, the instrument's error value, so it is excluded from daily averages. Every decision is logged with a reason and a row count."

## 1:30–2:00 Model
- Dashboard → Forecast. "Linear model 9.90 vs persistence 10.15 MAE on 436 held-out days. The interval covers 91.5% of test days. The gain is on polluted winter days (17.46 vs 18.63). On clean monsoon days persistence is slightly better, and we report that."

## 2:00–2:40 Insight Agent
Ask three questions in the chat widget:
1. "What is the current air quality in Karachi?" The agent gives the latest hour across the sensors, cites the evidence, and refuses a citywide index.
2. "Did traffic cause the PM2.5 increase?" It answers "I don't know based on the available evidence."
3. Switch to اردو and ask "Do PAQI and the US Consulate monitor agree?" Show the plain-language explanation next to the verified answer. (This needs `GEMINI_API_KEY`; otherwise show the guardrail test `python -m unittest tests.test_llm_explainer -v`.)

## 2:40–3:00 Automation
- GitHub → Actions → "Hourly Data Pipeline": a list of green hourly runs. Open `prefect_runs.csv` and point at a flow-run ID, its state, and the last successful run.
- "Rebuilt every hour, logged by Prefect, and every number in this video comes from those files."

## Viva notes: likely questions
- **Why OpenAQ if it's an aggregator?** It is only the access route. The original publishers are the U.S. State Department/AirNow and the Urban Unit. Licence and provider are read from OpenAQ metadata on every run, and the run fails if they change.
- **Are PAQI and the Consulate independent?** They come from different publishers. PAQI doesn't publish its monitor list, so we measure agreement (r = 0.87) instead of assuming independence.
- **Why not impute missing hours?** Imputed values would be invented exposure. Daily means need at least 18 valid hours (US EPA 75% rule).
- **Why is the model so close to persistence?** Daily PM2.5 is highly autocorrelated. We report the 2.5% gain honestly, show where it helps (winter, polluted days) and where it doesn't (monsoon), and claim no significance.
- **What stops the LLM from hallucinating?** It never sees raw data. It only rewrites the verified answer, and code rejects any output containing a number that isn't in the evidence, missing the required abstention, or citing evidence that doesn't exist. Tests: `tests/test_llm_explainer.py`.
- **Where does the hourly data come from?** The Urban Unit sensors via OpenAQ. The current month's raw file is re-fetched each hour; completed months are frozen with SHA-256 sidecars.
