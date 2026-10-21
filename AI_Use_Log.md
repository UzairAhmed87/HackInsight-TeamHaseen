# AI Use Log — HackInsight '26, Team Haseen

All data in this project comes from the original publishers named in `README.md`. No AI tool generated, edited or imputed any observation used for training, evaluation or display. Tests use small synthetic **software fixtures** that never enter the warehouse.

## Tools

| Tool | Used for |
|---|---|
| Cursor (AI coding agent; Claude models) | Writing and refactoring pipeline code, tests, dashboard UI, workflow files and documentation, and running the pipeline and tests |
| ChatGPT | Early planning: track comparison and source search |
| Optional runtime LLM (`pipeline/llm_explainer.py`, Gemini or Groq when a key is configured) | Rephrasing the Insight Agent's verified answer in plain English or Urdu. Output is discarded if it adds any number not in the cited evidence |

## Material uses, in order

| When (2026) | What the AI did | How we checked it |
|---|---|---|
| Oct 18–19 | Researched candidate sources and drafted `docs/dataset_research.md`, `docs/feasibility_decision.md` and `docs/source_register.csv` | Every licence and URL was opened and verified against the publisher page; unverified candidates stay marked UNVERIFIED |
| Oct 19–20 | Wrote the PAQI pipeline (`pipeline/run.py`), Data Quality Agent, forecasting backtest, deterministic Insight Agent and dashboard | 60 unit tests; metrics were read from `data/reports/forecast_metrics.json`, not from AI text |
| Oct 20 | Generated status, business-model and checklist documents | **Problem found:** these contained invented or wrong figures (for example a 15.4 vs 18.2 MAE claim, "Lighthouse 65 → 92", "2 independent sources (PAQI + AirGradient)" before a second source existed). The real values were 9.90 vs 10.15 MAE and one source. The files were corrected, then deleted on Oct 21 |
| Oct 21 | Replaced a script that wrote a fake run log with a real Prefect flow; fixed the GitHub Actions push permission (the run had failed with HTTP 403) | Ran the flow locally; checked each `prefect_runs.csv` field against the reports |
| Oct 21 | Found and added the U.S. Consulate Karachi monitor and the Urban Unit network via OpenAQ, with their quality rules | Licence and provider are read from OpenAQ metadata every run. Rules were chosen after profiling the real data (10,519 null hours; one 985 µg/m³ BAM error value). Cross-source r = 0.87 was computed by the pipeline |
| Oct 21 | Added the guardrailed LLM explanation layer, forecast errors by season and pollution level, and rewrote the README, Space card, summary and this log | Guardrail unit tests reject invented numbers, missing abstentions and fake citations. All figures in the docs were copied from pipeline outputs |

## What the AI was not allowed to do

- Produce or alter data values, metrics or quality counts. These are computed by code and read from artifacts.
- Make the Insight Agent's facts. Retrieval and every number are deterministic; the optional LLM only rephrases text that has already been checked.
- Claim compliance that the artifacts don't show.

## Human responsibility

The team reviewed the code and is responsible for explaining every part of it in the viva. Team members: Muhammad Taha Farrukh, Muhammad Bilal Rasheed, Muhammad Uzzam Siddiqui, Uzair Ahmed.
