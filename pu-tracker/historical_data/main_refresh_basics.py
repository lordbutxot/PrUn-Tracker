import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import logging
import json
from pathlib import Path

from historical_data.config import CACHE_DIR
from historical_data.data_processor import process_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_cache_directory():
    """Ensure cache directory exists."""
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Cache directory: {CACHE_DIR}")

def collect_basic_data():
    """Collect all basic data files needed for processing."""
    logger.info("=== PHASE 1: DATA COLLECTION ===")
    
    # 1. Fetch materials data
    logger.info("Fetching materials data...")
    try:
        from historical_data.fetch_materials import main as fetch_materials_main
        fetch_materials_main()
        logger.info("✅ Materials data collected")
    except Exception as e:
        logger.error(f"❌ Failed to fetch materials: {e}")
        return False

    # 2. Build buildings dictionary
    logger.info("Building buildings dictionary...")
    try:
        from historical_data.dictionary_builder_buildings import main as build_buildings_main
        build_buildings_main()
        logger.info("✅ Buildings dictionary created")
    except Exception as e:
        logger.error(f"❌ Failed to build buildings dictionary: {e}")
        return False

    # 3. Generate chain dictionary
    logger.info("Generating chain dictionary...")
    try:
        from historical_data.chain_dictionary_generator import main as chain_gen_main
        chain_gen_main()
        logger.info("✅ Chain dictionary created")
    except Exception as e:
        logger.error(f"❌ Failed to generate chain dictionary: {e}")
        return False

    # 4. Add tier information
    logger.info("Adding tier information...")
    try:
        from historical_data.add_tier_to_materials import main as add_tier_main
        add_tier_main()
        logger.info("✅ Tier information added")
    except Exception as e:
        logger.error(f"❌ Failed to add tier information: {e}")
        return False

    # 5. Fetch current market data
    logger.info("Fetching current market data...")
    try:
        from historical_data.fetch_all_tickers import main as fetch_tickers_main
        fetch_tickers_main()
        logger.info("✅ Market data collected")
    except Exception as e:
        logger.error(f"❌ Failed to fetch market data: {e}")
        return False

    return True

def verify_required_files():
    """Verify all required files exist and are valid."""
    logger.info("=== VERIFYING COLLECTED DATA ===")
    
    required_files = {
        "materials.csv": "Materials data",
        "buildings.json": "Buildings dictionary", 
        "recipes.json": "Recipes data",
        "chains.json": "Production chains",
        "categories.json": "Categories mapping",
        "market_data.csv": "Market prices",
        "tiers.json": "Tier information"
    }
    
    missing_files = []
    corrupted_files = []
    
    for filename, description in required_files.items():
        filepath = os.path.join(CACHE_DIR, filename)
        
        if not os.path.exists(filepath):
            missing_files.append(f"{filename} ({description})")
            continue
            
        # Check if file has content
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
                if df.empty:
                    corrupted_files.append(f"{filename} (empty)")
                else:
                    logger.info(f"✅ {filename}: {len(df)} rows")
            elif filename.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not data:
                    corrupted_files.append(f"{filename} (empty)")
                else:
                    logger.info(f"✅ {filename}: {len(data)} items")
        except Exception as e:
            corrupted_files.append(f"{filename} (corrupted: {e})")
    
    if missing_files:
        logger.error(f"❌ Missing files: {missing_files}")
        return False
        
    if corrupted_files:
        logger.error(f"❌ Corrupted files: {corrupted_files}")
        return False
        
    logger.info("✅ All required files verified successfully")
    return True

def process_collected_data():
    """Process the collected data."""
    logger.info("=== PHASE 2: DATA PROCESSING ===")
    
    # Load prices data
    prices_path = os.path.join(CACHE_DIR, "market_data.csv")
    prices_df = pd.read_csv(prices_path)
    logger.info(f"Loaded prices data: {len(prices_df)} rows")

    # Load support data
    with open(os.path.join(CACHE_DIR, "buildings.json"), "r", encoding="utf-8") as f:
        building_dict = json.load(f)
    with open(os.path.join(CACHE_DIR, "categories.json"), "r", encoding="utf-8") as f:
        categories = json.load(f)
    with open(os.path.join(CACHE_DIR, "chains.json"), "r", encoding="utf-8") as f:
        chains = json.load(f)

    logger.info(f"Loaded: {len(building_dict)} buildings, {len(categories)} categories, {len(chains)} chains")

    # Debug chains data to check for issues
    logger.info("Checking chains data integrity...")
    bad_chains = 0
    for ticker, chain_data in list(chains.items())[:5]:  # Check first 5
        if not isinstance(chain_data, dict):
            logger.warning(f"Bad chain data for {ticker}: {type(chain_data)} - {chain_data}")
            bad_chains += 1
    
    if bad_chains > 0:
        logger.error(f"Found {bad_chains} bad chain entries. Please regenerate chains.json")
        return None

    # Process data
    try:
        processed_df = process_data(prices_df, building_dict, categories, chains)
        logger.info(f"Processed DataFrame shape: {processed_df.shape}")
        
        if processed_df.empty:
            logger.error("❌ Processing resulted in empty DataFrame")
            return None
            
        # Save processed data
        output_path = os.path.join(CACHE_DIR, "processed_data.csv")
        processed_df.to_csv(output_path, index=False)
        logger.info(f"✅ Saved processed data to {output_path}")
        
        return processed_df
        
    except Exception as e:
        logger.error(f"❌ Data processing failed: {e}", exc_info=True)
        return None

def main():
    """Main execution function."""
    logger.info("🚀 Starting PrUn-Tracker Data Collection and Processing")
    
    # Ensure cache directory exists
    ensure_cache_directory()
    
    # Phase 1: Collect all basic data
    if not collect_basic_data():
        logger.error("❌ Data collection failed. Stopping.")
        return False
    
    # Verify all files are present and valid
    if not verify_required_files():
        logger.error("❌ File verification failed. Stopping.")
        return False
    
    # Phase 2: Process the collected data
    processed_df = process_collected_data()
    if processed_df is None:
        logger.error("❌ Data processing failed. Stopping.")
        return False
    
    logger.info("🎉 Data collection and processing completed successfully!")
    logger.info(f"📊 Final dataset: {len(processed_df)} rows, {len(processed_df.columns)} columns")
    
    # Show sample of what we have
    logger.info("Sample columns: " + ", ".join(processed_df.columns[:10].tolist()))
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ Ready for next phase: Report generation")
    else:
        logger.error("❌ Setup incomplete. Fix errors above before proceeding.")