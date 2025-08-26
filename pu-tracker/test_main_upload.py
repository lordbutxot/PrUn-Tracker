"""
Test the actual upload_data.py main function
"""
import os
import sys

def test_main_upload():
    print("=== TESTING UPLOAD_DATA.PY MAIN FUNCTION ===")
    
    # Change to the correct directory
    os.chdir(r"c:\Users\Usuario\Documents\GitHub\PrUn-Tracker - copia\pu-tracker")
    sys.path.insert(0, os.getcwd())
    
    # Check required files
    required_files = [
        "cache/daily_analysis.csv",
        "cache/processed_data.csv",
        "historical_data/prun-profit-7e0c3bafd690.json"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ Found: {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
            return
    
    try:
        # Import and run the main function
        from historical_data.upload_data import main
        print("✅ Imported upload_data successfully")
        
        print("\n=== RUNNING UPLOAD_DATA MAIN ===")
        main()
        
    except Exception as e:
        print(f"❌ Error running main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_main_upload()
