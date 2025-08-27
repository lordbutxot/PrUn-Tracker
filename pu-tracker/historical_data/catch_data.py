"""
catch_data.py
Entry point for fetching and caching raw data for PrUn-Tracker.
Updated to work with consolidated modules and fix import issues.
"""

import sys
from pathlib import Path

# Add parent directory to path for unified modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import data collection modules with absolute imports (no relative imports)
try:
    import fetch_all_tickers
    import fetch_materials 
    import main_refresh_basics
    import chain_dictionary_generator
    import dictionary_builder_buildings
    import add_tier_to_materials
    from unified_processor import UnifiedDataProcessor
except ImportError as e:
    print(f"[WARNING] Some modules not found: {e}")
    print("[INFO] Will attempt to run available modules only")

def main():
    print("[Catch] Starting data collection...")
    
    # Step 1: Fetch basic market data and tickers
    print("[Catch] Fetching market data and tickers...")
    try:
        import fetch_all_tickers
        fetch_all_tickers.main()
        print("[SUCCESS] Market data and tickers fetched")
    except Exception as e:
        print(f"[ERROR] Failed to fetch tickers: {e}")
    
    # Step 2: Fetch materials data
    print("[Catch] Fetching materials data...")
    try:
        import fetch_materials
        fetch_materials.main()
        print("[SUCCESS] Materials data fetched")
    except Exception as e:
        print(f"[ERROR] Failed to fetch materials: {e}")
    
    # Step 3: Build dictionaries and reference data
    print("[Catch] Building chain dictionary...")
    try:
        import chain_dictionary_generator
        chain_dictionary_generator.main()
        print("[SUCCESS] Chain dictionary built")
    except Exception as e:
        print(f"[ERROR] Failed to build chain dictionary: {e}")
    
    print("[Catch] Building buildings dictionary...")
    try:
        import dictionary_builder_buildings
        dictionary_builder_buildings.main()
        print("[SUCCESS] Buildings dictionary built")
    except Exception as e:
        print(f"[ERROR] Failed to build buildings dictionary: {e}")
    
    print("[Catch] Adding tier information to materials...")
    try:
        import add_tier_to_materials
        add_tier_to_materials.main()
        print("[SUCCESS] Tier information added")
    except Exception as e:
        print(f"[ERROR] Failed to add tier information: {e}")
    
    # Step 4: Collect and cache all data
    try:
        print("[Catch] Running main data collection...")
        
        # Import the correct processor
        from unified_processor import main as process_main
        
        # Run the processing
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
    
    print("[SUCCESS] Data collection completed")
    return True

if __name__ == "__main__":
    main()
