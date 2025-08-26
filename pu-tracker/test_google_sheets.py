#!/usr/bin/env python3

import pandas as pd
import os
import sys

print("Testing upload functionality...")

# Check if daily report exists and has correct structure
cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
report_path = os.path.join(cache_dir, "daily_report.csv")

if not os.path.exists(report_path):
    print("❌ Daily report not found")
    sys.exit(1)

# Load the data
report_df = pd.read_csv(report_path)
print(f"✅ Loaded daily report with {len(report_df)} rows")
print(f"✅ Columns: {list(report_df.columns)}")

# Check exchange data
if 'exchange' in report_df.columns:
    exchanges = report_df['exchange'].unique()
    print(f"✅ Found exchanges: {list(exchanges)}")
    
    for exchange in exchanges:
        exchange_data = report_df[report_df['exchange'] == exchange]
        print(f"   {exchange}: {len(exchange_data)} rows")
        
        # Show sample data
        if len(exchange_data) > 0:
            sample = exchange_data.iloc[0]
            print(f"   Sample: {sample['Ticker']} - {sample['Category']} - Tier {sample['Tier']}")
else:
    print("❌ No exchange column found")
    sys.exit(1)

# Test Google Sheets authentication
try:
    import gspread
    from historical_data.config import CONFIG
    
    print("Testing Google Sheets authentication...")
    service_account_file = CONFIG['GOOGLE_SERVICE_ACCOUNT_FILE']
    
    if not os.path.exists(service_account_file):
        print(f"❌ Credentials file not found at: {service_account_file}")
        sys.exit(1)
    
    gc = gspread.service_account(filename=service_account_file)
    print("✅ Authenticated with Google Sheets")
    
    # Test opening spreadsheet
    spreadsheet_id = CONFIG['TARGET_SPREADSHEET_ID']
    spreadsheet = gc.open_by_key(spreadsheet_id)
    print(f"✅ Opened spreadsheet: {spreadsheet.title}")
    
    # List existing worksheets
    worksheets = spreadsheet.worksheets()
    print(f"✅ Found {len(worksheets)} worksheets:")
    for ws in worksheets:
        print(f"   - {ws.title}")

except Exception as e:
    print(f"❌ Google Sheets error: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed!")
