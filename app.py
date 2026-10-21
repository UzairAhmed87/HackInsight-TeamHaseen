#!/usr/bin/env python3
"""
Hugging Face Space App
Wraps the dashboard server for HF Spaces deployment
"""

import os
import sys
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import dashboard

if __name__ == "__main__":
    # HF Spaces provides PORT environment variable
    port = int(os.environ.get("PORT", 7860))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"🚀 Starting HackInsight Dashboard on {host}:{port}")
    print(f"📊 Data warehouse: {Path('data/processed/gold_air_quality.csv').exists()}")
    print(f"✅ Quality report: {Path('data/quality/quality_report.json').exists()}")
    print(f"🔄 Pipeline log: {Path('prefect_runs.csv').exists()}")
    
    # Start the dashboard server
    dashboard.main(["--host", host, "--port", str(port)])
