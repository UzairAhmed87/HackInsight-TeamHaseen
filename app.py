#!/usr/bin/env python3
"""
Hugging Face Space App - Gradio Wrapper (FREE TIER)
Wraps the existing dashboard for HF Spaces using Gradio SDK
"""

import csv
import gradio as gr
import sys
from pathlib import Path
import json

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))

# Import dashboard components
try:
    from pipeline import insight_agent
    from pathlib import Path
    
    # Load data artifacts
    GOLD_DATA = Path("data/processed/gold_air_quality.csv")
    QUALITY_REPORT = Path("data/quality/quality_report.json")
    EXECUTION_STATUS = Path("data/reports/execution_status.json")
    FORECAST_METRICS = Path("data/reports/forecast_metrics.json")
    PIPELINE_RUNS = Path("prefect_runs.csv")
    
    data_available = all([
        GOLD_DATA.exists(),
        QUALITY_REPORT.exists(),
        EXECUTION_STATUS.exists(),
        FORECAST_METRICS.exists()
    ])
except Exception as e:
    data_available = False
    print(f"⚠️ Warning: {e}")

def get_dashboard_html():
    """Load the dashboard HTML"""
    dashboard_path = Path("dashboard/index.html")
    if dashboard_path.exists():
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "<h1>Dashboard not found</h1>"

def ask_insight_agent(question):
    """Query the Insight Agent"""
    if not data_available:
        return {
            "answer": "Data artifacts not available. Please run the data pipeline first.",
            "status": "error",
            "generated_at": None
        }
    
    try:
        # Call the insight agent
        if not question or not question.strip():
            return {"answer": "Please type a question.", "status": "error"}
        return insight_agent.answer_question(question)
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "status": "error",
            "generated_at": None
        }

def format_agent_response(response):
    """Format the agent response for display"""
    if isinstance(response, dict):
        answer = response.get('answer', 'No answer')
        status = response.get('status', 'unknown')
        
        # Format nicely
        output = f"**Answer:** {answer}\n\n"
        output += f"**Status:** {status}\n\n"
        
        evidence = response.get('evidence') or []
        if evidence:
            output += "**Evidence:**\n"
            for item in evidence:
                locator = item.get('locator') or item.get('operation') or item.get('kind', '')
                date_range = item.get('date_range')
                span = f" ({date_range['start']} → {date_range['end']})" if date_range else ""
                output += f"- `{item.get('source_file', '')}` — {locator}{span}\n"

        limitations = response.get('limitations') or []
        if limitations:
            output += "\n**Limitations:**\n"
            for item in (limitations if isinstance(limitations, list) else [limitations]):
                output += f"- {item}\n"

        if response.get('data_as_of'):
            output += f"\n_Data as of: {response['data_as_of']}_\n"
        
        return output
    return str(response)

def get_pipeline_status():
    """Get the latest pipeline run status"""
    if PIPELINE_RUNS.exists():
        try:
            with open(PIPELINE_RUNS, newline='') as f:
                runs = list(csv.DictReader(f))
        except (OSError, csv.Error):
            runs = []
        if runs:
            latest = runs[-1]
            successful = [r for r in runs if r.get('status', '').startswith('success')]
            text = f"**Total logged runs:** {len(runs)}\n\n"
            text += f"**Latest run:** {latest.get('timestamp')} — `{latest.get('status')}`\n\n"
            if successful:
                last_ok = successful[-1]
                text += f"**Last successful run:** {last_ok.get('timestamp')} ({last_ok.get('records_processed')} records, {last_ok.get('duration_seconds')}s)\n"
            return text
    return "Pipeline runs log not available"

def get_quality_summary():
    """Get quality report summary"""
    if QUALITY_REPORT.exists():
        try:
            with open(QUALITY_REPORT, 'r') as f:
                report = json.load(f)
                
            agent = report.get('data_quality_agent', {})
            counts = agent.get('counts', {})

            summary = "**Data Quality Summary:**\n\n"
            summary += f"- **Quality status:** {report.get('quality_status', agent.get('status', 'unknown'))}\n"
            summary += f"- **Agent status:** {agent.get('status', 'unknown')}\n"
            summary += f"- **Checks:** {counts.get('passed_checks', 0)} passed, {counts.get('warning_checks', 0)} warnings, {counts.get('failed_checks', 0)} failed\n"
            summary += f"- **FIX:** {counts.get('fixes', 0)} · **FILL** (not applied): {counts.get('fills_not_applied', 0)} · **FLAG:** {counts.get('flags', 0)}\n"
            summary += "\n**Data Freshness:**\n\n"
            summary += f"- **Observations:** {report.get('first_observation_date')} → {report.get('last_observation_date')} ({report.get('gold_record_count')} gold rows)\n"
            summary += f"- **Latest observation age:** {agent.get('source_age_days')} days\n"
            summary += f"- **Last quality check:** {agent.get('checked_at_utc')}\n"
            return summary
        except Exception as e:
            return f"Error loading quality report: {e}"
    return "Quality report not available"

# Create Gradio Interface
with gr.Blocks(title="HackInsight Air Quality Pakistan", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🌍 HackInsight Air Quality Pakistan
    
    **Automated air quality intelligence system with:**
    - 📊 Journal-quality data warehouse (2 independent sources)
    - ✅ Automated quality monitoring (15 validation rules)
    - 📈 Forecasting model (beats persistence: 9.90 vs 10.15 test MAE)
    - 🤖 Evidence-grounded RAG Insight Agent
    
    **GitHub:** [UzairAhmed87/HackInsight-TeamHaseen](https://github.com/UzairAhmed87/HackInsight-TeamHaseen)
    """)
    
    with gr.Tabs():
        # Tab 1: Insight Agent
        with gr.Tab("💬 Insight Agent"):
            gr.Markdown("""
            ### Ask the Evidence-Grounded AI Agent
            
            The agent answers questions using **only gold data** and **cites sources**.
            It says **"I don't know"** when data doesn't support the question.
            
            **Try asking:**
            - How many PM2.5 readings are missing?
            - What's the average PM2.5 level in the dataset?
            - How did the model compare with persistence?
            - What's the data coverage period?
            """)
            
            with gr.Row():
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="How many missing PM2.5 readings?",
                    lines=2
                )
            
            ask_button = gr.Button("Ask Agent 🤖", variant="primary")
            
            answer_output = gr.Markdown(label="Agent Response")
            
            ask_button.click(
                fn=lambda q: format_agent_response(ask_insight_agent(q)),
                inputs=question_input,
                outputs=answer_output
            )
            
            # Example questions
            gr.Examples(
                examples=[
                    ["How many PM2.5 readings are missing?"],
                    ["What's the average PM2.5 level in the dataset?"],
                    ["How did the model compare with persistence on the test set?"],
                    ["What's the data coverage period?"],
                    ["What's the current citywide Karachi AQI?"]  # Should say "I don't know"
                ],
                inputs=question_input
            )
        
        # Tab 2: Pipeline Status
        with gr.Tab("⚙️ Pipeline Status"):
            gr.Markdown("### Automated Hourly Pipeline")
            
            pipeline_status = gr.Markdown(get_pipeline_status())
            quality_status = gr.Markdown(get_quality_summary())
            
            refresh_button = gr.Button("🔄 Refresh Status")
            refresh_button.click(
                fn=lambda: (get_pipeline_status(), get_quality_summary()),
                outputs=[pipeline_status, quality_status]
            )
        
        # Tab 3: Project Info
        with gr.Tab("📖 About"):
            gr.Markdown("""
            ## Project Overview
            
            ### 🎯 Hackathon Track: Air Quality
            **Team:** TeamHaseen
            
            ### ✅ Requirements Met
            
            **1. Data Warehouse**
            - ✅ 2 independent sources (PAQI + AirGradient)
            - ✅ Raw/cleaned/processed layers
            - ✅ SHA-256 row-level lineage
            - ✅ Rebuild with: `make data`
            
            **2. Data Quality Agent**
            - ✅ 15+ validation rules
            - ✅ Fix/fill/flag decisions logged
            - ✅ Deterministic (no LLM)
            
            **3. Forecasting Model**
            - ✅ Linear regression beats persistence baseline
            - ✅ Test MAE: 9.90 vs 10.15 µg/m³ (persistence)
            - ✅ Time-based train/val/test splits
            - ✅ Uncertainty quantification
            
            **4. Insight Agent (RAG)**
            - ✅ Cites evidence sources
            - ✅ Says "I don't know" when unsupported
            - ✅ Numbers only from gold tables
            
            **5. Automation**
            - ✅ Hourly GitHub Actions pipeline
            - ✅ Logged to prefect_runs.csv
            - ✅ Shows freshness/quality/last run
            
            ### 📊 Key Metrics
            - **Data Points:** 3,009 daily observations
            - **Coverage:** 8+ years (2016-2024)
            - **Quality Checks:** 15 validation rules
            - **Model Performance:** about 2.5% lower test MAE than persistence
            - **Automation:** 24 runs/day
            - **Cost:** $0/month
            
            ### 🔗 Links
            - **GitHub:** [UzairAhmed87/HackInsight-TeamHaseen](https://github.com/UzairAhmed87/HackInsight-TeamHaseen)
            - **Tag:** v1.0-final
            - **Full Dashboard:** See repository for complete UI
            
            ### 📄 License
            - **Data:** CC BY 4.0 (PAQI)
            - **Attribution:** Omar Abid, Dawar Hameed Butt, Mahad Naveed, PAQI
            """)
    
    gr.Markdown("""
    ---
    **Built for HackInsight '26 Hackathon** | Air Quality Track | Journal-Quality Dataset
    """)

# Launch the app
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
