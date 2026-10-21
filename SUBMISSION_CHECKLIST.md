# Submission checklist — HackInsight '26, Team Haseen

Status as of 2026-10-21. "Evidence" points to the file a judge can open.

## Requirements

| Requirement | Status | Evidence |
|---|---|---|
| ≥ 2 independent sources from credible original publishers | Done: 3 sources | `README.md` sources table, `data/quality/warehouse_quality_report.json` |
| ≥ 1 credible source not on the track list | **Team to confirm** against the official track list (U.S. Consulate / AirNow and Urban Unit are the candidates) | `config/openaq_*.json` |
| Publisher, URL/DOI and licence for every source | Done | `README.md`, `docs/source_register.csv`, each `*_quality_report.json` |
| No synthetic or personal data; terms and robots respected | Done: public monitor data only; OpenAQ API used with a key and rate-limited (1.1 s between requests) | `pipeline/us_consulate.py`, `pipeline/urban_unit.py` |
| Raw, cleaned, processed layers rebuilt with `make data` | Done | `Makefile`, `pipeline/warehouse.py` |
| Data Quality Agent: validates, decides FIX/FILL/FLAG, explains each | Done for all three sources | `data/quality/*_quality_report.json`, `quality_log.csv` files |
| Model beats a declared baseline, with uncertainty and errors by group | Done: MAE 9.90 vs 10.15; 91.5% interval coverage; errors by year, season and prior-day level | `data/reports/forecast_metrics.json` |
| Insight Agent: cited answers; says "I don't know" when unsupported | Done; optional guardrailed LLM layer | `pipeline/insight_agent.py`, `pipeline/llm_explainer.py`, `tests/` |
| Hourly flow | Done in code; **needs the `OPENAQ_API_KEY` repo secret** and the PR merged to `main` before the hourly schedule runs | `.github/workflows/hourly-pipeline.yml`, `prefect_flow.py` |
| Space showing freshness, quality status and last successful run | `app.py` ready; **Space needs to be pushed and running** | `app.py`, `README_HF.md` |

## Deliverables

| Deliverable | Status |
|---|---|
| GitHub repo at the `v1.0-final` commit | Move the tag to the final commit after merge (`git tag -f v1.0-final && git push -f origin v1.0-final`) |
| Hugging Face Space link | Pending upload |
| `prefect_runs.csv` (unedited) with screenshot | Written by the hourly flow; collect it and a screenshot of the Actions or Prefect run list after a few hourly runs |
| One-page `Summary.pdf` | Regenerated from `docs/Summary.md` |
| Demo video ≤ 3 minutes | Script in `DEMO_VIDEO_SCRIPT.md`; recording pending |
| `AI_Use_Log.md` | Done |
| Physical viva | Talking points in `DEMO_VIDEO_SCRIPT.md` |
