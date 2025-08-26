"""
Direct upload test for Google Sheets
"""
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def test_direct_upload():
    print("=== DIRECT GOOGLE SHEETS UPLOAD TEST ===")
    
    # Load daily analysis
    analysis_path = r"c:\Users\Usuario\Documents\GitHub\PrUn-Tracker - copia\pu-tracker\cache\daily_analysis.csv"
    if not os.path.exists(analysis_path):
        print(f"❌ File not found: {analysis_path}")
        return
    
    df = pd.read_csv(analysis_path)
    print(f"✅ Loaded daily analysis: {df.shape}")
    
    # Check if exchange column exists
    if 'exchange' not in df.columns:
        print("❌ No 'exchange' column found")
        print(f"Available columns: {list(df.columns)}")
        return
    
    print(f"✅ Found exchanges: {df['exchange'].unique()}")
    
    # Try Google Sheets connection
    try:
        # Use the credentials file
        creds_path = r"c:\Users\Usuario\Documents\GitHub\PrUn-Tracker - copia\pu-tracker\historical_data\prun-profit-7e0c3bafd690.json"
        
        if not os.path.exists(creds_path):
            print(f"❌ Credentials not found: {creds_path}")
            return
        
        print(f"✅ Found credentials: {creds_path}")
        
        # Authenticate
        gc = gspread.service_account(filename=creds_path)
        print("✅ Authenticated with Google Sheets")
        
        # Open spreadsheet
        spreadsheet_id = '1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI'
        spreadsheet = gc.open_by_key(spreadsheet_id)
        print(f"✅ Opened spreadsheet: {spreadsheet.title}")
        
        # Get AI1 data
        ai1_data = df[df['exchange'] == 'AI1'].copy()
        print(f"✅ AI1 data: {len(ai1_data)} materials")
        
        if len(ai1_data) == 0:
            print("❌ No AI1 data found")
            return
        
        # Try to get or create Report AI1 worksheet
        worksheet_name = 'Report AI1'
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            print(f"✅ Found existing {worksheet_name}")
        except:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=2000, cols=30)
            print(f"✅ Created new {worksheet_name}")
        
        # Clear worksheet
        worksheet.clear()
        print("✅ Cleared worksheet")
        
        # Add header
        worksheet.update_cell(1, 1, "PROSPEROUS UNIVERSE - MARKET ANALYSIS REPORT")
        worksheet.update_cell(2, 1, f"Exchange: AI1")
        worksheet.update_cell(3, 1, f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        worksheet.update_cell(4, 1, f"Total Materials: {len(ai1_data)}")
        print("✅ Added headers")
        
        # Add arbitrage section
        current_row = 6
        arbitrage_data = ai1_data[ai1_data['Max Arbitrage Profit'] > 0].copy()
        
        worksheet.update_cell(current_row, 1, "🔄 ARBITRAGE OPPORTUNITIES")
        current_row += 1
        worksheet.update_cell(current_row, 1, f"Found {len(arbitrage_data)} profitable arbitrage opportunities")
        current_row += 2
        
        if len(arbitrage_data) > 0:
            # Add arbitrage headers
            arb_columns = ['Material Name', 'ticker', 'Current Price', 'Best Buy Exchange', 'Best Sell Exchange', 'Max Arbitrage Profit']
            for col_idx, col_name in enumerate(arb_columns):
                if col_name in arbitrage_data.columns:
                    worksheet.update_cell(current_row, col_idx + 1, col_name)
            
            current_row += 1
            
            # Add first 10 arbitrage rows
            for i in range(min(10, len(arbitrage_data))):
                row_data = arbitrage_data.iloc[i]
                for col_idx, col_name in enumerate(arb_columns):
                    if col_name in arbitrage_data.columns:
                        value = row_data[col_name]
                        if pd.isna(value):
                            value = ''
                        worksheet.update_cell(current_row + i, col_idx + 1, str(value))
            
            print(f"✅ Added {min(10, len(arbitrage_data))} arbitrage opportunities")
        
        print("✅ Upload test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_upload()
