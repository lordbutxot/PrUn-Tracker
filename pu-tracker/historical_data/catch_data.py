"""
catch_data.py
Entry point for fetching and caching raw data for PrUn-Tracker.
Updated to work with consolidated modules and fix import issues.
"""

import sys
from pathlib import Path
import requests

# Add parent directory to path for unified modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import data collection modules with absolute imports (no relative imports)
try:
    import fetch_all_tickers
    import fetch_materials 
    import chain_dictionary_generator
    import dictionary_builder_buildings
    import add_tier_to_materials
    from unified_processor import UnifiedDataProcessor
except ImportError as e:
    print(f"[WARNING] Some modules not found: {e}")
    print("[INFO] Will attempt to run available modules only")

def fetch_orders_csv():
    url = "https://rest.fnar.net/csv/orders"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    orders_file = cache_dir / "orders.csv"
    try:
        print("[Catch] Downloading orders.csv...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(orders_file, "wb") as f:
            f.write(response.content)
        print(f"[SUCCESS] Saved orders.csv ({orders_file})")
    except Exception as e:
        print(f"[ERROR] Failed to download orders.csv: {e}")

def fetch_bids_csv():
    url = "https://rest.fnar.net/csv/bids"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    bids_file = cache_dir / "bids.csv"
    try:
        print("[Catch] Downloading bids.csv...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(bids_file, "wb") as f:
            f.write(response.content)
        print(f"[SUCCESS] Saved bids.csv ({bids_file})")
    except Exception as e:
        print(f"[ERROR] Failed to download bids.csv: {e}")

def fetch_workforceneeds_json():
    url = "https://rest.fnar.net/global/workforceneeds"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    outfile = cache_dir / "workforceneeds.json"
    try:
        print("[Catch] Downloading workforceneeds.json...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(outfile, "wb") as f:
            f.write(resp.content)
        print(f"[SUCCESS] Saved workforceneeds.json ({outfile})")
    except Exception as e:
        print(f"[ERROR] Failed to download workforceneeds.json: {e}")

def fetch_market_data_csv():
    url = "https://rest.fnar.net/csv/marketdata"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    outfile = cache_dir / "market_data.csv"
    try:
        print("[Catch] Downloading market_data.csv...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(outfile, "wb") as f:
            f.write(resp.content)
        print(f"[SUCCESS] Saved market_data.csv ({outfile})")
    except Exception as e:
        print(f"[ERROR] Failed to download market_data.csv: {e}")

def fetch_planetresources_csv():
    url = "https://rest.fnar.net/csv/planetresources"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    outfile = cache_dir / "planetresources.csv"
    try:
        print("[Catch] Downloading planetresources.csv...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with open(outfile, "wb") as f:
            f.write(resp.content)
        print(f"[SUCCESS] Saved planetresources.csv ({outfile})")
    except Exception as e:
        print(f"[ERROR] Failed to download planetresources.csv: {e}")

def log_step(message):
    print(f"[STEP] {message}", flush=True)

def main():
    try:
        log_step("Starting data collection...")
        
        # Step 1: Fetch basic market data and tickers
        log_step("Fetching market data and tickers...")
        try:
            import fetch_all_tickers
            fetch_all_tickers.main()
            print("[SUCCESS] Market data and tickers fetched")
        except Exception as e:
            print(f"[ERROR] Failed to fetch tickers: {e}")
        
        # Step 2: Fetch materials data
        log_step("Fetching materials data...")
        try:
            import fetch_materials
            fetch_materials.main()
            print("[SUCCESS] Materials data fetched")
        except Exception as e:
            print(f"[ERROR] Failed to fetch materials: {e}")
        
        # Step 3: Build dictionaries and reference data
        log_step("Building chain dictionary...")
        try:
            import chain_dictionary_generator
            chain_dictionary_generator.main()
            print("[SUCCESS] Chain dictionary built")
        except Exception as e:
            print(f"[ERROR] Failed to build chain dictionary: {e}")
        
        log_step("Building buildings dictionary...")
        try:
            import dictionary_builder_buildings
            dictionary_builder_buildings.main()
            print("[SUCCESS] Buildings dictionary built")
        except Exception as e:
            print(f"[ERROR] Failed to build buildings dictionary: {e}")
        
        log_step("Generating workforces.csv from buildings data...")
        try:
            import generate_workforces
            generate_workforces.main()
            print("[SUCCESS] Workforces.csv generated")
        except Exception as e:
            print(f"[ERROR] Failed to generate workforces.csv: {e}")
        
        # Fetch required files BEFORE unified_processor runs
        log_step("Fetching buildingrecipes.csv...")
        try:
            from fetch_buildingrecipes import fetch_buildingrecipes
            fetch_buildingrecipes()
            print("[SUCCESS] buildingrecipes.csv fetched")
        except Exception as e:
            print(f"[ERROR] Failed to fetch buildingrecipes.csv: {e}")

        log_step("Fetching workforceneeds.json...")
        fetch_workforceneeds_json()
        
        log_step("Adding tier information to materials...")
        try:
            import add_tier_to_materials
            add_tier_to_materials.main()
            print("[SUCCESS] Tier information added")
        except Exception as e:
            print(f"[ERROR] Failed to add tier information: {e}")
        
        # Step 4: Collect and cache all data
        try:
            log_step("Running main data collection...")
            from unified_processor import main as process_main
            result = process_main()
            if result:
                print("[Catch] Data processing completed successfully")
            else:
                print("[Catch] Data processing had issues")
        except ImportError as e:
            print(f"[ERROR] Failed to import processor: {e}")
            print("[INFO] Skipping data processing step")
        except Exception as e:
            print(f"[ERROR] Failed to run main data collection: {e}")
        
        log_step("Fetching orders.csv...")
        fetch_orders_csv()
        log_step("Fetching bids.csv...")
        fetch_bids_csv()

        log_step("Fetching planetresources.csv...")
        fetch_planetresources_csv()

        print("[SUCCESS] Data collection completed", flush=True)
        return True
    except Exception as e:
        print(f"[FATAL] Unhandled exception in catch_data.py: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        print(f"[DEBUG] Exiting catch_data.py with code: {0 if success else 1}", flush=True)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FATAL] Unhandled exception at top level: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
