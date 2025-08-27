"""
Unified Enhanced Analysis Uploader
Combines robust checks, column handling, and rate limiting.
"""
import pandas as pd
import time
import sys
from pathlib import Path

# Import your preferred Sheets manager
try:
    from sheets_manager import UnifiedSheetsManager as SheetsManager
    SHEETS_AVAILABLE = True
except ImportError:
    try:
        from sheets_manager import SheetsManager
        SHEETS_AVAILABLE = True
    except ImportError as e:
        print(f"⚠️  Import error: {e}")
        SHEETS_AVAILABLE = False

REQUIRED_HEADERS = [
    'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe', 'Amount per Recipe',
    'Weight', 'Volume', 'Current Price', 'Input Cost per Unit', 'Input Cost per Stack',
    'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %',
    'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap',
    'Liquidity Ratio', 'Investment Score', 'Risk Level', 'Volatility'
]
EXCHANGE_TABS = ['DATA AI1', 'DATA CI1', 'DATA CI2', 'DATA IC1', 'DATA NC1', 'DATA NC2']
SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"

class UnifiedAnalysisUploader:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.cache_path = self.base_path / 'cache'
        self.sheets_manager = None

    def check_prerequisites(self) -> bool:
        if not SHEETS_AVAILABLE:
            print("❌ SheetsManager not available")
            return False
        enhanced_file = self.cache_path / 'daily_analysis_enhanced.csv'
        if not enhanced_file.exists():
            print(f"❌ Enhanced analysis file missing: {enhanced_file}")
            print("   📝 Run: python historical_data/data_analyzer.py")
            return False
        creds_file = Path(__file__).parent / 'prun-profit-7e0c3bafd690.json'
        if not creds_file.exists():
            print(f"❌ Credentials file missing: {creds_file}")
            return False
        return True

    def initialize_sheets_manager(self) -> bool:
        try:
            print("🔄 Initializing Google Sheets connection...")
            self.sheets_manager = SheetsManager()
            # Only call connect if it exists
            connect_method = getattr(self.sheets_manager, "connect", None)
            if callable(connect_method):
                connected = connect_method()
                if not connected:
                    print("❌ Failed to connect to Google Sheets")
                    return False
                print("✅ Connected to Google Sheets")
            else:
                print("✅ SheetsManager initialized (auto-connect)")
            return True
        except Exception as e:
            print(f"❌ SheetsManager error: {e}")
            return False

    def upload_to_sheets(self, df: pd.DataFrame) -> bool:
        if not self.sheets_manager:
            if not self.initialize_sheets_manager():
                return False
        if not self.sheets_manager:
            print("❌ SheetsManager initialization failed")
            return False
        success_count = 0
        for tab_name in EXCHANGE_TABS:
            try:
                print(f"Uploading to {tab_name}...")
                # Try upload_dataframe_to_sheet first, fallback to upload_to_sheet
                upload_df_method = getattr(self.sheets_manager, "upload_dataframe_to_sheet", None)
                upload_sheet_method = getattr(self.sheets_manager, "upload_to_sheet", None)
                if callable(upload_df_method):
                    success = upload_df_method(tab_name, df)
                elif callable(upload_sheet_method):
                    success = upload_sheet_method(SPREADSHEET_ID, tab_name, df)
                else:
                    print("❌ No valid upload method found in SheetsManager")
                    success = False
                if success:
                    print(f"✅ Uploaded to {tab_name}")
                    success_count += 1
                else:
                    print(f"❌ Failed to upload to {tab_name}")
                time.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"Upload error for {tab_name}: {e}")
        print(f"\n📊 Upload Summary: {success_count}/{len(EXCHANGE_TABS)} tabs successful")
        return success_count > 0

def main() -> bool:
    print("🚀 Unified Enhanced Analysis Uploader")
    print("=" * 60)
    uploader = UnifiedAnalysisUploader()
    if not uploader.check_prerequisites():
        print("❌ Prerequisites not met")
        return False
    enhanced_file = uploader.cache_path / 'daily_analysis_enhanced.csv'
    try:
        df = pd.read_csv(enhanced_file)
        print(f"✅ Loaded enhanced data: {len(df)} rows, {len(df.columns)} columns")
        df = df[REQUIRED_HEADERS]  # Ensure correct column order
    except Exception as e:
        print(f"❌ Error loading enhanced data: {e}")
        return False
    print(f"\n📊 Data Summary:")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   Required: {len(REQUIRED_HEADERS)} columns")
    print(f"   Target tabs: {len(EXCHANGE_TABS)}")
    if SHEETS_AVAILABLE:
        return uploader.upload_to_sheets(df)
    else:
        print("❌ SheetsManager not available")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)