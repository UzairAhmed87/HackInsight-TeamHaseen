"""
Demo Video Script for HackInsight Air Quality Pakistan
Duration: 3 minutes max
Hackathon Submission - Air Quality Track
"""

# ============================================================================
# DEMO VIDEO SCRIPT - 3 MINUTES
# ============================================================================

## SECTION 1: PROBLEM & SOLUTION (30 seconds)
"""
[Screen: Dashboard homepage]

"Hi! This is HackInsight - an automated air quality intelligence system for Pakistan.

Air pollution is a critical health crisis. But existing data is scattered, 
unreliable, and hard to trust. 

We built a journal-quality data warehouse with automated quality monitoring, 
forecasting, and an AI agent that never invents facts.

Let me show you how it works."
"""

## SECTION 2: DATA WAREHOUSE (45 seconds)
"""
[Screen: Terminal showing `make data`]

"Everything starts with traceable, licensed data. We use 2 independent sources:
PAQI's historical dataset from Zenodo, and live AirGradient sensors.

Watch this: one command rebuilds the entire warehouse.

[Run: make data]

[Screen: File explorer showing data/raw, data/cleaned, data/processed]

Raw data stays untouched. Cleaned data is normalized. 
And gold data has SHA-256 row-level lineage.

Every observation is traceable to its original source."
"""

## SECTION 3: DATA QUALITY AGENT (45 seconds)
"""
[Screen: data/quality/quality_report.json]

"Here's our Data Quality Agent in action. It's deterministic - no black box.

[Scroll through quality_report.json]

It checks 15+ validation rules: schema, dates, duplicates, missing values.

[Screen: data/quality/quality_log.csv]

Every decision is logged: fix, fill, or flag. With the reason.

[Highlight example rows]

See? 305 fixes for trailing decimals. 6 missing values flagged - never invented.

This is journal-quality validation."
"""

## SECTION 4: FORECASTING MODEL (30 seconds)
"""
[Screen: Dashboard forecast section]

"Our linear regression model beats the persistence baseline.

[Point to metrics]

Time-based splits: train, validation, test. No data leakage.

[Point to uncertainty intervals]

Uncertainty intervals from validation residuals. 

[Point to yearly breakdown]

Errors broken down by year. Full transparency."
"""

## SECTION 5: INSIGHT AGENT (RAG) (30 seconds)
"""
[Screen: Dashboard chat widget]

"Now the magic: our Insight Agent.

[Type: "How many missing PM2.5 readings?"]

It answers with citations. From gold data only.

[Show response with evidence references]

[Type: "What's the current citywide AQI?"]

Watch this: it says "I don't know" when data doesn't support it.

No hallucinations. Evidence-grounded only."
"""

## SECTION 6: AUTOMATION & FRESHNESS (20 seconds)
"""
[Screen: GitHub Actions workflow]

"Everything runs automatically. Every hour.

[Show: .github/workflows/hourly-pipeline.yml]

GitHub Actions triggers the pipeline. 

[Screen: prefect_runs.csv]

Every run is logged. Status, row counts, quality metrics.

[Point to dashboard freshness indicator]

Dashboard shows data freshness and last successful run."
"""

## SECTION 7: UI & FEATURES (20 seconds)
"""
[Screen: Dashboard - toggle dark mode]

"Modern UI with dark mode. WCAG AAA contrast.

[Show calendar heatmap]

Calendar heatmap for daily patterns.

[Click export buttons]

Export data as CSV or charts as PNG.

[Show keyboard shortcuts]

Keyboard shortcuts for power users.

Professional, not 'vibe coded'."
"""

## SECTION 8: COMPLIANCE & WRAP-UP (20 seconds)
"""
[Screen: README or checklist]

"Let's verify hackathon requirements:

✅ 2 independent sources
✅ Traceable, licensed data  
✅ Quality Agent with fix/fill/flag
✅ Model beats baseline with uncertainty
✅ RAG Agent with citations
✅ Hourly automation
✅ Hugging Face Space

[Screen: Repository]

Full code on GitHub. Tag v1.0-final.

Journal-quality data. Automated pipeline. Trustworthy insights.

That's HackInsight. Thank you!"
"""

# ============================================================================
# RECORDING TIPS
# ============================================================================

"""
BEFORE RECORDING:
1. Clear browser cache and restart dashboard
2. Test all demo flows once
3. Prepare example questions for Insight Agent
4. Have terminal commands ready in history
5. Set screen resolution to 1920x1080
6. Close unnecessary apps/notifications
7. Test microphone and screen recording

DURING RECORDING:
- Speak clearly and confidently
- Use cursor highlights or zoom for important details
- Keep a steady pace (not rushed)
- Show real outputs, not mockups
- Demonstrate actual functionality

EDITING:
- Add title card with team name
- Add section titles/transitions
- Highlight key metrics with text overlays
- Speed up long waits (2x)
- Add background music (subtle)
- Export at 1080p, 30fps
- Keep under 3 minutes (aim for 2:45)

FILE NAMING:
- hackinsight_demo_v1.0.mp4
- Upload to Google Drive or YouTube (unlisted)
- Add link to README and submission form
"""

# ============================================================================
# ALTERNATIVE: 2-MINUTE FAST VERSION
# ============================================================================

"""
If 3 minutes is too long, here's a 2-minute version:

1. Problem (15s): Air quality crisis, need trustworthy data
2. Warehouse (30s): 2 sources, make data, lineage
3. Quality Agent (30s): 15 checks, fix/fill/flag, logged
4. Model + RAG (30s): Beats baseline, cited answers, no hallucinations
5. Automation (15s): Hourly pipeline, logged runs
6. Wrap-up (10s): ✅ All requirements, GitHub, HF Space

Total: 2:10
"""
