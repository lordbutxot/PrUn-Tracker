#!/usr/bin/env python3
"""
Debug script to identify why Google Sheets upload isn't working correctly.
This will test each step of the upload process.
"""

import sys
import os
import pandas as pd
import json
import gspread
from pathlib import Path

# Add pu-tracker to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pu-tracker'))

def check_data_availability():
    """Check if processed data is available"""
    print("=== STEP 1: CHECKING DATA AVAILABILITY ===")
    
    cache_dir = Path("pu-tracker/cache")
    daily_report_path = cache_dir / "daily_report.csv"
    
    if not daily_report_path.exists():
        print(f"❌ FAILED: {daily_report_path} does not exist")
        return None
    
    df = pd.read_csv(daily_report_path)
    print(f"✅ Data loaded: {len(df)} rows")
    print(f"✅ Columns: {list(df.columns)}")
    
    # Check for category and tier data
    if 'category' in df.columns:
        unique_categories = df['category'].nunique()
        print(f"✅ Category column found with {unique_categories} unique values")
        print(f"   Sample categories: {df['category'].value_counts().head(3).to_dict()}")
    else:
        print("❌ FAILED: No 'category' column found")
    
    if 'tier' in df.columns:
        unique_tiers = df['tier'].nunique()
        print(f"✅ Tier column found with {unique_tiers} unique values")
        print(f"   Sample tiers: {df['tier'].value_counts().head().to_dict()}")
    else:
        print("❌ FAILED: No 'tier' column found")
    
    # Check AI1 data specifically
    ai1_data = df[df['exchange'] == 'AI1']
    print(f"✅ AI1 data: {len(ai1_data)} rows")
    if len(ai1_data) > 0:
        print(f"   Sample AI1 rows with category/tier:")
        for idx, row in ai1_data.head(3).iterrows():
            print(f"   {row.get('ticker', 'N/A')} - Category: {row.get('category', 'N/A')}, Tier: {row.get('tier', 'N/A')}")
    
    return df

def check_authentication():
    """Check Google Sheets authentication"""
    print("\n=== STEP 2: CHECKING AUTHENTICATION ===")
    
    try:
        from historical_data.config import CONFIG
        print("✅ Config loaded successfully")
        
        # Check if service account file exists
        service_account_path = CONFIG.get('GOOGLE_SERVICE_ACCOUNT_FILE')
        if service_account_path and os.path.exists(service_account_path):
            print(f"✅ Service account file found: {service_account_path}")
        else:
            print(f"❌ FAILED: Service account file not found: {service_account_path}")
            return None
        
        # Try to authenticate
        gc = gspread.service_account(filename=service_account_path)
        print("✅ Authentication successful")
        
        # Try to open the spreadsheet
        spreadsheet_id = CONFIG.get('TARGET_SPREADSHEET_ID')
        if not spreadsheet_id:
            print("❌ FAILED: No TARGET_SPREADSHEET_ID in config")
            return None
        
        spreadsheet = gc.open_by_key(spreadsheet_id)
        print(f"✅ Spreadsheet opened: {spreadsheet.title}")
        
        # List all worksheets
        worksheets = spreadsheet.worksheets()
        print(f"✅ Found {len(worksheets)} worksheets:")
        for ws in worksheets:
            print(f"   - {ws.title}")
        
        return gc, spreadsheet
        
    except Exception as e:
        print(f"❌ FAILED: Authentication error: {e}")
        return None

def check_worksheet_structure(spreadsheet):
    """Check the DATA AI1 worksheet structure"""
    print("\n=== STEP 3: CHECKING WORKSHEET STRUCTURE ===")
    
    try:
        worksheet = spreadsheet.worksheet('DATA AI1')
        print("✅ DATA AI1 worksheet found")
        
        # Get the header row
        headers = worksheet.row_values(1)
        print(f"✅ Current headers: {headers}")
        
        # Check if category and tier columns exist
        if 'category' in headers or 'Category' in headers:
            print("✅ Category column exists in headers")
        else:
            print("❌ FAILED: No category column in headers")
        
        if 'tier' in headers or 'Tier' in headers:
            print("✅ Tier column exists in headers")
        else:
            print("❌ FAILED: No tier column in headers")
        
        # Get some data rows to see what's actually there
        all_values = worksheet.get_all_values()
        print(f"✅ Total rows in sheet: {len(all_values)}")
        
        if len(all_values) > 1:
            print("✅ Sample data rows:")
            for i, row in enumerate(all_values[1:4]):  # First 3 data rows
                print(f"   Row {i+2}: {row}")
        
        return worksheet
        
    except Exception as e:
        print(f"❌ FAILED: Worksheet error: {e}")
        return None

def test_upload_process(df, spreadsheet):
    """Test the actual upload process"""
    print("\n=== STEP 4: TESTING UPLOAD PROCESS ===")
    
    try:
        # Get AI1 data
        ai1_data = df[df['exchange'] == 'AI1'].copy()
        
        if len(ai1_data) == 0:
            print("❌ FAILED: No AI1 data to upload")
            return False
        
        print(f"✅ Preparing to upload {len(ai1_data)} AI1 rows")
        
        # Check what columns we have
        print(f"✅ Available columns: {list(ai1_data.columns)}")
        
        # Get or create worksheet
        try:
            worksheet = spreadsheet.worksheet('DATA AI1')
            print("✅ Using existing DATA AI1 worksheet")
        except:
            worksheet = spreadsheet.add_worksheet(title='DATA AI1', rows=1000, cols=20)
            print("✅ Created new DATA AI1 worksheet")
        
        # Prepare data for upload
        # Make sure we include category and tier
        upload_columns = ['ticker', 'category', 'tier', 'supply', 'demand', 'price', 'price_average', 'shipped', 'availability']
        
        # Check which columns exist
        existing_columns = []
        for col in upload_columns:
            if col in ai1_data.columns:
                existing_columns.append(col)
                print(f"✅ Column {col} available for upload")
            else:
                print(f"❌ Column {col} NOT available for upload")
        
        if len(existing_columns) == 0:
            print("❌ FAILED: No valid columns for upload")
            return False
        
        # Prepare upload data
        upload_data = ai1_data[existing_columns].copy()
        
        # Convert to list of lists for gspread
        headers = existing_columns
        data_rows = upload_data.values.tolist()
        
        print(f"✅ Upload data prepared: {len(data_rows)} rows, {len(headers)} columns")
        print(f"✅ Headers: {headers}")
        print(f"✅ Sample row: {data_rows[0] if data_rows else 'No data'}")
        
        # Clear existing data and upload new
        worksheet.clear()
        
        # Upload headers
        worksheet.append_row(headers)
        print("✅ Headers uploaded")
        
        # Upload data in batches
        batch_size = 100
        for i in range(0, len(data_rows), batch_size):
            batch = data_rows[i:i+batch_size]
            for row in batch:
                worksheet.append_row(row)
            print(f"✅ Uploaded batch {i//batch_size + 1}/{(len(data_rows)-1)//batch_size + 1}")
        
        print("✅ Upload completed successfully")
        
        # Verify upload
        uploaded_values = worksheet.get_all_values()
        print(f"✅ Verification: Sheet now has {len(uploaded_values)} rows")
        
        if len(uploaded_values) > 1:
            print("✅ Verification sample:")
            for i, row in enumerate(uploaded_values[1:4]):
                print(f"   Row {i+2}: {row}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Upload error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run complete debug process"""
    print("🔍 DEBUGGING GOOGLE SHEETS UPLOAD PROCESS\n")
    
    # Step 1: Check data
    df = check_data_availability()
    if df is None:
        print("\n❌ STOPPING: Data not available")
        return
    
    # Step 2: Check authentication
    auth_result = check_authentication()
    if auth_result is None:
        print("\n❌ STOPPING: Authentication failed")
        return
    
    gc, spreadsheet = auth_result
    
    # Step 3: Check worksheet structure
    worksheet = check_worksheet_structure(spreadsheet)
    
    # Step 4: Test upload
    upload_success = test_upload_process(df, spreadsheet)
    
    if upload_success:
        print("\n✅ DEBUG COMPLETE: Upload should be working")
        print("Check your Google Sheets DATA AI1 tab now!")
    else:
        print("\n❌ DEBUG COMPLETE: Upload failed")

if __name__ == "__main__":
    main()
