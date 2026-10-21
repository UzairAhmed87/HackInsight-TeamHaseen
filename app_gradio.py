#!/usr/bin/env python3
"""
Hugging Face Space App - Gradio Wrapper (FREE TIER)
Wraps the existing dashboard for HF Spaces using Gradio SDK
"""

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
        result = insight_agent.answer_question(question, format_type='json')
        return result
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
        
        if 'evidence' in response:
            output += "**Evidence:**\n"
            for key, val in response['evidence'].items():
                output += f"- {key}: {val}\n"
        
        if 'limitations' in response and response['limitations']:
            output += f"\n**Limitations:** {response['limitations']}\n"
        
        return output
    return str(response)

def get_pipeline_status():
    """Get the latest pipeline run status"""
    if PIPELINE_RUNS.exists():
        try:
            with open(PIPELINE_RUNS, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_run = lines[-1].strip()
                    return f"**Latest Pipeline Run:**\n```\n{last_run}\n```"
        except:
            pass
    return "Pipeline runs log not available"

def get_quality_summary():
    """Get quality report summary"""
    if QUALITY_REPORT.exists():
        try:
            with open(QUALITY_REPORT, 'r') as f:
                report = json.load(f)
                
            summary = "**Data Quality Summary:**\n\n"
            
            # Overall status
            if 'overall_status' in report:
                summary += f"- **Status:** {report['overall_status']}\n"
            
            # Decision counts
            if 'decision_counts' in report:
                counts = report['decision_counts']
                summary += f"- **Fix:** {counts.get('fix', 0)} decisions\n"
                summary += f"- **Fill:** {counts.get('fill', 0)} decisions\n"
                summary += f"- **Flag:** {counts.get('flag', 0)} decisions\n"
            
            # Severity breakdown
            if 'severity_breakdown' in report:
                severity = report['severity_breakdown']
                summary += f"\n**Severity:**\n"
                for level, count in severity.items():
                    summary += f"- {level}: {count}\n"
            
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
    - 📈 Forecasting model (beats baseline by 15%)
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
            - ✅ MAE: 15.4 vs 18.2 (15% improvement)
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
            - **Model Performance:** 15% better than baseline
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
