# PrUn-Tracker - Reorganized Structure

## Overview
All core functionality has been moved to the `historical_data/` folder for better organization. Testing files remain in the root directory for easy access during development.

## New Structure

### Core Files (in historical_data/)
- `catch_data.py` - Data collection entry point
- `process_data.py` - Data processing entry point  
- `upload_data.py` - Data upload entry point
- All supporting modules and configuration files

### Entry Points
- `main.py` - New unified entry point with command options
- `run_pipeline.bat` - Updated batch file using new main.py

## Usage

### Command Line
```bash
# Run individual steps
python main.py catch    # Data collection only
python main.py process  # Data processing only
python main.py upload   # Data upload only
python main.py full     # Complete pipeline

# Or use the batch file
run_pipeline.bat
```

### Direct Module Access
```python
# Import from historical_data
from historical_data.catch_data import main as catch_main
from historical_data.process_data import main as process_main
from historical_data.upload_data import main as upload_main
```

## Changes Made

1. **File Relocation**: Core files moved to `historical_data/` folder
2. **Import Updates**: All imports updated to use relative imports within historical_data
3. **Path Adjustments**: Cache and config paths adjusted for new structure
4. **Deduplication**: Removed duplicate credential files
5. **Entry Point**: New `main.py` provides unified access to all functions

## Benefits

- **Better Organization**: Core functionality consolidated in one folder
- **Cleaner Root**: Testing files separated from core functionality
- **Easier Imports**: Consistent import structure within historical_data
- **No Duplicates**: Removed duplicate files and imports
- **Backwards Compatibility**: Batch file still works with new structure

## Testing Files
All test files remain in the root directory for easy development access:
- `test_*.py` files
- `debug_*.py` files  
- `analyze_*.py` files
- Development and verification scripts
