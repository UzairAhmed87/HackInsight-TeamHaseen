#!/usr/bin/env python3
"""
Automated Pipeline Runner for HackInsight
Runs data acquisition, quality checks, and forecasting
Logs all runs to prefect_runs.csv for hackathon submission
"""
import sys
import csv
import json
import subprocess
from pathlib import Path
from datetime import datetime
import time

class PipelineRunner:
    def __init__(self):
        self.log_file = Path("prefect_runs.csv")
        self.setup_log_file()
    
    def setup_log_file(self):
        """Create log file with headers if it doesn't exist"""
        if not self.log_file.exists():
            with open(self.log_file, 'w', newline='') as f:
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
            print(f"✅ Created {self.log_file}")
    
    def run_data_pipeline(self):
        """Run the data acquisition and quality check pipeline"""
        print("\n" + "="*60)
        print("🔄 Running Data Pipeline...")
        print("="*60)
        
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, "-m", "pipeline.run"],
            capture_output=True,
            text=True
        )
        duration = time.time() - start_time
        
        if result.returncode != 0:
            print(f"❌ Pipeline failed: {result.stderr}")
            return None, duration
        
        print("✅ Pipeline completed successfully")
        
        # Parse execution status
        status_file = Path("data/reports/execution_status.json")
        if status_file.exists():
            with open(status_file) as f:
                return json.load(f), duration
        
        return None, duration
    
    def check_quality(self):
        """Check data quality metrics"""
        print("\n🔍 Checking Data Quality...")
        
        quality_file = Path("data/quality/quality_report.json")
        if not quality_file.exists():
            print("⚠️  Quality report not found")
            return None
        
        with open(quality_file) as f:
            quality = json.load(f)
        
        failed = quality.get("counts", {}).get("failed_checks", 0)
        warnings = quality.get("counts", {}).get("warning_checks", 0)
        
        if failed > 0:
            print(f"⚠️  {failed} quality checks failed")
        else:
            print(f"✅ All quality checks passed")
        
        if warnings > 0:
            print(f"⚠️  {warnings} warning checks")
        
        return quality
    
    def run_forecasting(self):
        """Run forecasting model"""
        print("\n📊 Running Forecasting Model...")
        
        result = subprocess.run(
            [sys.executable, "-m", "pipeline.forecasting"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"⚠️  Forecasting warning: {result.stderr}")
            return None
        
        print("✅ Forecasting completed")
        
        metrics_file = Path("data/reports/forecast_metrics.json")
        if metrics_file.exists():
            with open(metrics_file) as f:
                return json.load(f)
        
        return None
    
    def log_run(self, status, quality, forecast, duration):
        """Log pipeline run to CSV"""
        timestamp = datetime.utcnow().isoformat() + 'Z'
        run_id = status.get('run_id', 'unknown') if status else 'unknown'
        status_str = status.get('status', 'failed') if status else 'failed'
        records = status.get('gold_record_count', 0) if status else 0
        
        quality_status = quality.get('pipeline_status', 'unknown') if quality else 'unknown'
        failed = quality.get('counts', {}).get('failed_checks', 0) if quality else 0
        warnings = quality.get('counts', {}).get('warning_checks', 0) if quality else 0
        
        mae = None
        if forecast and 'test' in forecast:
            mae = forecast['test'].get('linear_model', {}).get('mae')
        
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                run_id,
                status_str,
                records,
                quality_status,
                failed,
                warnings,
                mae,
                round(duration, 2)
            ])
        
        print(f"\n📝 Logged run to {self.log_file}")
    
    def run_full_pipeline(self):
        """Execute complete pipeline"""
        print("\n" + "="*60)
        print("🚀 HackInsight Air Quality Pipeline")
        print(f"⏰ Started: {datetime.utcnow().isoformat()}Z")
        print("="*60)
        
        try:
            # Step 1: Data pipeline
            status, duration = self.run_data_pipeline()
            
            # Step 2: Quality checks
            quality = self.check_quality()
            
            # Step 3: Forecasting
            forecast = self.run_forecasting()
            
            # Step 4: Log results
            self.log_run(status, quality, forecast, duration)
            
            print("\n" + "="*60)
            print("✅ Pipeline Completed Successfully!")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Pipeline failed with error: {e}")
            return False

def main():
    """Main entry point"""
    runner = PipelineRunner()
    success = runner.run_full_pipeline()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
