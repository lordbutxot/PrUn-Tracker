#!/usr/bin/env python3
"""
Upload planet resources data to Google Sheets for Price Analyser planet selection feature.
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
SHEET_NAME = 'Planet Resources'


def upload_planet_resources():
    """
    Upload planetresources.csv to Google Sheets.
    """
    print("\n" + "=" * 60)
    print("   Planet Resources Upload to Google Sheets")
    print("=" * 60)
    
    # Check if planetresources.csv exists
    planetresources_path = CACHE_DIR / "planetresources.csv"
    
    if not planetresources_path.exists():
        print(f"[ERROR] planetresources.csv not found at {planetresources_path}")
        print("[INFO] Run the main pipeline first to fetch planet resources data")
        return False
    
    # Load planet resources data
    print(f"[STEP] Loading planet resources from {planetresources_path}")
    df = pd.read_csv(planetresources_path)
    print(f"[INFO] Loaded {len(df)} planet resource records")
    print(f"[INFO] Columns: {list(df.columns)}")
    
    # Show sample data
    print("\n[INFO] Sample data (first 5 rows):")
    print(df.head())
    
    # Initialize Google Sheets manager
    print("\n[STEP] Initializing Google Sheets connection...")
    sheets_manager = SheetsManager()
    
    # Upload to Google Sheets
    print(f"[STEP] Uploading to '{SHEET_NAME}' sheet...")
    try:
        # Use upload_to_sheet method instead
        sheets_manager.upload_to_sheet(SPREADSHEET_ID, SHEET_NAME, df, clear_first=True)
        
        print(f"[SUCCESS] Uploaded {len(df)} rows to '{SHEET_NAME}' sheet")
        print(f"[INFO] Sheet URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        return True
            
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    try:
        success = upload_planet_resources()
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
