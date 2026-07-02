# Save this as fetch_all_tickers.py and run it once
import requests
import pandas as pd
import os
from io import StringIO
import csv
import json

def main():
    """Main function to fetch market data and tier0 resources."""
    try:
        # 1. Fetch current market prices
        print("Fetching market prices...")
        prices_url = "https://rest.fnar.net/csv/prices"
        response = requests.get(prices_url)
        response.raise_for_status()
        
        # Save raw market data
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
        os.makedirs(cache_dir, exist_ok=True)
        
        market_data_path = os.path.join(cache_dir, "market_data.csv")
        with open(market_data_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        print(f"Downloaded market_data.csv to {market_data_path}")
        
        # Also create a formatted version
        df = pd.read_csv(StringIO(response.text))
        prices_all_path = os.path.join(cache_dir, "prices_all.csv")
        df.to_csv(prices_all_path, index=False)
        print(f"Created formatted prices_all.csv with {len(df)} rows")
        
        # 2. Fetch materials and extract tier0 resources
        print("Fetching tier0 resources...")
        materials_url = "https://rest.fnar.net/csv/materials"
        response = requests.get(materials_url)
        response.raise_for_status()

        csvfile = StringIO(response.text)
        reader = csv.DictReader(csvfile)

        # Only Tier 0 resources
        tier0 = [row['Ticker'] for row in reader if row.get('Tier') == '0']

        # Save tier0 resources
        tier0_path = os.path.join(cache_dir, "tier0_resources.json")
        with open(tier0_path, "w", encoding="utf-8") as f:
            json.dump(tier0, f, indent=2)
        
        print(f"Generated tier0_resources.json with {len(tier0)} items in {cache_dir}")
        
        # 3. Create a tickers.json file with all available tickers
        all_tickers = df['Ticker'].dropna().unique().tolist()
        tickers_path = os.path.join(cache_dir, "tickers.json")
        with open(tickers_path, "w", encoding="utf-8") as f:
            json.dump(all_tickers, f, indent=2)
        
        print(f"Generated tickers.json with {len(all_tickers)} tickers")
        
    except Exception as e:
        print(f"Error fetching market data: {e}")
        raise

if __name__ == "__main__":
    main()