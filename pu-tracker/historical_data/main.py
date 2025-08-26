"""
main.py
Main entry point for PrUn-Tracker pipeline located in historical_data folder.
This allows for proper relative imports within the package.
"""

import sys
import os

def run_catch_data():
    """Run data collection."""
    print("=== RUNNING DATA COLLECTION ===")
    from . import catch_data
    catch_data.main()

def run_process_data():
    """Run data processing."""
    print("=== RUNNING DATA PROCESSING ===")
    from . import process_data
    process_data.main()

def run_upload_data():
    """Run data upload."""
    print("=== RUNNING DATA UPLOAD ===")
    from . import upload_data
    upload_data.main()

def run_full_pipeline():
    """Run the complete pipeline."""
    print("="*60)
    print("🚀 STARTING PRUN-TRACKER FULL PIPELINE")
    print("="*60)
    
    try:
        # Step 1: Catch Data
        print("\n🔄 STEP 1: DATA COLLECTION")
        run_catch_data()
        print("✅ Data collection completed")
        
        # Step 2: Process Data
        print("\n🔄 STEP 2: DATA PROCESSING")
        run_process_data()
        print("✅ Data processing completed")
        
        # Step 3: Upload Data
        print("\n🔄 STEP 3: DATA UPLOAD")
        run_upload_data()
        print("✅ Data upload completed")
        
        print("\n" + "="*60)
        print("🎉 FULL PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {e}")
        print("="*60)
        raise

def main():
    """Main entry point with command line options."""
    if len(sys.argv) < 2:
        print("Usage: python -m historical_data.main [catch|process|upload|full]")
        print("  catch   - Run data collection only")
        print("  process - Run data processing only") 
        print("  upload  - Run data upload only")
        print("  full    - Run complete pipeline")
        return
    
    command = sys.argv[1].lower()
    
    if command == "catch":
        run_catch_data()
    elif command == "process":
        run_process_data()
    elif command == "upload":
        run_upload_data()
    elif command == "full":
        run_full_pipeline()
    else:
        print(f"Unknown command: {command}")
        print("Valid commands: catch, process, upload, full")

if __name__ == "__main__":
    main()
