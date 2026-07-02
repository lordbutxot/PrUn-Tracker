"""
Upload planet fertility data to Google Sheets.
Fertility data affects farming building (FRM, ORC, VIN) production times.
"""

import os
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sheets_manager import SheetsManager

# Configuration
CACHE_DIR = Path(__file__).parent.parent / "cache"
SPREADSHEET_ID = os.getenv('PRUN_SPREADSHEET_ID', '1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI')
SHEET_NAME = 'Planet Fertility'


def upload_planet_fertility():
    """
    Upload planet_fertility.csv to Google Sheets.
    Creates or updates the "Planet Fertility" tab.
    """
    print("\n" + "=" * 60)
    print("   Planet Fertility Upload to Google Sheets")
    print("=" * 60)
    
    # Check if planet_fertility.csv exists
    fertility_path = CACHE_DIR / "planet_fertility.csv"
    
    if not fertility_path.exists():
        print(f"[WARN] planet_fertility.csv not found at {fertility_path}")
        print("[INFO] Skipping fertility upload - farming will use default values")
        return False
    
    try:
        print(f"[STEP] Loading planet fertility from {fertility_path}")
        df = pd.read_csv(fertility_path)
        
        if df.empty:
            print("[WARN] planet_fertility.csv is empty")
            return False
        
        print(f"[INFO] Loaded {len(df)} planets with fertility data")
        print(f"[INFO] Columns: {list(df.columns)}")
        
        # Show sample data
        print("\n[INFO] Sample data (first 5 rows):")
        print(df.head())
        
        # Initialize SheetsManager
        print("\n[STEP] Initializing Google Sheets connection...")
        sheets_manager = SheetsManager()
        
        # Upload to Google Sheets
        print(f"[STEP] Uploading to '{SHEET_NAME}' sheet...")
        sheets_manager.upload_to_sheet(SPREADSHEET_ID, SHEET_NAME, df, clear_first=True)
        
        print(f"[SUCCESS] Uploaded {len(df)} rows to '{SHEET_NAME}' sheet")
        print(f"[INFO] Sheet URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to upload planet fertility: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    try:
        success = upload_planet_fertility()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
