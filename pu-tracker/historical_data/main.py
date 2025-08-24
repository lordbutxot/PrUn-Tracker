import asyncio
import logging
import time
import pandas as pd
import sys
import os
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add pu-tracker to sys.path
pu_tracker_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(pu_tracker_path)
logger.info(f"sys.path updated with: {pu_tracker_path}")

try:
    from historical_data.data_collection import fetch_and_cache_data, init_db
    from historical_data.data_processor import process_data
    from historical_data.data_analysis import analyze_data, authenticate_sheets, load_data_sheets
    from historical_data.sheets_api import MarketProcessor
    from historical_data.db_manager import insert_price_data
    from historical_data.config import CACHE_DIR, TARGET_SPREADSHEET_ID
except ImportError as e:
    logger.error(f"Import failed: {e}")
    raise

async def run_pipeline():
    """Run the full data pipeline."""
    start_time = time.time()
    logger.info("Starting pipeline execution")
    
    try:
        # Initialize database
        init_db()
        
        # Fetch and cache data
        logger.info("Fetching and caching data")
        prices_df, building_dict, categories, tickers, product_tiers, chains = await fetch_and_cache_data(fetch_static=True)
        
        if not chains or not product_tiers or not tickers:
            logger.error("No chains, tiers, or tickers available, aborting pipeline")
            return
        
        if prices_df.empty:
            logger.error("No price data available, aborting pipeline")
            return
        
        # Insert price data into database
        logger.info("Inserting price data into database")
        insert_price_data(prices_df)
        
        # Process data
        logger.info("Processing data")
        processed_data = process_data(prices_df, building_dict, categories, tickers, product_tiers, chains)
        
        if processed_data.empty:
            logger.warning("No processed data available")
            return
        
        logger.info("Data processing completed")
        
        # Load data from Google Sheets
        client = authenticate_sheets()
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID)
        data_sheets = load_data_sheets(spreadsheet)
        
        # Analyze data
        logger.info("Analyzing data")
        analysis_results, trends, recommendations = analyze_data(data_sheets, processed_data, chains, product_tiers, tickers)
        
        if not analysis_results:
            logger.warning("No analysis results generated")
            return
        
        logger.info("Data analysis completed")
        
        # Update Google Sheets
        processor = MarketProcessor(spreadsheet)
        await processor.process(analysis_results)
        logger.info("Google Sheets updated")
        
        await processor.close()
        logger.info("MarketProcessor closed")
        
        logger.info(f"Pipeline completed in {time.time() - start_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(run_pipeline())