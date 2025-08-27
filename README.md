# PrUn-Tracker

**PrUn-Tracker** is a data analysis pipeline for the game Prosperous Universe. It automates the process of fetching, processing, and analyzing in-game economic data, then uploads the results to Google Sheets for easy viewing and further analysis.

---

## Folder Structure

PrUn-Tracker/  
├── .gitignore                  # Git ignore rules  
├── pyrightconfig.json          # Pyright type checker config  
├── README.md                   # Project documentation  
├── ROOT_CLEANUP_ANALYSIS.md    # Notes/analysis for project cleanup  
├── pu-tracker/                 # Main project code and data  
│   ├── .env                    # Environment variables for local config  
│   ├── main_enhanced.py        # Enhanced data processing entry point  
│   ├── remove_duplicates.bat   # Batch script to clean duplicate files  
│   ├── run_pipeline.bat        # Main pipeline runner (calls main.py)  
│   ├── writer_profiles.json    # Config for data uploaders  
│   ├── cache/                  # Intermediate and final data files (CSV/JSON)  
│   │   ├── buildings.csv/json, categories.json, chains.json, ...  
│   │   ├── daily_analysis.csv, daily_analysis_enhanced.csv, daily_report.csv  
│   │   ├── market_data.csv, materials.csv, prices_all.csv, ...  
│   │   ├── recipes.json, recipe_inputs.csv, recipe_outputs.csv  
│   │   ├── tickers.json, tiers.json, workforces.csv  
│   ├── data/                   # Historical and persistent data (DB/JSON)  
│   │   ├── historical_data_condensed.json  
│   │   └── prosperous_universe.db  
│   ├── historical_data/        # All pipeline scripts and helpers  
│   │   ├── main.py, catch_data.py, process_data.py, upload_data.py, ...  
│   │   ├── data_analyzer.py, enhanced_analysis.py, ...  
│   │   ├── sheets_manager.py, rate_limiter.py, ...  
│   │   └── __pycache__/  
│   ├── logs/                   # Log files from pipeline runs  
│   └── (other folders/files)   # Additional supporting files  
├── tests/                      # Test suites and unit tests  
│   ├── __init__.py  
│   ├── test_comprehensive.py  
│   └── unit/  
└── utils/                      # Utility scripts and helpers  

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
- **Testing:** The `tests/` folder contains comprehensive and unit tests to ensure reliability.

For more details, see the docstrings in each script and the comments
