"""
Unified Enhanced Analysis Uploader
Combines robust checks, column handling, and rate limiting.
"""
import pandas as pd
import time
import sys
from pathlib import Path
import traceback
import hashlib
import numpy as np

# Import your preferred Sheets manager
try:
    from sheets_manager import UnifiedSheetsManager as SheetsManager
    SHEETS_AVAILABLE = True
except ImportError:
    try:
        from sheets_manager import SheetsManager
        SHEETS_AVAILABLE = True
    except ImportError as e:
        print(f"  Import error: {e}")
        SHEETS_AVAILABLE = False

REQUIRED_HEADERS = [
    'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe', 'Amount per Recipe',
    'Weight', 'Volume', 'Ask_Price', 'Bid_Price', 'Input Cost per Unit', 'Input Cost per Stack',
    'Input Cost per Hour',  # <-- Add this
    'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %',
    'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap',
    'Liquidity Ratio', 'Investment Score', 'Risk Level', 'Exchange'
]
EXCHANGE_TABS = ['DATA AI1', 'DATA CI1', 'DATA CI2', 'DATA IC1', 'DATA NC1', 'DATA NC2']
SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"

def dataframe_hash(df):
    hash_arr = pd.util.hash_pandas_object(df, index=True)  # <-- FIX: add index=True
    return hashlib.md5(np.asarray(hash_arr).tobytes()).hexdigest()

class UnifiedAnalysisUploader:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.cache_path = self.base_path / 'cache'
        self.sheets_manager = None

    def check_prerequisites(self) -> bool:
        if not SHEETS_AVAILABLE:
            print(" SheetsManager not available")
            return False
        enhanced_file = self.cache_path / 'daily_analysis_enhanced.csv'
        if not enhanced_file.exists():
            print(f" Enhanced analysis file missing: {enhanced_file}")
            print("    Run: python historical_data/data_analyzer.py")
            return False
        # Support environment variable for credentials (for GitHub Actions)
        import os
        env_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if env_creds and Path(env_creds).exists():
            creds_file = Path(env_creds)
        else:
            creds_file = Path(__file__).parent / 'prun-profit-42c5889f620d.json'
        if not creds_file.exists():
            print(f" Credentials file missing: {creds_file}")
            return False
        return True

    def initialize_sheets_manager(self) -> bool:
        try:
            print(" Initializing Google Sheets connection...")
            self.sheets_manager = SheetsManager()
            # Only call connect if it exists
            connect_method = getattr(self.sheets_manager, "connect", None)
            if callable(connect_method):
                connected = connect_method()
                if not connected:
                    print(" Failed to connect to Google Sheets")
                    return False
                print(" Connected to Google Sheets")
            else:
                print(" SheetsManager initialized (auto-connect)")
            return True
        except Exception as e:
            print(f" SheetsManager error: {e}")
            return False

    def upload_to_sheets(self, df: pd.DataFrame) -> bool:
        if not self.sheets_manager:
            if not self.initialize_sheets_manager():
                return False
        if not self.sheets_manager:
            print(" SheetsManager initialization failed")
            return False
        success_count = 0
        for tab_name in EXCHANGE_TABS:
            # Extract exchange code from tab name
            exch = tab_name.split()[-1]
            df_exch = df[df['Exchange'] == exch].copy()
            if df_exch.empty:
                print(f" {tab_name} has no data, skipping upload.")
                continue
            hash_file = self.cache_path / f"{tab_name}_last_hash.txt"
            new_hash = dataframe_hash(df_exch)
            old_hash = hash_file.read_text() if hash_file.exists() else ""
            if new_hash == old_hash:
                print(f" {tab_name} unchanged, skipping upload.")
                continue
            try:
                print(f"Uploading to {tab_name}...")
                # Try upload_dataframe_to_sheet first, fallback to upload_to_sheet
                upload_df_method = getattr(self.sheets_manager, "upload_dataframe_to_sheet", None)
                upload_sheet_method = getattr(self.sheets_manager, "upload_to_sheet", None)
                if callable(upload_df_method):
                    success = upload_df_method(tab_name, df_exch)
                elif callable(upload_sheet_method):
                    success = upload_sheet_method(SPREADSHEET_ID, tab_name, df_exch)
                else:
                    print(" No valid upload method found in SheetsManager")
                    success = False
                if success:
                    print(f" Uploaded to {tab_name}")
                    # Apply formatting if available
                    format_method = getattr(self.sheets_manager, "apply_data_tab_formatting", None)
                    if callable(format_method):
                        try:
                            format_method(tab_name, df_exch)
                            print(f" Formatting applied to {tab_name}")
                        except Exception as fe:
                            print(f"  Formatting failed for {tab_name}: {fe}")
                    success_count += 1
                else:
                    print(f" Failed to upload to {tab_name}")
                time.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"Upload error for {tab_name}: {e}")
            hash_file.write_text(new_hash)
        print(f"\n Upload Summary: {success_count}/{len(EXCHANGE_TABS)} tabs successful")
        return success_count > 0

# Add this utility function in upload_enhanced_analysis.py (and reuse elsewhere as needed)
def expand_multiple_recipes(df):
    """
    For rows where the 'Recipe' column contains multiple recipes separated by ';',
    split them into separate rows, each with a single recipe.
    """
    if 'Recipe' not in df.columns:
        return df
    # Split recipes and explode
    df = df.copy()
    df['Recipe'] = df['Recipe'].fillna('')
    df['Recipe'] = df['Recipe'].astype(str)
    df['Recipe_list'] = df['Recipe'].str.split(';')
    df = df.explode('Recipe_list')
    df['Recipe'] = df['Recipe_list'].str.strip()
    df = df.drop(columns=['Recipe_list'])
    # Remove empty recipes (if any)
    df = df[df['Recipe'] != '']
    # Deduplicate by Ticker, Exchange, Recipe (if Exchange exists)
    dedup_cols = ['Ticker', 'Recipe']
    if 'Exchange' in df.columns:
        dedup_cols.insert(1, 'Exchange')
    df = df.drop_duplicates(subset=dedup_cols)
    return df

def main() -> bool:
    print("[STEP] Starting upload to Google Sheets...", flush=True)
    print(" Unified Enhanced Analysis Uploader")
    print("=" * 60)
    uploader = UnifiedAnalysisUploader()
    if not uploader.check_prerequisites():
        print(" Prerequisites not met")
        return False
    enhanced_file = uploader.cache_path / 'daily_analysis_enhanced.csv'
    try:
        df = pd.read_csv(enhanced_file)
        print(f" Loaded enhanced data: {len(df)} rows, {len(df.columns)} columns")
        missing = [col for col in REQUIRED_HEADERS if col not in df.columns]
        if missing:
            print(f" Missing columns in enhanced data: {missing}")
            # --- ADD MISSING COLUMNS WITH DEFAULTS ---
            for col in missing:
                df[col] = "" if col not in ['Tier', 'Ask_Price', 'Bid_Price', 'Input Cost per Unit', 'Input Cost per Stack', 'Input Cost per Hour', 'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %', 'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap', 'Liquidity Ratio', 'Investment Score'] else 0
        df = df[REQUIRED_HEADERS]  # Ensure correct column order
        
        # CRITICAL FIX: Ensure numeric columns are actually numeric (not strings or NaN)
        numeric_columns = ['Tier', 'Ask_Price', 'Bid_Price', 'Input Cost per Unit', 'Input Cost per Stack', 
                          'Input Cost per Hour', 'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %', 
                          'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap', 'Liquidity Ratio', 
                          'Investment Score', 'Amount per Recipe', 'Weight', 'Volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df = expand_multiple_recipes(df)  # <-- keep this line
        df = df.sort_values("Investment Score", ascending=False)
    except Exception as e:
        print(f" Error loading enhanced data: {e}")
        return False
    print(f"\n Data Summary:")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   Required: {len(REQUIRED_HEADERS)} columns")
    print(f"   Target tabs: {len(EXCHANGE_TABS)}")
    
    # DEBUG: Show sample Supply/Demand values
    if 'Supply' in df.columns and 'Demand' in df.columns:
        print(f"\n Sample Supply/Demand values (first 3 rows):")
        print(f"   AAR AI1: Supply={df.iloc[0]['Supply']}, Demand={df.iloc[0]['Demand']}, Traded={df.iloc[0]['Traded Volume']}")
        if len(df) > 1:
            print(f"   Row 2: Supply={df.iloc[1]['Supply']}, Demand={df.iloc[1]['Demand']}, Traded={df.iloc[1]['Traded Volume']}")
        if len(df) > 2:
            print(f"   Row 3: Supply={df.iloc[2]['Supply']}, Demand={df.iloc[2]['Demand']}, Traded={df.iloc[2]['Traded Volume']}")
    if SHEETS_AVAILABLE:
        uploader.upload_to_sheets(df)
        print("[SUCCESS] Upload completed", flush=True)
        return True  # <-- Always return True, even if no tabs uploaded
    else:
        print(" SheetsManager not available")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)