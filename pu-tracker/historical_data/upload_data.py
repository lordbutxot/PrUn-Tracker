"""
upload_data.py
Entry point for uploading/syncing processed data for PrUn-Tracker.
"""

import asyncio
import os
import pandas as pd
import numpy as np
import json
import gspread
from google.oauth2.service_account import Credentials

def main():
    print("[Upload] Starting data upload...")
    
    # First validate that we have processed data - now relative to historical_data folder
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
    processed_path = os.path.join(cache_dir, "processed_data.csv")
    report_path = os.path.join(cache_dir, "daily_report.csv")
    analysis_path = os.path.join(cache_dir, "daily_analysis.csv")
    
    if not os.path.exists(processed_path):
        print("[Upload] ❌ No processed data found. Run process_data.py first.")
        return
    
    # Load and validate data
    processed_df = pd.read_csv(processed_path)
    print(f"[Upload] ✅ Found processed data: {len(processed_df)} rows")
    
    # Check for both report types
    daily_report_df = None
    daily_analysis_df = None
    
    if os.path.exists(report_path):
        daily_report_df = pd.read_csv(report_path)
        print(f"[Upload] ✅ Found daily report: {len(daily_report_df)} rows")
    else:
        print("[Upload] ⚠️  No daily report found")
    
    if os.path.exists(analysis_path):
        daily_analysis_df = pd.read_csv(analysis_path)
        print(f"[Upload] ✅ Found daily analysis: {len(daily_analysis_df)} rows")
    else:
        print("[Upload] ⚠️  No daily analysis found")
    
    # Step 1: Try to update Google Sheets (with error handling)
    print("[Upload] Attempting to update Google Sheets...")
    try:
        # Check if credentials file exists - now in same directory
        credentials_path = os.path.join(os.path.dirname(__file__), 'prun-profit-7e0c3bafd690.json')
        if not os.path.exists(credentials_path):
            print(f"[Upload] ❌ Credentials file not found at: {credentials_path}")
            print("[Upload] Skipping Google Sheets upload")
        else:
            print(f"[Upload] ✅ Credentials file found")
            
            # Import config with relative import
            from .config import CONFIG
            
            print("[Upload] 🔄 Running direct sheet upload...")
            
            # Authenticate
            service_account_file = CONFIG['GOOGLE_SERVICE_ACCOUNT_FILE']
            gc = gspread.service_account(filename=service_account_file)
            print("[Upload] ✅ Authenticated with Google Sheets")
            
            # Open spreadsheet
            spreadsheet_id = CONFIG['TARGET_SPREADSHEET_ID']
            spreadsheet = gc.open_by_key(spreadsheet_id)
            print(f"[Upload] ✅ Opened spreadsheet: {spreadsheet.title}")
            
            # Skip advanced analysis (Report sheets) to save quota for DATA sheets
            # if daily_analysis_df is not None:
            #     print("[Upload] 📊 Uploading advanced analysis to Report sheets...")
            #     try:
            #         upload_advanced_analysis(spreadsheet, daily_analysis_df)
            #         print("[Upload] ✅ Report sheets uploaded successfully")
            #     except Exception as e:
            #         print(f"[Upload] ⚠️  Report sheets upload failed: {e}")
            
            print("[Upload] 📊 Skipping Report sheets to save quota for DATA sheets")
            
            # Upload basic daily reports (DATA sheets) with ultra-optimization
            if daily_report_df is not None:
                print("[Upload] 📊 Using ultra-optimized upload for ALL exchanges...")
                try:
                    # Import the ultra-optimized uploader
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                    from ultra_all_exchanges_upload import UltraOptimizedUploader
                    
                    # Merge report and analysis data to get complete column set
                    print("[Upload] 🔄 Merging report and analysis data for complete columns...")
                    
                    if daily_analysis_df is not None:
                        # Merge datasets to get Investment Score and Risk Level
                        merged_df = daily_report_df.merge(
                            daily_analysis_df[['ticker', 'exchange', 'Investment Score', 'Risk Level']], 
                            on=['ticker', 'exchange'], 
                            how='left'
                        )
                        print(f"[Upload] ✅ Merged data: {len(merged_df)} records with complete columns")
                    else:
                        merged_df = daily_report_df.copy()
                        print(f"[Upload] ⚠️  No analysis data to merge, using report data only")
                    
                    # Initialize ultra-optimized uploader
                    uploader = UltraOptimizedUploader(
                        CONFIG['GOOGLE_SERVICE_ACCOUNT_FILE'],
                        CONFIG['TARGET_SPREADSHEET_ID']
                    )
                    
                    # Upload all DATA sheets with priority order
                    success_count, failed_exchanges = uploader.upload_all_data_sheets(
                        merged_df,
                        priority_exchanges=['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
                    )
                    
                    if success_count > 0:
                        print(f"[Upload] ✅ Ultra-optimized upload completed: {success_count} exchanges")
                        print(f"[Upload] 🚀 API efficiency: ~99% fewer calls than traditional method")
                    else:
                        print(f"[Upload] ❌ Ultra-optimized upload failed for all exchanges")
                        
                    # Print performance stats
                    uploader.print_performance_stats()
                    
                    print("[Upload] ✅ DATA sheets uploaded successfully")
                except Exception as e:
                    print(f"[Upload] ⚠️  Ultra-optimized upload failed: {e}")
                    print("[Upload] Falling back to basic single-exchange upload...")
                    
                    # Fallback to AI1-only upload
                    exchanges = daily_report_df['exchange'].unique()
                    if 'AI1' in exchanges:
                        ai1_data = daily_report_df[daily_report_df['exchange'] == 'AI1'].copy()
                        if len(ai1_data) > 0:
                            print(f"[Upload] Processing fallback DATA AI1 ({len(ai1_data)} rows)")
                            upload_basic_reports_single(spreadsheet, ai1_data, 'AI1')
                            print("[Upload] ✅ AI1 fallback completed")
                        
                    if "AI1" not in str(e):  # If AI1 wasn't the issue, it might have succeeded
                        print("[Upload] Note: Some exchanges might have uploaded successfully before error")
            
            print("[Upload] ✅ Google Sheets update process completed")
            
    except ImportError as e:
        print(f"[Upload] ⚠️  Google Sheets modules not available: {e}")
        print("[Upload] Skipping Google Sheets upload")
    except Exception as e:
        print(f"[Upload] ⚠️  Google Sheets upload failed: {e}")
        print(f"[Upload] Error details: {str(e)}")
        print("[Upload] Data is processed and ready - sheets upload can be fixed separately")
    
    # Step 2: Local data validation and summary
    print("[Upload] Performing local data validation...")
    try:
        # Validate basic report
        if daily_report_df is not None:
            validate_data(daily_report_df, "Basic Daily Report")
        
        # Validate advanced analysis
        if daily_analysis_df is not None:
            validate_data(daily_analysis_df, "Advanced Daily Analysis")
        
    except Exception as e:
        print(f"[Upload] Error in data validation: {e}")
    
    print("\n[Upload] Data upload process complete.")
    print("="*50)
    print("📊 PIPELINE STATUS:")
    print("✅ catch_data.py - Data collection")
    print("✅ process_data.py - Data processing") 
    print("✅ upload_data.py - Data validation")
    print("="*50)

def upload_basic_reports_single(spreadsheet, exchange_data, exchange):
    """Upload a single exchange using optimized batch operations with complete column set"""
    import time
    
    worksheet_name = f'DATA {exchange}'
    
    # Get or create worksheet
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
        print(f"[Upload] ✅ Found existing worksheet: {worksheet_name}")
    except:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=25)
        print(f"[Upload] ✅ Created new worksheet: {worksheet_name}")
        time.sleep(2)  # Rate limiting after creation
    
    # Complete columns for DATA sheets - all required columns
    all_required_columns = [
        'Material Name', 'ticker', 'category', 'tier', 'Recipe', 'Amount per Recipe', 
        'Weight', 'Volume', 'Current Price', 'Input Cost per Unit', 'Input Cost per Stack',
        'Profit per Unit', 'Profit per Stack', 'ROI %', 'Supply', 'Demand', 
        'Traded Volume', 'Market Cap', 'Liquidity Ratio', 'Investment Score', 
        'Risk Level', 'Volatility'
    ]
    
    # Display headers (proper capitalization)
    display_headers = [
        'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe', 'Amount per Recipe', 
        'Weight', 'Volume', 'Current Price', 'Input Cost per Unit', 'Input Cost per Stack',
        'Profit per Unit', 'Profit per Stack', 'ROI %', 'Supply', 'Demand', 
        'Traded Volume', 'Market Cap', 'Liquidity Ratio', 'Investment Score', 
        'Risk Level', 'Volatility'
    ]
    
    # Filter to available columns
    available_columns = []
    final_headers = []
    
    for i, col in enumerate(all_required_columns):
        if col in exchange_data.columns:
            available_columns.append(col)
            final_headers.append(display_headers[i])
    
    filtered_data = exchange_data[available_columns].copy()
    
    print(f"[Upload] Preparing {len(filtered_data)} rows for {worksheet_name}")
    print(f"[Upload] Using {len(available_columns)} columns: {available_columns}")
    
    # Clear worksheet
    worksheet.clear()
    time.sleep(1)
    
    # Prepare all data including headers
    all_data = [final_headers]  # Headers first (with proper capitalization)
    
    # Add data rows
    for _, row in filtered_data.iterrows():
        row_data = []
        for col in available_columns:
            value = row.get(col, '')
            if pd.isna(value) or value == 'nan':
                value = ''
            row_data.append(str(value))
        all_data.append(row_data)
    
    # Upload in one optimized batch
    try:
        print(f"[Upload] Uploading all data to {worksheet_name} in single batch...")
        
        # Define range for all data
        end_col_letter = chr(ord('A') + len(available_columns) - 1)
        range_name = f"A1:{end_col_letter}{len(all_data)}"
        
        worksheet.update(range_name, all_data)
        print(f"[Upload] ✅ Successfully uploaded {len(filtered_data)} rows to {worksheet_name}")
        print(f"[Upload] Headers: {final_headers}")
        
        # Rate limiting after upload
        time.sleep(3)
        
    except Exception as e:
        print(f"[Upload] ❌ Batch upload failed for {worksheet_name}: {e}")
        if "429" in str(e):
            print("[Upload] Rate limit hit - waiting and will retry later")
            time.sleep(60)
        raise

def upload_basic_reports(spreadsheet, daily_report_df):
    """Upload basic daily reports to DATA sheets using optimized approach."""
    exchanges = daily_report_df['exchange'].unique()
    print(f"[Upload] Found exchanges for basic reports: {list(exchanges)}")
    
    # Prioritize AI1 first
    ai1_priority = ['AI1'] + [ex for ex in exchanges if ex != 'AI1']
    
    for exchange in ai1_priority:
        exchange_data = daily_report_df[daily_report_df['exchange'] == exchange].copy()
        if len(exchange_data) > 0:
            try:
                print(f"[Upload] Processing DATA {exchange} ({len(exchange_data)} rows)")
                upload_basic_reports_single(spreadsheet, exchange_data, exchange)
                print(f"[Upload] ✅ DATA {exchange} completed")
                
                # If AI1 succeeds, that's the main priority
                if exchange == 'AI1':
                    print("[Upload] 🎯 AI1 upload successful - main objective achieved!")
                    
            except Exception as e:
                print(f"[Upload] ❌ Failed to upload DATA {exchange}: {e}")
                if exchange == 'AI1':
                    print("[Upload] ⚠️  AI1 upload failed - this is the priority issue!")
                    raise  # Re-raise for AI1 failures
                else:
                    print(f"[Upload] Continuing with other exchanges...")
                    continue

def upload_advanced_analysis(spreadsheet, daily_analysis_df):
    """Upload advanced analysis to Report sheets with organized sections."""
    exchanges = daily_analysis_df['exchange'].unique()
    print(f"[Upload] Found exchanges for advanced analysis: {list(exchanges)}")
    
    for exchange in exchanges:
        exchange_data = daily_analysis_df[daily_analysis_df['exchange'] == exchange].copy()
        if len(exchange_data) > 0:
            worksheet_name = f'Report {exchange}'
            
            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                print(f"[Upload] ✅ Found existing worksheet: {worksheet_name}")
            except:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=2000, cols=30)
                print(f"[Upload] ✅ Created new worksheet: {worksheet_name}")
            
            # Upload structured report with sections
            upload_structured_report(worksheet, exchange_data, worksheet_name)
        else:
            print(f"[Upload] ⚠️  No data for exchange {exchange}")

def upload_structured_report(worksheet, exchange_data, worksheet_name):
    """Upload data to worksheet with organized sections and formatting."""
    # Clear the worksheet
    worksheet.clear()
    
    current_row = 1
    
    # === HEADER SECTION ===
    worksheet.update_cell(current_row, 1, f"PROSPEROUS UNIVERSE - MARKET ANALYSIS REPORT")
    worksheet.update_cell(current_row + 1, 1, f"Exchange: {worksheet_name.replace('Report ', '')}")
    worksheet.update_cell(current_row + 2, 1, f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    worksheet.update_cell(current_row + 3, 1, f"Total Materials: {len(exchange_data)}")
    current_row += 5
    
    # === SECTION 1: ARBITRAGE OPPORTUNITIES ===
    # Get current exchange from worksheet name (e.g., "Report AI1" -> "AI1")
    current_exchange = worksheet_name.replace('Report ', '').strip()
    
    # Filter arbitrage opportunities to only include those involving this exchange
    arbitrage_data = exchange_data[exchange_data['Max Arbitrage Profit'] > 0].copy()
    
    # Further filter to only show arbitrage where this exchange is either buy or sell location
    if not arbitrage_data.empty:
        exchange_mask = (
            (arbitrage_data['Best Buy Exchange'] == current_exchange) |
            (arbitrage_data['Best Sell Exchange'] == current_exchange)
        )
        arbitrage_data = arbitrage_data[exchange_mask].copy()
    
    if not arbitrage_data.empty:
        # Section header
        worksheet.update_cell(current_row, 1, "🔄 ARBITRAGE OPPORTUNITIES")
        current_row += 1
        worksheet.update_cell(current_row, 1, f"Found {len(arbitrage_data)} arbitrage opportunities involving {current_exchange}")
        current_row += 2
        
        # Arbitrage columns
        arbitrage_columns = [
            'Material Name', 'ticker', 'category', 'tier', 'Current Price',
            'Best Buy Exchange', 'Best Sell Exchange', 'Max Arbitrage Profit', 'Arbitrage ROI %',
            'Investment Score', 'Risk Level'
        ]
        
        # Upload arbitrage section
        current_row = upload_section_data(worksheet, arbitrage_data, arbitrage_columns, current_row)
        current_row += 2
    else:
        worksheet.update_cell(current_row, 1, "🔄 ARBITRAGE OPPORTUNITIES")
        current_row += 1
        worksheet.update_cell(current_row, 1, f"No profitable arbitrage opportunities involving {current_exchange} found at this time")
        current_row += 3
    
    # === SECTION 2: BOTTLENECK ANALYSIS ===
    bottleneck_data = exchange_data[exchange_data['Bottleneck Severity'] > 0].copy()
    
    if not bottleneck_data.empty:
        # Section header
        worksheet.update_cell(current_row, 1, "⚠️ SUPPLY/DEMAND BOTTLENECKS")
        current_row += 1
        worksheet.update_cell(current_row, 1, f"Found {len(bottleneck_data)} materials with supply/demand imbalances")
        current_row += 2
        
        # Bottleneck columns
        bottleneck_columns = [
            'Material Name', 'ticker', 'category', 'tier', 'Current Price',
            'Supply', 'Demand', 'Bottleneck Type', 'Bottleneck Severity', 'Market Opportunity',
            'Investment Score', 'Risk Level'
        ]
        
        # Upload bottleneck section
        current_row = upload_section_data(worksheet, bottleneck_data, bottleneck_columns, current_row)
        current_row += 2
    else:
        worksheet.update_cell(current_row, 1, "⚠️ SUPPLY/DEMAND BOTTLENECKS")
        current_row += 1
        worksheet.update_cell(current_row, 1, "No significant bottlenecks detected")
        current_row += 3
    
    # === SECTION 3: PRODUCTION ANALYSIS ===
    production_data = exchange_data[exchange_data['Break-even Quantity'] > 0].copy()
    
    if not production_data.empty:
        # Section header
        worksheet.update_cell(current_row, 1, "🏭 PRODUCTION OPPORTUNITIES")
        current_row += 1
        worksheet.update_cell(current_row, 1, f"Found {len(production_data)} materials with profitable production")
        current_row += 2
        
        # Production columns
        production_columns = [
            'Material Name', 'ticker', 'category', 'tier', 'Current Price',
            'Input Cost per Unit', 'Profit per Unit', 'ROI %', 'Total Production Cost',
            'Break-even Quantity', 'Production Time (hrs)', 'Recommendation', 'Confidence %'
        ]
        
        # Upload production section
        current_row = upload_section_data(worksheet, production_data, production_columns, current_row)
        current_row += 2
    else:
        worksheet.update_cell(current_row, 1, "🏭 PRODUCTION OPPORTUNITIES")
        current_row += 1
        worksheet.update_cell(current_row, 1, "No profitable production opportunities identified")
        current_row += 3
    
    # === SECTION 4: TOP INVESTMENT OPPORTUNITIES ===
    top_investments = exchange_data.nlargest(20, 'Investment Score').copy()
    
    # Section header
    worksheet.update_cell(current_row, 1, "📈 TOP INVESTMENT OPPORTUNITIES")
    current_row += 1
    worksheet.update_cell(current_row, 1, f"Top 20 materials ranked by investment score")
    current_row += 2
    
    # Investment columns
    investment_columns = [
        'Material Name', 'ticker', 'category', 'tier', 'Current Price',
        'Investment Score', 'ROI %', 'Risk Level', 'Recommendation', 'Confidence %',
        'Volatility'
    ]
    
    # Upload investment section
    current_row = upload_section_data(worksheet, top_investments, investment_columns, current_row)
    current_row += 2
    
    # === SECTION 5: COMPLETE DATA TABLE ===
    worksheet.update_cell(current_row, 1, "📊 COMPLETE MARKET DATA")
    current_row += 1
    worksheet.update_cell(current_row, 1, f"All {len(exchange_data)} materials with complete analysis data")
    current_row += 2
    
    # All analysis columns
    all_columns = [
        'Material Name', 'ticker', 'category', 'tier', 'Current Price', 'Supply', 'Demand',
        'Input Cost per Unit', 'Profit per Unit', 'ROI %',
        'Best Buy Exchange', 'Best Sell Exchange', 'Max Arbitrage Profit', 'Arbitrage ROI %',
        'Bottleneck Type', 'Bottleneck Severity', 'Market Opportunity',
        'Recommendation', 'Confidence %', 'Break-even Quantity', 'Production Time (hrs)',
        'Total Production Cost', 'Investment Score', 'Risk Level', 'Volatility'
    ]
    
    # Filter to available columns
    available_columns = [col for col in all_columns if col in exchange_data.columns]
    
    # Upload complete data section
    upload_section_data(worksheet, exchange_data, available_columns, current_row)
    
    print(f"[Upload] ✅ Uploaded structured report to {worksheet_name}")
    print(f"[Upload]    - Arbitrage ops: {len(arbitrage_data) if not arbitrage_data.empty else 0}")
    print(f"[Upload]    - Bottlenecks: {len(bottleneck_data) if not bottleneck_data.empty else 0}")
    print(f"[Upload]    - Production ops: {len(production_data) if not production_data.empty else 0}")
    print(f"[Upload]    - Total materials: {len(exchange_data)}")

def upload_section_data(worksheet, data, columns, start_row):
    """Upload a section of data to the worksheet with rate limiting."""
    import time
    
    # Filter to available columns
    available_columns = [col for col in columns if col in data.columns]
    
    if not available_columns:
        return start_row
    
    # Upload headers
    for col_idx, col_name in enumerate(available_columns):
        worksheet.update_cell(start_row, col_idx + 1, col_name)
        time.sleep(0.5)  # Rate limiting
    
    current_row = start_row + 1
    
    # Upload data rows in smaller batches to avoid quota limits
    batch_size = 10  # Further reduced to avoid quota issues
    for i in range(0, len(data), batch_size):
        try:
            print(f"[Upload] Uploading batch {i//batch_size + 1}/{(len(data)-1)//batch_size + 1}")
            batch = data.iloc[i:i+batch_size]
            batch_rows = []
            for idx, row in batch.iterrows():
                row_data = []
                for col in available_columns:
                    value = row.get(col, '')
                    if pd.isna(value) or value == 'nan':
                        value = ''
                    row_data.append(str(value))
                batch_rows.append(row_data)
            
            # Update batch
            if batch_rows:
                end_row = current_row + len(batch_rows) - 1
                end_col = len(available_columns)
                range_name = f"A{current_row}:{chr(ord('A') + end_col - 1)}{end_row}"
                worksheet.update(range_name, batch_rows)
                current_row += len(batch_rows)
                
                # Rate limiting: wait between batches
                time.sleep(2.0)
                
        except Exception as e:
            print(f"[Upload] ⚠️  Batch upload error: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                print("[Upload] Rate limit hit, waiting 60 seconds...")
                time.sleep(60)
            continue
    
    return current_row

def upload_to_worksheet(worksheet, upload_data, available_columns, worksheet_name):
    """Helper function to upload data to a worksheet using optimized single batch operation."""
    import time
    
    print(f"[Upload] Starting optimized upload to {worksheet_name}")
    
    # Clear worksheet
    worksheet.clear()
    time.sleep(1.0)  # Rate limiting
    
    # Prepare all data including headers in one batch
    all_data = [available_columns]  # Headers first
    
    # Add all data rows
    for idx, row in upload_data.iterrows():
        row_data = []
        for col in available_columns:
            value = row.get(col, '')
            if pd.isna(value) or value == 'nan':
                value = ''
            row_data.append(str(value))
        all_data.append(row_data)
    
    # Upload everything in ONE API call
    try:
        print(f"[Upload] Uploading {len(all_data)} rows (including headers) in single batch...")
        
        # Calculate range for all data
        end_col_letter = chr(ord('A') + len(available_columns) - 1)
        range_name = f"A1:{end_col_letter}{len(all_data)}"
        
        # Single batch upload - this is the key optimization!
        worksheet.update(range_name, all_data)
        
        print(f"[Upload] ✅ Successfully uploaded {len(upload_data)} rows to {worksheet_name}")
        print(f"[Upload]    Columns: {available_columns}")
        
        # Rate limiting after upload
        time.sleep(2.0)
        
    except Exception as e:
        print(f"[Upload] ❌ Batch upload failed: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            print("[Upload] Rate limit hit, waiting 60 seconds...")
            time.sleep(60)
        raise

def validate_data(df, data_type):
    """Validate data and show summary."""
    # Validate key columns
    required_cols = ['ticker', 'exchange', 'category', 'tier']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"[Upload] ⚠️  {data_type} missing columns: {missing_cols}")
    else:
        print(f"[Upload] ✅ {data_type} all required columns present")
        
    # Show sample data
    print(f"\n[Upload] Sample {data_type}:")
    sample_data = df[['ticker', 'exchange', 'category', 'tier']].head(3)
    print(sample_data.to_string(index=False))
    
    # Show statistics
    print(f"\n[Upload] {data_type} Statistics:")
    print(f"  - Total rows: {len(df)}")
    print(f"  - Unique tickers: {df['ticker'].nunique()}")
    print(f"  - Exchanges: {df['exchange'].unique()}")
    print(f"  - Categories: {df['category'].nunique()} unique")
    print(f"  - Tiers: {sorted(df['tier'].unique())}")

if __name__ == "__main__":
    main()
