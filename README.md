# PrUn-Tracker

**PrUn-Tracker** is an advanced, modular data pipeline and analytics suite for the MMO [Prosperous Universe](https://prosperousuniverse.com/).

## Project Overview & Aims

PrUn-Tracker automates the entire workflow of collecting, processing, analyzing, and reporting in-game economic and production data.  
It enables players, corporations, and analysts to make data-driven decisions and optimize their gameplay.

### Key Aims and Features

- **Automated Data Collection:**  
  Fetches up-to-date market, production, building, and workforce data directly from the Prosperous Universe API.

- **Comprehensive Data Processing:**  
  Cleans, merges, and transforms raw data into structured formats (CSV, JSON), ready for analysis.

- **True Cost Calculation:**  
  Calculates not just the direct input costs for any product or recipe, but also includes the cost of all workforce consumables (like RAT, DW, OVE, etc.) based on the workforce type, hours required, and current market prices.  
  This provides a **real, all-inclusive input cost per unit, per stack, and per hour**—enabling truly accurate profitability and ROI analysis.

- **Advanced Analytics & Reporting:**  
  Generates enhanced analytics, including arbitrage opportunities, bottlenecks, investment scores, and more.  
  Produces detailed reports and summary tabs for each exchange and product.

- **Google Sheets Integration:**  
  Seamlessly uploads processed and analyzed data to Google Sheets, populating multiple tabs (DATA, REPORT, etc.) for easy access, sharing, and further custom analysis.

- **Batch Pipeline & Logging:**  
  One-click batch execution (`run_pipeline.bat`) orchestrates the entire workflow, with robust logging and error handling for transparency and debugging.

- **Extensible & Modular:**  
  Designed for easy extension—add new scripts, data sources, or analysis modules as needed.

- **Testing & Reliability:**  
  Includes unit and integration tests to ensure the pipeline remains robust as the game and your needs evolve.

---

## What You Can Use the Results For in Prosperous Universe

With PrUn-Tracker, you can:

- **Calculate True Production Costs:**  
  Know the exact cost to produce any item, including all hidden workforce consumable costs, so you never underprice or overpay.

- **Identify Profitable Opportunities:**  
  Instantly spot arbitrage and trade opportunities across exchanges, with real ROI and risk metrics.

- **Optimize Production Chains:**  
  Analyze bottlenecks, workforce needs, and input dependencies to streamline your production lines and maximize output.

- **Plan Investments and Expansion:**  
  Use investment scores, market cap, and liquidity ratios to make informed decisions about what to produce, buy, or sell.

- **Collaborate and Share Insights:**  
  Share live, auto-updating Google Sheets with your corporation or alliance, enabling coordinated strategy and market intelligence.

- **React to Market Changes:**  
  With automated, up-to-date data, you can quickly adapt to shifts in supply, demand, and pricing.

---

## Features

- **Automated Data Fetching:** Collects market, production, and building data from Prosperous Universe.
- **Data Cleaning & Processing:** Cleans, merges, and transforms raw data into structured CSV and JSON files.
- **Advanced Analysis:** Generates enhanced analytics, reports, and metrics for deeper economic insights.
- **Google Sheets Integration:** Uploads processed and analyzed data directly to Google Sheets, populating multiple tabs for easy access and collaboration.
- **Batch Pipeline:** One-click batch script (`run_pipeline.bat`) orchestrates the entire workflow, including logging and error handling.
- **Extensible & Modular:** Designed for easy extension with new scripts, data sources, or analysis modules.
- **Testing:** Includes comprehensive and unit tests to ensure reliability.

---

## Folder Structure

PrUn-Tracker/
│
├── .env
│   # Environment variables for local development (API keys, etc.)
│
├── dual_logger.py
│   # Helper script to duplicate pipeline output to both console and log file.
│
├── main_enhanced.py
│   # Async/advanced pipeline orchestrator (alternative to main.py).
│
├── remove_duplicates.bat
│   # Batch script to remove duplicate entries from data files.
│
├── run_pipeline.bat
│   # Main batch file to run the full pipeline and log output.
│
├── writer_profiles.json
│   # Configuration for Google Sheets writers/profiles.
│
├── cache/
│   # Folder for all intermediate and raw data files.
│   ├── bids.csv
│   ├── buildingrecipes.csv
│   ├── buildings.csv
│   ├── buildings.json
│   ├── cache_metadata.json
│   ├── categories.json
│   ├── chains.json
│   ├── daily_analysis_enhanced.csv
│   ├── daily_analysis.csv
│   ├── daily_report.csv
│   ├── DATA AI1_last_hash.txt
│   ├── DATA CI1_last_hash.txt
│   ├── DATA CI2_last_hash.txt
│   ├── DATA IC1_last_hash.txt
│   ├── DATA NC1_last_hash.txt
│   ├── DATA NC2_last_hash.txt
│   ├── data_sheets_cache.json
│   ├── market_data.csv
│   ├── materials.csv
│   ├── orders.csv
│   ├── prices_all.csv
│   ├── processed_data.csv
│   ├── recipe_inputs.csv
│   ├── recipe_outputs.csv
│   ├── recipes.json
│   ├── tickers.json
│   ├── tier0_resources.json
│   ├── tiers.json
│   ├── workforceneeds.json
│   └── workforces.csv
│   # (All files here are fetched, processed, or cached data for the pipeline.)
│
├── data/
│   # Folder for persistent data and database files.
│   ├── historical_data_condensed.json
│   └── prosperous_universe.db
│   # (Condensed data and SQLite DB for advanced analysis or backup.)
│
├── historical_data/
│   # Main source folder for all pipeline scripts and modules.
│   ├── __init__.py
│   │   # Marks this folder as a Python package.
│   ├── add_tier_to_materials.py
│   │   # Adds tier info to materials data.
│   ├── catch_data.py
│   │   # Entry point for fetching and caching all raw data.
│   ├── chain_dictionary_generator.py
│   │   # Generates a dictionary mapping for production chains.
│   ├── data_analyzer.py
│   │   # Performs unified analysis and generates enhanced CSV for upload.
│   ├── db_manager.py
│   │   # Handles database operations for persistent storage.
│   ├── debu_data_file.py
│   │   # Debug script for testing API endpoints and data.
│   ├── dictionary_builder_buildings.py
│   │   # Builds a dictionary of buildings and their properties.
│   ├── fetch_all_tickers.py
│   │   # Fetches all market tickers from the API.
│   ├── fetch_buildingrecipes.py
│   │   # Fetches building recipes from the API.
│   ├── fetch_materials.py
│   │   # Fetches materials data from the API.
│   ├── fetch_orders_and_bids.py
│   │   # Fetches orders and bids for arbitrage calculations.
│   ├── generate_report_tabs.py
│   │   # Generates and uploads report tabs to Google Sheets.
│   ├── main.py
│   │   # Main orchestrator for the full pipeline (fetch, process, analyze, upload).
│   ├── prun-profit-7e0c3bafd690.json
│   │   # Google API credentials for Sheets access.
│   ├── rate_limiter.py
│   │   # Handles API rate limiting for data fetching.
│   ├── sheets_manager.py
│   │   # Unified manager for Google Sheets API operations.
│   ├── smart_cache.py
│   │   # Intelligent caching system to minimize API calls.
│   ├── StepByStepRun.py
│   │   # Script to run each pipeline step individually for debugging.
│   ├── test_setup.bat
│   │   # Batch script for test environment setup.
│   ├── ultra_all_exchanges_upload.py
│   │   # Uploads all exchanges' data to Google Sheets in one go.
│   ├── unified_config.py
│   │   # Centralized configuration for the pipeline.
│   ├── unified_processor.py
│   │   # Processes and merges all raw data into unified datasets.
│   ├── upload_enhanced_analysis.py
│   │   # Uploads enhanced analysis to Google Sheets.
│   ├── workforce_costs.py
│   │   # Module for calculating input costs including workforce consumables.
│   └── __pycache__/
│       # Compiled Python files for faster loading.
│
├── logs/
│   # Folder for pipeline and debug log files.
│   └── pipeline_YYYYMMDD_HHMMSS.log
│   # (All logs from pipeline runs are stored here.)
│
└── (other files as needed) 

---

## Summary

- **Purpose:** Automates the collection and analysis of Prosperous Universe market and production data.
- **Pipeline:**  
  1. **Fetch:** Scripts collect data from the game's API.  
  2. **Process:** Data is cleaned, merged, and analyzed into CSVs.  
  3. **Analyze:** Enhanced analysis scripts generate advanced metrics and reports.  
  4. **Upload:** Results are uploaded to Google Sheets for sharing and further use.
- **Key Outputs:**  
  - `daily_report.csv` and `daily_analysis.csv` (core processed data)  
  - `daily_analysis_enhanced.csv` (final, enhanced data for Google Sheets)  
  - Google Sheets tabs: DATA AI1 (main), Report AI1 (advanced), and others for different exchanges.
- **Testing:** Includes unit and integration tests to ensure the pipeline remains robust as the game and your needs evolve.

---

## Conclusion

**PrUn-Tracker** empowers Prosperous Universe players with professional-grade analytics and automation.  
Whether you’re a solo entrepreneur, a logistics manager, or a corporation leader, you can use its results to:

- **Maximize profits**
- **Minimize waste**
- **Outmaneuver competitors**
- **Make data-driven decisions**
- **Collaborate more effectively**

All with minimal manual effort—just run the pipeline and get actionable, accurate insights delivered straight to your Google Sheets.

For more details, see the docstrings in each script and the comments throughout the codebase.
