"""
OpenAQ Data Source Integration
Fetches historical PM2.5 data from OpenAQ API for Pakistan
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from pathlib import Path
import hashlib
import json

class OpenAQFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openaq.org/v3"
        self.headers = {"X-API-Key": api_key}
    
    def fetch_locations(self, country="PK", parameter="pm25"):
        """Fetch available monitoring locations in Pakistan"""
        url = f"{self.base_url}/locations"
        params = {
            "country": country,
            "parameter": parameter,
            "limit": 100
        }
        
        print(f"🔍 Fetching OpenAQ locations for {country}...")
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        
        # Debug
        if response.status_code != 200:
            print(f"Response: {response.text}")
        
        response.raise_for_status()
        
        data = response.json()
        locations = data.get("results", [])
        print(f"✅ Found {len(locations)} locations")
        
        return locations
    
    def fetch_measurements(self, location_id, date_from, date_to, parameter="pm25"):
        """Fetch measurements for a specific location"""
        url = f"{self.base_url}/measurements"
        params = {
            "location": location_id,
            "parameter": parameter,
            "date_from": date_from,
            "date_to": date_to,
            "limit": 10000
        }
        
        response = requests.get(url, headers=self.headers, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        return data.get("results", [])
    
    def fetch_historical_data(self, days_back=365, max_locations=5):
        """Fetch historical PM2.5 data from multiple locations"""
        print("\n" + "="*60)
        print("🌍 Fetching OpenAQ Historical Data")
        print("="*60)
        
        # Get locations
        locations = self.fetch_locations()
        
        if not locations:
            print("❌ No locations found in Pakistan")
            return None
        
        # Use top locations with most data
        top_locations = sorted(
            locations, 
            key=lambda x: x.get("measurements", 0), 
            reverse=True
        )[:max_locations]
        
        print(f"\n📍 Selected {len(top_locations)} locations:")
        for loc in top_locations:
            name = loc.get("name", "Unknown")
            city = loc.get("city", "Unknown")
            measurements = loc.get("measurements", 0)
            print(f"  • {name} ({city}) - {measurements:,} measurements")
        
        # Fetch measurements
        all_measurements = []
        date_to = datetime.utcnow().strftime("%Y-%m-%d")
        date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        for i, location in enumerate(top_locations, 1):
            loc_id = location.get("id")
            loc_name = location.get("name", "Unknown")
            
            print(f"\n📥 [{i}/{len(top_locations)}] Fetching {loc_name}...")
            
            try:
                measurements = self.fetch_measurements(loc_id, date_from, date_to)
                all_measurements.extend(measurements)
                print(f"  ✅ Got {len(measurements)} measurements")
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
                continue
        
        if not all_measurements:
            print("\n❌ No measurements retrieved")
            return None
        
        print(f"\n✅ Total measurements: {len(all_measurements):,}")
        
        # Convert to DataFrame
        df = self.process_measurements(all_measurements)
        return df
    
    def process_measurements(self, measurements):
        """Process measurements into structured DataFrame"""
        print("\n🔄 Processing measurements...")
        
        records = []
        for m in measurements:
            try:
                record = {
                    "datetime": m.get("date", {}).get("utc"),
                    "location_id": m.get("location_id"),
                    "location": m.get("location"),
                    "city": m.get("city"),
                    "country": m.get("country"),
                    "parameter": m.get("parameter"),
                    "value": m.get("value"),
                    "unit": m.get("unit"),
                    "coordinates_lat": m.get("coordinates", {}).get("latitude"),
                    "coordinates_lon": m.get("coordinates", {}).get("longitude")
                }
                records.append(record)
            except Exception as e:
                continue
        
        df = pd.DataFrame(records)
        
        # Convert datetime
        df["datetime"] = pd.to_datetime(df["datetime"])
        df["date"] = df["datetime"].dt.date
        
        # Daily aggregation (mean)
        daily = df.groupby(["date", "location_id", "location", "city"]).agg({
            "value": "mean",
            "coordinates_lat": "first",
            "coordinates_lon": "first"
        }).reset_index()
        
        daily = daily.rename(columns={"value": "pm25_ug_m3"})
        
        print(f"✅ Processed into {len(daily):,} daily records")
        print(f"📅 Date range: {daily['date'].min()} to {daily['date'].max()}")
        
        return daily
    
    def save_raw_data(self, df, output_dir="data/raw/openaq_pakistan"):
        """Save raw OpenAQ data with provenance"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"openaq_pm25_pakistan_{timestamp}.csv"
        filepath = output_path / filename
        
        # Save data
        df.to_csv(filepath, index=False)
        
        # Save provenance
        provenance = {
            "source": "OpenAQ",
            "source_url": "https://openaq.org",
            "api_version": "v3",
            "parameter": "pm25",
            "country": "Pakistan",
            "fetched_at_utc": datetime.utcnow().isoformat() + "Z",
            "filename": filename,
            "records": len(df),
            "date_range": {
                "start": str(df["date"].min()),
                "end": str(df["date"].max())
            },
            "locations": df["location"].unique().tolist(),
            "cities": df["city"].unique().tolist()
        }
        
        provenance_file = filepath.with_suffix(".json")
        with open(provenance_file, "w") as f:
            json.dump(provenance, f, indent=2)
        
        # Calculate hash
        with open(filepath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        print(f"\n✅ Saved to: {filepath}")
        print(f"📊 Records: {len(df):,}")
        print(f"🔐 SHA256: {file_hash}")
        
        return filepath, provenance

def main():
    """Test OpenAQ integration"""
    import os
    
    # Get API key from environment or argument
    api_key = os.getenv("OPENAQ_API_KEY", "YOUR_API_KEY_HERE")
    
    if api_key == "YOUR_API_KEY_HERE":
        print("❌ Please set OPENAQ_API_KEY environment variable")
        return
    
    fetcher = OpenAQFetcher(api_key)
    
    # Fetch last 2 years of data
    df = fetcher.fetch_historical_data(days_back=730, max_locations=10)
    
    if df is not None:
        # Save
        filepath, provenance = fetcher.save_raw_data(df)
        print("\n" + "="*60)
        print("✅ OpenAQ Data Fetch Complete!")
        print("="*60)

if __name__ == "__main__":
    main()
