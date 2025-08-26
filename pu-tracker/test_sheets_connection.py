"""
Test the Google Sheets upload functionality
"""
import pandas as pd
import os
import sys

# Add the directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_upload():
    print("=== TESTING GOOGLE SHEETS UPLOAD ===")
    
    # Check if daily analysis exists
    analysis_path = "cache/daily_analysis.csv"
    if not os.path.exists(analysis_path):
        print(f"❌ No daily analysis found at {analysis_path}")
        return False
    
    # Load data
    df = pd.read_csv(analysis_path)
    print(f"✅ Loaded daily analysis: {len(df)} rows")
    
    # Check exchanges
    if 'exchange' in df.columns:
        exchanges = df['exchange'].unique()
        print(f"✅ Found exchanges: {list(exchanges)}")
        
        # Check AI1 data specifically
        ai1_data = df[df['exchange'] == 'AI1'].copy()
        print(f"✅ AI1 data: {len(ai1_data)} materials")
        
        # Check key columns
        key_columns = ['Max Arbitrage Profit', 'Bottleneck Severity', 'Investment Score']
        for col in key_columns:
            if col in ai1_data.columns:
                count = len(ai1_data[ai1_data[col] > 0])
                print(f"   - {col}: {count} items > 0")
        
    else:
        print("❌ No 'exchange' column found")
        return False
    
    # Try to authenticate with Google Sheets
    try:
        import gspread
        from historical_data.config import CONFIG
        
        print("✅ Imports successful")
        
        # Check credentials
        creds_path = CONFIG['GOOGLE_SERVICE_ACCOUNT_FILE']
        if os.path.exists(creds_path):
            print(f"✅ Credentials found at: {creds_path}")
        else:
            print(f"❌ Credentials not found at: {creds_path}")
            return False
        
        # Try authentication
        gc = gspread.service_account(filename=creds_path)
        print("✅ Google Sheets authentication successful")
        
        # Try opening spreadsheet
        spreadsheet_id = CONFIG['TARGET_SPREADSHEET_ID']
        spreadsheet = gc.open_by_key(spreadsheet_id)
        print(f"✅ Opened spreadsheet: {spreadsheet.title}")
        
        # Check if Report AI1 worksheet exists
        try:
            worksheet = spreadsheet.worksheet('Report AI1')
            print("✅ Found 'Report AI1' worksheet")
            
            # Check current content
            values = worksheet.get_all_values()
            print(f"   Current content: {len(values)} rows")
            
        except:
            print("⚠️  'Report AI1' worksheet not found - will be created")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Sheets error: {e}")
        return False

if __name__ == "__main__":
    test_upload()
