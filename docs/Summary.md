# HackInsight — Pakistan Air Quality Intelligence
**Team:** Haseen | **Track:** Air quality | **Demo:** https://hackinsight-air-quality-pakistan.onrender.com/

## Problem
Karachi needs trustworthy air-quality information that separates historical evidence, live neighbourhood sensors, and model backtests — without inventing citywide “current AQI.”

## What we built
1. **Historical warehouse** — PAQI Karachi daily PM2.5 (2016–2024), validated gold table, quality agent, reproducible pipeline.
2. **Live sensors** — public AirGradient / Urban Unit point readings (e.g. Gulistan-e-Johar); Orangi marked unavailable until API-verified.
3. **Forecast evaluation** — next-day linear model vs persistence on held-out 2023-10-07–2024-12-31 (MAE ≈ 9.90 vs 10.15 µg/m³). Historical backtest only.
4. **Insight Agent** — evidence-cited Q&A; abstains on citywide live claims; can report a live sensor reading with attribution.

## Honesty
No fabricated live numbers. LLM does not invent metrics. Outputs are informational, not medical advice.

## Repo
https://github.com/UzairAhmed87/HackInsight-TeamHaseen (tag coming: v1.0-final)