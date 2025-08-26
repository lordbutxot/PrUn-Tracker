"""
Minimal Google Sheets test
"""
try:
    import gspread
    print("✅ gspread imported")
    
    # Try authentication
    creds_path = r"c:\Users\Usuario\Documents\GitHub\PrUn-Tracker - copia\pu-tracker\historical_data\prun-profit-7e0c3bafd690.json"
    gc = gspread.service_account(filename=creds_path)
    print("✅ Authentication successful")
    
    # Try opening spreadsheet
    spreadsheet_id = '1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI'
    spreadsheet = gc.open_by_key(spreadsheet_id)
    print(f"✅ Opened spreadsheet: {spreadsheet.title}")
    
    # List worksheets
    worksheets = spreadsheet.worksheets()
    print(f"✅ Found {len(worksheets)} worksheets:")
    for ws in worksheets:
        print(f"   - {ws.title}")
    
    # Check if Report AI1 exists
    try:
        report_ai1 = spreadsheet.worksheet('Report AI1')
        values = report_ai1.get_all_values()
        print(f"✅ Report AI1 exists with {len(values)} rows")
        if len(values) > 0:
            print(f"   First row: {values[0][:5] if len(values[0]) > 5 else values[0]}")
    except:
        print("❌ Report AI1 worksheet not found")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
