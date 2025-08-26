# Deprecated Files and Folders Analysis

## 🗑️ DEPRECATED FOLDERS TO DELETE

### 1. `/historical_data/analysis/` 
- **Files**: `market_analyzer.py`
- **Reason**: No imports found, functionality merged into main modules

### 2. `/historical_data/cache/`
- **Files**: `cache_manager.py` 
- **Reason**: No imports found, cache functionality handled by main modules

### 3. `/historical_data/collectors/`
- **Files**: 
  - `market_data_collector.py`
  - `material_data_collector.py` 
  - `recipe_data_collector.py`
  - `__init__.py`
- **Reason**: No imports found, replaced by individual fetch modules

### 4. `/historical_data/database/`
- **Files**:
  - `connection_manager.py`
  - `price_data_repository.py`
  - `schema_manager.py`
- **Reason**: No imports found, `db_manager.py` handles database operations

### 5. `/historical_data/orchestration/`
- **Files**:
  - `pipeline_coordinator.py`
  - `stage_manager.py`
  - `__init__.py`
- **Reason**: No imports found, replaced by `main.py` entry point

### 6. `/historical_data/reports/`
- **Files**: `historical_report_builder.py`
- **Reason**: No imports found, functionality in `report_builder.py`

### 7. `/historical_data/sheets/`
- **Files**:
  - `batch_uploader.py`
  - `sheets_client.py`
  - `__init__.py`
- **Reason**: Only internal imports within sheets/, but no external usage found

### 8. `/monitoring/`
- **Files**:
  - `error_handler.py`
  - `metrics_collector.py`
  - `__init__.py`
- **Reason**: No imports found anywhere in codebase

### 9. `/onn_data/`
- **Files**:
  - `onn_article_generator.py`
  - `__init__.py`
  - `__pycache__/`
- **Reason**: No imports found, appears to be standalone feature

### 10. `/utils/`
- **Files**:
  - `data_transformers.py`
  - `__init__.py`
- **Reason**: No imports found, functionality likely moved to main modules

## 🗑️ DEPRECATED ROOT FILES TO DELETE

### 1. Core Files (Superseded)
- `historical_data_manager.py` - Appears to be old version of data management
- `debug_*.py` files - Development/debugging scripts
- `analyze_*.py` files - Analysis scripts not used in pipeline
- `compare_analysis.py` - Comparison utility
- `fix_daily_analysis.py` - Fix script
- `simple_*.py` files - Simplified test scripts
- `verify_sheets.py` - Verification script
- `direct_upload_minimal.py` - Alternative upload script

### 2. Retry/Alternative Implementations
- `upload_with_retry.py` - Alternative upload implementation
- `restart_panic_button.py` - Emergency restart script
- `restart_panic_button.txt` - Instructions file

## 🔍 USED MODULES (KEEP)

### Essential Pipeline Files:
- `historical_data/catch_data.py` ✅
- `historical_data/process_data.py` ✅  
- `historical_data/upload_data.py` ✅
- `historical_data/report_builder.py` ✅
- `historical_data/data_processor.py` ✅
- `historical_data/data_analysis.py` ✅

### Core Supporting Modules:
- `historical_data/fetch_*.py` ✅
- `historical_data/main_refresh_basics.py` ✅
- `historical_data/config.py` ✅
- `historical_data/db_manager.py` ✅
- `historical_data/sheets_api.py` ✅
- Individual data collection modules ✅

### Keep for Development:
- `test_*.py` files ✅
- `main.py` ✅
- `run_pipeline.bat` ✅
- Documentation files ✅
- `cache/` directory ✅
- `data/` directory ✅
- `configuration/` directory ✅

## 📊 SUMMARY
- **Folders to delete**: 10 deprecated folders
- **Individual files to delete**: ~15 deprecated scripts
- **Total cleanup**: Removing unused/superseded code
- **Impact**: Cleaner codebase, easier maintenance
