"""
AirGradient Sensor Data as Second Independent Source
Captures live sensor readings as historical warehouse data
"""
import json
import csv
import hashlib
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.live_sensors import fetch_live_snapshot

def capture_airgradient_snapshot():
    """Capture current AirGradient sensor readings for warehouse"""
    print("\n" + "="*60)
    print("📡 Capturing AirGradient Sensor Data")
    print("="*60)
    
    # Fetch live data
    live_data = fetch_live_snapshot()
    
    if not live_data or live_data.get("status") != "ok":
        print("⚠️  No live sensor data available")
        return None
    
    # Prepare warehouse entry
    timestamp = datetime.utcnow().isoformat() + "Z"
    date = datetime.utcnow().date().isoformat()
    
    records = []
    
    # Primary sensor
    primary = live_data.get("primary_sensor")
    if primary and primary.get("pm25_ug_m3") is not None:
        records.append({
            "date": date,
            "timestamp_utc": timestamp,
            "location_id": primary.get("location_id"),
            "location_name": primary.get("location_name") or primary.get("configured_label"),
            "area": primary.get("area", "Karachi"),
            "pm25_ug_m3": primary.get("pm25_ug_m3"),
            "temperature_c": primary.get("temperature_c"),
            "humidity_pct": primary.get("relative_humidity_pct"),
            "observation_time": primary.get("observation_time_utc"),
            "freshness": primary.get("freshness"),
            "source": "AirGradient"
        })
    
    # Other sensors
    for sensor in live_data.get("sensors", []):
        if sensor.get("pm25_ug_m3") is not None:
            records.append({
                "date": date,
                "timestamp_utc": timestamp,
                "location_id": sensor.get("location_id"),
                "location_name": sensor.get("location_name") or sensor.get("configured_label"),
                "area": sensor.get("area", "Karachi"),
                "pm25_ug_m3": sensor.get("pm25_ug_m3"),
                "temperature_c": sensor.get("temperature_c"),
                "humidity_pct": sensor.get("relative_humidity_pct"),
                "observation_time": sensor.get("observation_time_utc"),
                "freshness": sensor.get("freshness"),
                "source": "AirGradient"
            })
    
    if not records:
        print("⚠️  No valid sensor readings")
        return None
    
    print(f"✅ Captured {len(records)} sensor readings")
    
    # Save to warehouse
    output_dir = Path("data/raw/airgradient_sensors")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Append to historical file
    hist_file = output_dir / "airgradient_historical.csv"
    
    # Create with headers if new
    if not hist_file.exists():
        with open(hist_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
    
    # Append records
    with open(hist_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writerows(records)
    
    # Calculate hash
    with open(hist_file, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    # Save provenance
    provenance = {
        "source": "AirGradient",
        "source_url": "https://api.airgradient.com/",
        "provider": "The Urban Unit / AirGradient",
        "captured_at_utc": timestamp,
        "date": date,
        "records_added": len(records),
        "locations": [r["location_name"] for r in records],
        "file_sha256": file_hash
    }
    
    prov_file = output_dir / f"capture_{date.replace('-', '')}.json"
    with open(prov_file, 'w') as f:
        json.dump(provenance, f, indent=2)
    
    print(f"📁 Saved to: {hist_file}")
    print(f"📊 Total warehouse records: {sum(1 for _ in open(hist_file)) - 1}")
    print(f"🔐 SHA256: {file_hash[:16]}...")
    
    return hist_file, provenance

if __name__ == "__main__":
    result = capture_airgradient_snapshot()
    if result:
        filepath, prov = result
        print("\n✅ AirGradient data captured successfully!")
        print(f"Independent Source: {prov['provider']}")
    else:
        print("\n❌ Failed to capture AirGradient data")
