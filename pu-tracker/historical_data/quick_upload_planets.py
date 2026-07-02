#!/usr/bin/env python3
"""Quick upload of planet resources to Google Sheets"""

import pandas as pd
import gspread
import time
from google.oauth2.service_account import Credentials
from pathlib import Path

# Setup
cache_dir = Path(__file__).parent.parent / "cache"
creds_file = Path(__file__).parent / "prun-profit-42c5889f620d.json"
spreadsheet_id = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
sheet_name = "Planet Resources"

# Load data
print(f"Loading data from {cache_dir / 'planetresources.csv'}...")
df = pd.read_csv(cache_dir / "planetresources.csv")
print(f"[OK] Loaded {len(df)} rows, {len(df.columns)} columns")

# Connect to Google Sheets
print("Connecting to Google Sheets...")
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(str(creds_file), scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(spreadsheet_id)
print("[OK] Connected")

# Get or create sheet
print(f"Checking for '{sheet_name}' sheet...")
try:
    worksheet = spreadsheet.worksheet(sheet_name)
    print(f"[OK] Sheet exists, clearing...")
    worksheet.clear()
except gspread.exceptions.WorksheetNotFound:
    print(f"[OK] Creating new sheet...")
    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=len(df)+100, cols=10)

# Upload data in batches (Google Sheets API has a 10MB limit per request)
print("Uploading data (this may take a minute)...")
data = [df.columns.values.tolist()] + df.values.tolist()

# Use batch update for better performance
batch_size = 1000
total_rows = len(data)
print(f"Uploading {total_rows} rows in batches of {batch_size}...")

for i in range(0, total_rows, batch_size):
    batch_end = min(i + batch_size, total_rows)
    batch_data = data[i:batch_end]
    
    # Calculate range (A1 notation)
    start_row = i + 1
    end_row = batch_end
    range_name = f'A{start_row}:E{end_row}'
    
    print(f"  Uploading rows {start_row}-{end_row}...")
    worksheet.update(range_name=range_name, values=batch_data, value_input_option='RAW')
    
    # Small delay to avoid rate limiting
    if batch_end < total_rows:
        time.sleep(1)

print(f"[SUCCESS] Uploaded {len(df)} rows to '{sheet_name}'")
print(f"[INFO] URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
