"""
main.py
Main entry point for PrUn-Tracker pipeline.
All core functionality is now located in the historical_data folder.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

def run_catch_data():
    """Run data collection."""
    print("=== RUNNING DATA COLLECTION ===")
    from historical_data.catch_data import main as catch_main
    catch_main()

def run_process_data():
    """Run data processing."""
    print("=== RUNNING DATA PROCESSING ===")
    from historical_data.process_data import main as process_main
    process_main()

def run_upload_data():
    """Run data upload."""
    print("=== RUNNING DATA UPLOAD ===")
    from historical_data.upload_data import main as upload_main
    upload_main()

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
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python main.py [catch|process|upload|full]")
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
