# PrUn-Tracker
Prosperous Universe Data Analyser


Hello!
I have the following;

I have several python scripts and programs that fetch info from source apis to deliver calculations and stamp it in 2 google spreadsheets, one named ONN_Historical_Data (Timestamps and data for that day) and another named PrUn Calculator (Daily overview reports).

These are for a game called Prosperous Universe about space capitalism in essence.
The folder structure is as follows; with files explained:

PrUn-Tracker/
│
├── .gitignore
├── pyrightconfig.json
├── README.md
├── ROOT_CLEANUP_ANALYSIS.md
│
├── pu-tracker/
│   ├── .env
│   ├── main_enhanced.py
│   ├── remove_duplicates.bat
│   ├── run_pipeline.bat
│   ├── writer_profiles.json
│   │
│   ├── cache/
│   │   ├── buildings.csv
│   │   ├── buildings.json
│   │   ├── cache_metadata.json
│   │   ├── categories.json
│   │   ├── chains.json
│   │   ├── daily_analysis_enhanced.csv
│   │   ├── daily_analysis.csv
│   │   ├── daily_report.csv
│   │   ├── data_sheets_cache.json
│   │   ├── market_data.csv
│   │   ├── materials.csv
│   │   ├── prices_all.csv
│   │   ├── processed_data.csv
│   │   ├── recipe_inputs.csv
│   │   ├── recipe_outputs.csv
│   │   ├── recipes.json
│   │   ├── tickers.json
│   │   ├── tier0_resources.json
│   │   ├── tiers.json
│   │   └── workforces.csv
│   │
│   ├── data/
│   │   ├── historical_data_condensed.json
│   │   └── prosperous_universe.db
│   │
│   ├── historical_data/
│   │   ├── __init__.py
│   │   ├── add_tier_to_materials.py
│   │   ├── catch_data.py
│   │   ├── chain_dictionary_generator.py
│   │   ├── data_analyzer.py
│   │   ├── db_manager.py
│   │   ├── debu_data_file.py
│   │   ├── debu_process_data_file.py
│   │   ├── dictionary_builder_buildings.py
│   │   ├── enhanced_analysis.py
│   │   ├── fetch_all_tickers.py
│   │   ├── fetch_materials.py
│   │   ├── main.py
│   │   ├── prun-profit-7e0c3bafd690.json
│   │   ├── rate_limiter.py
│   │   ├── sheets_manager.py
│   │   ├── smart_cache.py
│   │   ├── test_setup.bat
│   │   ├── ultra_all_exchanges_upload.py
│   │   ├── unified_config.py
│   │   ├── unified_processor.py
│   │   ├── upload_data.py
│   │   ├── upload_enhanced_analysis.py
│   │   └── __pycache__/
│   │        └── (compiled .pyc files)
│   │
│   └── logs/
│        └── (pipeline log files)
│
├── tests/
│   ├── __init__.py
│   ├── test_comprehensive.py
│   └── unit/
│
└── utils/

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
