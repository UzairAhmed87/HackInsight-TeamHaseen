---
title: HackInsight Air Quality Pakistan
emoji: 🌍
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.50.0"
python_version: "3.12"
app_file: app.py
pinned: false
license: cc-by-4.0
tags:
  - air-quality
  - pakistan
  - data-pipeline
  - forecasting
  - rag
---

# HackInsight '26 — Karachi Air Quality (Team Haseen)

This Space shows the Insight Agent, data freshness per source, quality status, and the last successful hourly Prefect run. Every number shown is read from the pipeline artifacts committed by the hourly flow.

- **Code and full documentation:** https://github.com/UzairAhmed87/HackInsight-TeamHaseen (tag `v1.0-final`)
- **Full dashboard:** https://hackinsight-air-quality-pakistan.onrender.com/

## Data (115,146 gold rows)

| Source | Licence | Rows |
|---|---|---|
| PAQI Karachi daily PM2.5, [DOI 10.5281/zenodo.15845428](https://doi.org/10.5281/zenodo.15845428) | CC BY 4.0 | 3,009 days, 2016–2024 |
| U.S. Consulate General Karachi monitor (AirNow via OpenAQ location 8156) | US Public Domain | 46,937 hours, 2019–2025 |
| The Urban Unit AirGradient network, 8 sensors (via OpenAQ) | CC BY 4.0 | 65,200 hours, since 2025-06, refreshed hourly |

PAQI and the Consulate monitor agree with Pearson r = 0.87 over 1,399 shared days.

## What to try

- *What is the current air quality in Karachi?* The agent gives the latest warehouse hour across the sensors and refuses to give a citywide index.
- *Do PAQI and the US Consulate monitor agree?*
- *How did the model compare with persistence on the held-out test set?* Linear MAE 9.90 vs persistence 10.15 µg/m³, n = 436.
- *Did traffic cause the PM2.5 increase?* The agent answers "I don't know based on the available evidence."

## Optional generative explanations

Add a `GEMINI_API_KEY` (or `GROQ_API_KEY`) secret in the Space settings. The LLM then rewrites the verified answer in English or Urdu. Its output is discarded if it contains any number that is not in the cited evidence.

Attribution: PAQI (Omar Abid, Dawar Hameed Butt, Mahad Naveed), CC BY 4.0; U.S. Department of State / U.S. EPA AirNow; The Urban Unit / AirGradient, CC BY 4.0; accessed via OpenAQ. Informational only; not medical advice.
