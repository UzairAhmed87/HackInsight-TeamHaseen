"""
Prefect Flow for HackInsight Air Quality Pipeline
Runs data acquisition, quality checks, and model evaluation hourly
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import json
from prefect import flow, task

@task(name="fetch_and_validate_data", retries=2, retry_delay_seconds=30)
def fetch_and_validate_data():
    """Fetch data from sources and validate"""
    print("🔄 Running data pipeline...")
    result = subprocess.run(
        [sys.executable, "-m", "pipeline.run"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if result.returncode != 0:
        print(f"❌ Pipeline failed: {result.stderr}")
        raise Exception(f"Data pipeline failed: {result.stderr}")
    
    print(f"✅ Pipeline completed successfully")
    
    # Parse execution status
    status_file = Path("data/reports/execution_status.json")
    if status_file.exists():
        with open(status_file) as f:
            status = json.load(f)
        return status
    return None

@task(name="check_data_quality")
def check_data_quality(status):
    """Verify data quality meets thresholds"""
    print("🔍 Checking data quality...")
    
    if not status:
        raise Exception("No status available")
    
    # Check quality metrics
    quality_status = status.get("quality_status", "unknown")
    if quality_status == "failed":
        raise Exception("Data quality checks failed")
    
    # Read quality report
    quality_file = Path("data/quality/quality_report.json")
    if quality_file.exists():
        with open(quality_file) as f:
            quality = json.load(f)
        
        failed_checks = quality.get("counts", {}).get("failed_checks", 0)
        if failed_checks > 0:
            print(f"⚠️  {failed_checks} quality checks failed")
        else:
            print(f"✅ All quality checks passed")
        
        return quality
    
    return None

@task(name="run_forecasting")
def run_forecasting():
    """Run forecasting model and evaluation"""
    print("📊 Running forecasting model...")
    result = subprocess.run(
        [sys.executable, "-m", "pipeline.forecasting"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if result.returncode != 0:
        print(f"⚠️  Forecasting warning: {result.stderr}")
        # Don't fail on forecasting errors
        return None
    
    print("✅ Forecasting completed")
    
    # Parse forecast metrics
    metrics_file = Path("data/reports/forecast_metrics.json")
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)
        return metrics
    
    return None

@task(name="log_run_results")
def log_run_results(status, quality, forecast):
    """Log pipeline run results to CSV"""
    import csv
    from datetime import datetime
    
    log_file = Path("prefect_runs.csv")
    
    # Create file with headers if it doesn't exist
    if not log_file.exists():
        with open(log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'run_id',
                'status',
                'records_processed',
                'quality_status',
                'failed_checks',
                'warnings',
                'forecast_mae',
                'duration_seconds'
            ])
    
    # Append run data
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        
        timestamp = datetime.utcnow().isoformat() + 'Z'
        run_id = status.get('run_id', 'unknown') if status else 'unknown'
        status_str = status.get('status', 'unknown') if status else 'unknown'
        records = status.get('gold_record_count', 0) if status else 0
        
        quality_status = quality.get('pipeline_status', 'unknown') if quality else 'unknown'
        failed = quality.get('counts', {}).get('failed_checks', 0) if quality else 0
        warnings = quality.get('counts', {}).get('warning_checks', 0) if quality else 0
        
        mae = None
        if forecast and 'test' in forecast:
            mae = forecast['test'].get('linear_model', {}).get('mae')
        
        # Calculate duration (mock for now)
        duration = 0
        if status:
            start = datetime.fromisoformat(status.get('started_at_utc', '').replace('Z', ''))
            end = datetime.fromisoformat(status.get('finished_at_utc', '').replace('Z', ''))
            duration = (end - start).total_seconds()
        
        writer.writerow([
            timestamp,
            run_id,
            status_str,
            records,
            quality_status,
            failed,
            warnings,
            mae,
            duration
        ])
    
    print(f"✅ Logged run results to {log_file}")
    return str(log_file)

@flow(
    name="hackinsight-pipeline",
    description="Hourly air quality data pipeline with quality checks and forecasting"
)
def hackinsight_pipeline():
    """Main pipeline flow"""
    print("=" * 60)
    print("🚀 Starting HackInsight Air Quality Pipeline")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)
    
    # Step 1: Fetch and validate data
    status = fetch_and_validate_data()
    
    # Step 2: Check data quality
    quality = check_data_quality(status)
    
    # Step 3: Run forecasting
    forecast = run_forecasting()
    
    # Step 4: Log results
    log_file = log_run_results(status, quality, forecast)
    
    print("=" * 60)
    print("✅ Pipeline completed successfully!")
    print(f"📝 Results logged to: {log_file}")
    print("=" * 60)
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "log_file": log_file
    }

if __name__ == "__main__":
    # Run the flow
    result = hackinsight_pipeline()
    print(f"\n✅ Flow completed: {result}")
