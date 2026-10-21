#!/usr/bin/env python3
"""Hugging Face Space (Gradio SDK): Insight Agent, data freshness, quality status and last successful run.

Every number shown here is read from committed pipeline artifacts at request time.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline import insight_agent, llm_explainer  # noqa: E402

WAREHOUSE_REPORT = ROOT / "data" / "quality" / "warehouse_quality_report.json"
PAQI_QUALITY = ROOT / "data" / "quality" / "quality_report.json"
FORECAST_METRICS = ROOT / "data" / "reports" / "forecast_metrics.json"
PIPELINE_RUNS = ROOT / "prefect_runs.csv"
REPO_URL = "https://github.com/UzairAhmed87/HackInsight-TeamHaseen"


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def ask(question: str, language: str) -> str:
    if not question or not question.strip():
        return "Please type a question."
    try:
        result = insight_agent.answer_question(question)
    except (insight_agent.InsightAgentError, ValueError) as exc:
        return f"The Insight Agent could not access its evidence: {exc}"
    explanation = llm_explainer.explain(result, language="ur" if language.startswith("اردو") else "en")
    lines = []
    if explanation.get("used"):
        lines += [f"**Plain-language explanation** _(AI: {explanation['model']}, numbers checked against evidence)_",
                  "", explanation["text"], ""]
    lines += [f"**Verified answer** · `{result['status']}`", "", result["answer"], ""]
    if result.get("evidence"):
        lines.append("**Evidence**")
        for index, item in enumerate(result["evidence"], start=1):
            locator = item.get("locator") or item.get("operation") or item.get("kind", "")
            span = item.get("date_range")
            span_text = f" ({span['start']} → {span['end']})" if span else ""
            lines.append(f"- [E{index}] `{item.get('source_file', '')}` — {locator}{span_text}")
    if result.get("limitations"):
        lines += ["", "**Limitations**"] + [f"- {item}" for item in result["limitations"] if item]
    lines += ["", f"_Data as of {result.get('data_as_of')} · generated {result.get('generated_at')}_"]
    if not explanation.get("used") and explanation.get("reason") == "rejected_by_guardrail":
        lines.append("_An AI explanation was generated but discarded because it failed the evidence check._")
    return "\n".join(lines)


def pipeline_status() -> str:
    try:
        with PIPELINE_RUNS.open(encoding="utf-8", newline="") as stream:
            runs = list(csv.DictReader(stream))
    except OSError:
        runs = []
    if not runs:
        return "No Prefect runs logged yet (`prefect_runs.csv` is written by the hourly flow)."
    latest = runs[-1]
    completed = [run for run in runs if run.get("state") == "Completed"]
    text = [
        "### Hourly Prefect flow",
        f"- **Logged runs:** {len(runs)} ({len(completed)} completed, {len(runs) - len(completed)} not completed)",
        f"- **Latest run:** {latest.get('finished_at_utc')} — `{latest.get('state')}` ({latest.get('flow_run_name')})",
    ]
    if completed:
        last = completed[-1]
        text.append(
            f"- **Last successful run:** {last.get('finished_at_utc')} · {last.get('gold_rows')} gold rows · "
            f"quality `{last.get('quality_status')}` · {last.get('duration_seconds')} s"
        )
    return "\n".join(text)


def quality_and_freshness() -> str:
    warehouse = _json(WAREHOUSE_REPORT)
    paqi = _json(PAQI_QUALITY).get("data_quality_agent", {})
    test = _json(FORECAST_METRICS).get("splits", {}).get("test", {})
    lines = ["### Data freshness and quality"]
    for source in warehouse.get("sources", []):
        age = f" ({source['latest_age_hours']} h old at last run)" if source.get("latest_age_hours") is not None else ""
        lines.append(
            f"- **{source['publisher']}** — {source['license']}, {source['resolution']}, "
            f"{int(source.get('gold_rows') or 0):,} gold rows, latest `{source.get('latest_observation')}`{age}, "
            f"status `{source.get('status')}`"
        )
    if warehouse:
        lines.append(
            f"- **Warehouse:** {warehouse.get('total_gold_rows', 0):,} gold rows · two-source compliance "
            f"`{warehouse.get('two_source_compliance')}` · generated {warehouse.get('generated_at_utc')}"
        )
        cross = warehouse.get("cross_source", {})
        if cross.get("paired_days"):
            lines.append(
                f"- **Cross-source check:** PAQI vs U.S. Consulate on {cross['paired_days']:,} days, "
                f"Pearson r = {cross['pearson_r']}, mean difference {cross['mean_difference_paqi_minus_consulate']} µg/m³"
            )
    counts = paqi.get("counts", {})
    if counts:
        lines.append(
            f"- **PAQI Data Quality Agent:** {counts.get('passed_checks')} passed, {counts.get('warning_checks')} warnings, "
            f"{counts.get('failed_checks')} failed · FIX {counts.get('fixes')} · FLAG {counts.get('flags')}"
        )
    model, persistence = test.get("linear_model", {}), test.get("persistence_on_model_matched_targets", {})
    if model.get("mae") is not None:
        lines.append(
            f"- **Model (held-out test {test['dates']['start']} → {test['dates']['end']}):** linear MAE "
            f"{model['mae']:.2f} vs persistence {persistence.get('mae', float('nan')):.2f} µg/m³ (n = {model.get('n')})"
        )
    return "\n".join(lines)


with gr.Blocks(title="HaseenInsight Air Quality Pakistan", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# HaseenInsight Air Quality — Karachi\n"
        "Three-source PM2.5 warehouse (PAQI, U.S. Consulate Karachi, Urban Unit AirGradient network), "
        "a Data Quality Agent, a forecast evaluated against persistence, and an Insight Agent that cites its evidence "
        f"and says \"I don't know\" when the data cannot answer. Code: [{REPO_URL.split('/', 3)[3]}]({REPO_URL})"
    )
    with gr.Tab("Insight Agent"):
        question = gr.Textbox(label="Your question", placeholder="Do PAQI and the US Consulate monitor agree?", lines=2)
        language = gr.Radio(["English", "اردو (Urdu)"], value="English", label="Explanation language")
        button = gr.Button("Ask with evidence", variant="primary")
        answer = gr.Markdown()
        button.click(ask, inputs=[question, language], outputs=answer)
        question.submit(ask, inputs=[question, language], outputs=answer)
        gr.Examples(
            [
                ["What is the current air quality in Karachi?"],
                ["Do PAQI and the US Consulate monitor agree?"],
                ["How did the model compare with persistence on the held-out test set?"],
                ["How many PM2.5 readings are missing?"],
                ["Did traffic cause the PM2.5 increase?"],
            ],
            inputs=question,
        )
    with gr.Tab("Pipeline status"):
        status_md = gr.Markdown(pipeline_status())
        quality_md = gr.Markdown(quality_and_freshness())
        gr.Button("Refresh").click(lambda: (pipeline_status(), quality_and_freshness()), outputs=[status_md, quality_md])
    with gr.Tab("About"):
        gr.Markdown(
            "- **Sources and licences:** PAQI daily PM2.5 (Zenodo DOI 10.5281/zenodo.15845428, CC BY 4.0); "
            "U.S. Consulate General Karachi monitor via OpenAQ location 8156 (US Public Domain); "
            "The Urban Unit AirGradient sensors via OpenAQ (CC BY 4.0).\n"
            "- **Rebuild:** `make data` (raw → cleaned → gold for every source). Hourly: GitHub Actions runs the Prefect "
            "flow in `prefect_flow.py`, which appends to `prefect_runs.csv`.\n"
            "- **Generative AI:** optional; it only rephrases the verified answer and is discarded if it introduces any "
            "number not present in the cited evidence.\n"
            "- Informational only; not medical or regulatory advice."
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
