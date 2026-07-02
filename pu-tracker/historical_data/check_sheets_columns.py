"""
Quick script to check what columns are actually in Google Sheets DATA tabs
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sheets_manager import UnifiedSheetsManager as SheetsManager
except ImportError:
    from sheets_manager import SheetsManager

SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
EXCHANGE_TABS = ['DATA AI1', 'DATA CI1', 'DATA CI2', 'DATA IC1', 'DATA NC1', 'DATA NC2']

def check_columns():
    """Check what columns exist in Google Sheets DATA tabs"""
    print("=" * 80)
    print("CHECKING GOOGLE SHEETS DATA TABS COLUMNS")
    print("=" * 80)
    
    try:
        # Initialize sheets manager
        sheets_manager = SheetsManager()
        
        # Check first tab only (all tabs should have same columns)
        tab_name = EXCHANGE_TABS[0]
        print(f"\nChecking: {tab_name}")
        print("-" * 80)
        
        # Get the spreadsheet
        spreadsheet = sheets_manager.client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(tab_name)
        
        # Get first row (headers)
        headers = worksheet.row_values(1)
        
        print(f"\nTotal columns found: {len(headers)}")
        print("\nColumn listing:")
        print("-" * 80)
        
        for i, header in enumerate(headers, 1):
            marker = ""
            if header in ['Supply', 'Demand', 'Traded Volume']:
                marker = " ⭐ TARGET COLUMN"
            print(f"{i:2d}. {header}{marker}")
        
        # Check if target columns exist
        print("\n" + "=" * 80)
        print("VERIFICATION:")
        print("-" * 80)
        
        target_columns = ['Supply', 'Demand', 'Traded Volume']
        for col in target_columns:
            if col in headers:
                position = headers.index(col) + 1
                print(f"✅ '{col}' found at position {position}")
            else:
                print(f"❌ '{col}' NOT FOUND")
        
        # Get sample data from these columns
        print("\n" + "=" * 80)
        print("SAMPLE DATA (First 5 rows):")
        print("-" * 80)
        
        if all(col in headers for col in target_columns):
            supply_col = headers.index('Supply') + 1
            demand_col = headers.index('Demand') + 1
            traded_col = headers.index('Traded Volume') + 1
            
            # Get data (rows 2-6)
            all_data = worksheet.get_all_values()
            
            print(f"\n{'Ticker':<10} {'Supply':<12} {'Demand':<12} {'Traded Volume':<15}")
            print("-" * 50)
            
            for i, row in enumerate(all_data[1:6], 2):  # Skip header, show 5 rows
                ticker = row[1] if len(row) > 1 else 'N/A'  # Column B (Ticker)
                supply = row[supply_col - 1] if len(row) >= supply_col else 'N/A'
                demand = row[demand_col - 1] if len(row) >= demand_col else 'N/A'
                traded = row[traded_col - 1] if len(row) >= traded_col else 'N/A'
                
                print(f"{ticker:<10} {supply:<12} {demand:<12} {traded:<15}")
        
        # Check all tabs
        print("\n" + "=" * 80)
        print("CHECKING ALL DATA TABS:")
        print("-" * 80)
        
        for tab in EXCHANGE_TABS:
            try:
                worksheet = spreadsheet.worksheet(tab)
                headers = worksheet.row_values(1)
                has_supply = 'Supply' in headers
                has_demand = 'Demand' in headers
                has_traded = 'Traded Volume' in headers
                
                status = "✅ ALL" if (has_supply and has_demand and has_traded) else "❌ MISSING"
                print(f"{tab:<15} {status:<10} (Supply:{has_supply}, Demand:{has_demand}, Traded:{has_traded})")
            except Exception as e:
                print(f"{tab:<15} ❌ ERROR: {e}")
        
        print("\n" + "=" * 80)
        print("CHECK COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = check_columns()
    sys.exit(0 if success else 1)
