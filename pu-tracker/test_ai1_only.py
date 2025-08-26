"""
Test uploading only Report AI1 with rate limiting
"""
import os
import sys
import pandas as pd
import time

def test_report_ai1_only():
    print("=== TESTING REPORT AI1 UPLOAD ONLY ===")
    
    os.chdir(r"c:\Users\Usuario\Documents\GitHub\PrUn-Tracker - copia\pu-tracker")
    sys.path.insert(0, os.getcwd())
    
    try:
        from historical_data.upload_data import upload_advanced_analysis
        import gspread
        from historical_data.config import CONFIG
        
        # Load data
        df = pd.read_csv("cache/daily_analysis.csv")
        ai1_data = df[df['exchange'] == 'AI1'].copy()
        print(f"✅ Loaded AI1 data: {len(ai1_data)} materials")
        
        # Connect to Google Sheets
        gc = gspread.service_account(filename=CONFIG['GOOGLE_SERVICE_ACCOUNT_FILE'])
        spreadsheet = gc.open_by_key(CONFIG['TARGET_SPREADSHEET_ID'])
        print(f"✅ Connected to: {spreadsheet.title}")
        
        # Create a filtered DataFrame with just AI1 data
        ai1_df = df[df['exchange'] == 'AI1'].copy()
        
        print(f"✅ Uploading Report AI1 with {len(ai1_df)} materials...")
        
        # Upload only AI1 report
        upload_advanced_analysis(spreadsheet, ai1_df)
        
        print("✅ Report AI1 upload completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_report_ai1_only()
