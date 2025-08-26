"""
catch_data.py
Entry point for fetching and caching raw data for PrUn-Tracker.
"""

# Import data collection modules with relative imports
from . import (
    fetch_all_tickers, 
    fetch_materials, 
    main_refresh_basics,
    chain_dictionary_generator,
    dictionary_builder_buildings,
    add_tier_to_materials
)

def main():
    print("[Catch] Starting data collection...")
    
    # Step 1: Fetch basic market data and tickers
    print("[Catch] Fetching market data and tickers...")
    fetch_all_tickers.main()
    
    # Step 2: Fetch materials data
    print("[Catch] Fetching materials data...")
    fetch_materials.main()
    
    # Step 3: Build dictionaries and reference data
    print("[Catch] Building chain dictionary...")
    chain_dictionary_generator.main()
    
    print("[Catch] Building buildings dictionary...")
    dictionary_builder_buildings.main()
    
    print("[Catch] Adding tier information to materials...")
    add_tier_to_materials.main()
    
    # Step 4: Collect and cache all data
    print("[Catch] Running main data collection...")
    main_refresh_basics.main()
    
    print("[Catch] Data collection complete.")

if __name__ == "__main__":
    main()
