"""
Check if Report AI1 has been updated
"""
import gspread

def check_report_ai1():
    try:
        print("=== CHECKING REPORT AI1 CONTENT ===")
        
        # Connect to Google Sheets
        creds_path = r"c:\Users\Usuario\Documents\GitHub\PrUn-Tracker - copia\pu-tracker\historical_data\prun-profit-7e0c3bafd690.json"
        gc = gspread.service_account(filename=creds_path)
        spreadsheet = gc.open_by_key('1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI')
        
        print(f"✅ Connected to: {spreadsheet.title}")
        
        # Get Report AI1 worksheet
        worksheet = spreadsheet.worksheet('Report AI1')
        
        # Get first 20 rows to check content
        values = worksheet.get_values("A1:E20")
        
        print(f"✅ Report AI1 content (first 20 rows):")
        for i, row in enumerate(values[:20], 1):
            if row:  # Only print non-empty rows
                print(f"Row {i:2}: {row}")
        
        # Check if it has our structured format
        if len(values) > 0:
            if "PROSPEROUS UNIVERSE" in str(values[0]):
                print("✅ Found structured report header!")
            elif "🔄 ARBITRAGE" in str(values):
                print("✅ Found arbitrage section!")
            elif any("arbitrage" in str(row).lower() for row in values):
                print("✅ Found arbitrage content!")
            else:
                print("⚠️  Content doesn't match expected structure")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_report_ai1()
