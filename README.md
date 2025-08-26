# PrUn-Tracker
Prosperous Universe Data Analyser


Hello!
I have the following;

I have several python scripts and programs that fetch info from source apis to deliver calculations and stamp it in 2 google spreadsheets, one named ONN_Historical_Data (Timestamps and data for that day) and another named PrUn Calculator (Daily overview reports).

These are for a game called Prosperous Universe about space capitalism in essence.

The folder structure is:

The folder structure is:

|   debug_csv_columns.py
|   historical_data_manager.py
|   pipeline.log
|   prun-profit-7e0c3bafd690.json
|   structure.txt
|   writer_profiles.json
|   
+---cache
|       buildings.json
|       categories.json
|       chains.json
|       daily_report.csv
|       data_sheets_cache.json
|       market_data.csv
|       materials.csv
|       prices_all.csv
|       processed_data.csv
|       recipes.json
|       tickers.json
|       tier0_resources.json
|       tiers.json
|       
+---data
|       historical_data_condensed.json
|       prosperous_universe.db
|       
+---historical_data
|   |   add_tier_to_materials.py
|   |   chain_dictionary_generator.py
|   |   config.py
|   |   data_analysis.py
|   |   data_collection.py
|   |   data_processor.py
|   |   db_manager.py
|   |   dictionary_builder_buildings.py
|   |   fetch_all_tickers.py
|   |   fetch_materials.py
|   |   formatting_config.py
|   |   main.py
|   |   main_refresh_basics.py
|   |   prun-profit-7e0c3bafd690.json
|   |   report_builder.py
|   |   sheets_api.py
|   |   sheet_updater.py
|   |   __init__.py
|   |   
|   \---__pycache__
|           add_tier_to_materials.cpython-313.pyc
|           chain_dictionary_generator.cpython-313.pyc
|           config.cpython-313.pyc
|           data_analysis.cpython-313.pyc
|           data_collection.cpython-313.pyc
|           data_processor.cpython-313.pyc
|           db_manager.cpython-313.pyc
|           dictionary_builder_buildings.cpython-313.pyc
|           fetch_all_tickers.cpython-313.pyc
|           fetch_materials.cpython-313.pyc
|           formatting_config.cpython-313.pyc
|           report_builder.cpython-313.pyc
|           sheets_api.cpython-313.pyc
|           sheet_updater.cpython-313.pyc
|           __init__.cpython-313.pyc
|           
+---onn_data
|   |   onn_article_generator.py
|   |   __init__.py
|   |   
|   \---__pycache__
|           onn_article_generator.cpython-313.pyc
|           
\---__pycache__
        data_analysis.cpython-313.pyc
        
