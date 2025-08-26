# PrUn-Tracker
Prosperous Universe Data Analyser


Hello!
I have the following;

I have several python scripts and programs that fetch info from source apis to deliver calculations and stamp it in 2 google spreadsheets, one named ONN_Historical_Data (Timestamps and data for that day) and another named PrUn Calculator (Daily overview reports).

These are for a game called Prosperous Universe about space capitalism in essence.
The folder structure is as follows; with files explained:

PrUn-Tracker/
├── pu-tracker/
│   │
│   ├── MAIN ENTRY POINTS
│   ├── main.py                          # Top-level entry point, redirects to historical_data/main.py
│   ├── run_pipeline.bat                 # Windows batch file to run the complete 3-step pipeline
│   │
│   ├── OPTIMIZATION & UPLOAD SCRIPTS
│   ├── complete_ai1_upload.py           # Complete AI1 upload with all 22 required columns (merges report+analysis data)
│   ├── simple_ai1_upload.py             # Simple AI1-only upload using single batch API call
│   ├── optimized_sheets_upload.py       # Optimized uploader with rate limiting and batch operations
│   │
│   ├── DIAGNOSTIC & TEST SCRIPTS
│   ├── diagnose_ai1.py                  # Diagnostic script to check AI1 data and Google Sheets connection
│   ├── test_ai1_only.py                 # Test script for uploading only Report AI1 data
│   ├── test_ai1_upload_optimized.py     # Test optimized AI1 upload function
│   ├── test_data_types.py               # Test data type validation
│   ├── test_direct_sheets.py            # Test direct Google Sheets connection
│   ├── test_google_sheets.py            # Test Google Sheets API functionality
│   ├── test_improved_analysis.py        # Test improved analysis features
│   ├── test_improvements.py             # Test various improvements
│   ├── test_main_upload.py              # Test main upload functionality
│   ├── test_sheets_connection.py        # Test Google Sheets connection and data
│   ├── test_upload.py                   # Test upload operations
│   ├── upload_data_ai1_only.py          # Alternative AI1-only upload script
│   │
│   ├── DOCUMENTATION
│   ├── DAILY_ANALYSIS_IMPROVEMENTS.md   # Documentation of daily analysis improvements
│   ├── ENHANCED_REPORTS_SUMMARY.md      # Summary of enhanced reporting features
│   ├── GOOGLE_SHEETS_REPORT_FORMATTING_SUMMARY.md # Google Sheets formatting documentation
│   ├── IMPROVEMENTS_SUMMARY.md          # Overall improvements summary
│   ├── PU_TRACKER_CLEANUP_PLAN.md       # Cleanup and optimization plan
│   ├── STRUCTURE_UPDATE.md              # Structure update documentation
│   │
│   ├── CONFIGURATION
│   ├── writer_profiles.json             # Writer profiles configuration
│   ├── configuration/
│   │   ├── app_config.py                # Application configuration settings
│   │   └── environment_config.py        # Environment-specific configuration
│   │
│   ├── CACHED DATA
│   ├── cache/
│   │   ├── buildings.csv                # Building data cache
│   │   ├── buildings.json               # Building data in JSON format
│   │   ├── cache_metadata.json          # Cache metadata and timestamps
│   │   ├── categories.json              # Material categories cache
│   │   ├── chains.json                  # Production chain data
│   │   ├── daily_analysis.csv           # MAIN: Advanced daily analysis with Investment Score, Risk Level
│   │   ├── daily_report.csv             # MAIN: Basic daily report with Recipe, Weight, Volume data
│   │   ├── data_sheets_cache.json       # Google Sheets data cache
│   │   ├── market_data.csv              # Raw market data
│   │   ├── materials.csv                # Materials database
│   │   ├── prices_all.csv               # All price data across exchanges
│   │   ├── processed_data.csv           # Processed and cleaned data
│   │   ├── recipe_inputs.csv            # Recipe input requirements
│   │   ├── recipe_outputs.csv           # Recipe output data
│   │   ├── recipes.json                 # Production recipes database
│   │   ├── tickers.json                 # All available ticker symbols
│   │   ├── tier0_resources.json         # Tier 0 (raw) resources list
│   │   ├── tiers.json                   # Material tier classifications
│   │   └── workforces.csv               # Workforce data
│   │
│   ├── PERSISTENT DATA
│   ├── data/
│   │   ├── historical_data_condensed.json # Condensed historical data
│   │   └── prosperous_universe.db       # SQLite database with historical data
│   │
│   └── CORE PROCESSING MODULES
│       └── historical_data/
│           ├── __init__.py              # Python package initialization
│           ├── main.py                  # MAIN: Core pipeline controller (catch/process/upload commands)
│           ├── prun-profit-7e0c3bafd690.json # Google Sheets API credentials
│           │
│           ├── DATA COLLECTION
│           ├── catch_data.py            # STEP 1: Collect data from PrUn API
│           ├── data_collection.py       # Data collection utilities
│           ├── fetch_all_tickers.py     # Fetch all available ticker symbols
│           ├── fetch_materials.py       # Fetch material data from API
│           ├── main_refresh_basics.py   # Refresh basic data caches
│           │
│           ├── DATA PROCESSING
│           ├── process_data.py          # STEP 2: Process and analyze collected data
│           ├── data_processor.py        # Core data processing engine
│           ├── data_analysis.py         # Advanced data analysis algorithms
│           ├── report_builder.py        # Build daily reports and analysis
│           │
│           ├── DATA UPLOAD
│           ├── upload_data.py           # STEP 3: Upload processed data to Google Sheets
│           ├── sheet_updater.py         # Google Sheets update utilities
│           ├── sheets_api.py            # Google Sheets API wrapper
│           ├── sheets_optimizer.py      # Optimize Google Sheets operations
│           ├── sheets_rate_limiter.py   # Rate limiting for Google Sheets API
│           │
│           ├── UTILITIES & HELPERS
│           ├── config.py                # Configuration constants and settings
│           ├── db_manager.py            # Database management utilities
│           ├── rate_limiter.py          # General API rate limiting
│           ├── smart_cache.py           # Intelligent caching system
│           ├── formatting_config.py     # Data formatting configurations
│           │
│           ├── DATA BUILDERS
│           ├── add_tier_to_materials.py # Add tier information to materials
│           ├── chain_dictionary_generator.py # Generate production chain dictionaries
│           ├── dictionary_builder_buildings.py # Build building dictionaries
│           │
│           └── __pycache__/             # Python compiled bytecode cache
│               └── *.pyc files          # Compiled Python modules for faster loading

PIPELINE FLOW:
1. run_pipeline.bat OR main.py → historical_data/main.py
2. STEP 1 (catch): catch_data.py → Collects data from PrUn API
3. STEP 2 (process): process_data.py → Creates daily_report.csv & daily_analysis.csv
4. STEP 3 (upload): upload_data.py → Uploads to Google Sheets with rate limiting

KEY DATA FILES:
- daily_report.csv: Contains Recipe, Weight, Volume, Market Cap, Liquidity Ratio
- daily_analysis.csv: Contains Investment Score, Risk Level, Advanced Analysis
- Both merged for complete DATA AI1 sheet with all 22 required columns

GOOGLE SHEETS OUTPUT:
- DATA AI1: Basic market data with all 22 columns (primary focus)
- Report AI1: Advanced analysis with arbitrage, bottlenecks, production opportunities
- Similar sheets for other exchanges (CI1, CI2, NC1, NC2, IC1)
