"""
PrUn-Tracker Unified Pipeline
"""
import sys
from pathlib import Path
import subprocess

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

CACHE_DIR = current_dir.parent / "cache"

def is_market_data_ready():
    market_file = CACHE_DIR / "market_data.csv"
    prices_file = CACHE_DIR / "prices_all.csv"
    for f in [market_file, prices_file]:
        if f.exists() and f.stat().st_size > 0:
            return True
    return False

def run_script(script_name, description=None):
    if description:
        print(f"\n\033[1;36m[STEP]\033[0m {description}")
    print(f"\033[1;33m[RUNNING]\033[0m {script_name}")
    # Use unbuffered output (-u) and stream output live
    process = subprocess.Popen(
        [sys.executable, "-u", script_name],
        cwd=current_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8"  # <-- Add this line
    )
    if process.stdout is not None:
        for line in process.stdout:
            print(line, end='')  # Print each line as it arrives
    process.wait()
    if process.returncode != 0:
        print(f"\033[1;31m[ERROR]\033[0m {script_name} failed.")
        return False
    print(f"\033[1;32m[SUCCESS]\033[0m {script_name} completed.")
    return True

def main(mode='full'):
    print("\n\033[1;35m========================================\033[0m")
    print("\033[1;35m   PrUn-Tracker Unified Pipeline\033[0m")
    print("\033[1;35m========================================\033[0m")
    print(f"Starting at {Path(__file__).parent} | Mode: {mode}\n")

    # 1. Ensure market data is present
    if not is_market_data_ready():
        print("\033[1;36m[STEP]\033[0m Market data missing. Fetching market data...")
        fetchers = ["fetch_all_tickers.py", "catch_data.py"]
        for fetcher in fetchers:
            fetcher_path = current_dir / fetcher
            if fetcher_path.exists():
                if not run_script(fetcher, f"Fetching data with {fetcher}"):
                    print(f"\033[1;31m[ERROR]\033[0m {fetcher} failed. Cannot proceed.")
                    return 1
                if is_market_data_ready():
                    break
        if not is_market_data_ready():
            print("\033[1;31m[FATAL]\033[0m Market data still missing after fetch attempts. Exiting.")
            return 1
    else:
        print("\033[1;32m[INFO]\033[0m Market data found.")

    # 2. Process data
    if not run_script("unified_processor.py", "Processing and merging all data"):
        print("\033[1;31m[FATAL]\033[0m Data processing failed. Exiting.")
        return 1

    # 3. Run enhanced analysis
    if not run_script("data_analyzer.py", "Generating enhanced analysis for upload"):
        print("\033[1;31m[FATAL]\033[0m Enhanced analysis failed. Exiting.")
        return 1

    # 4. Upload to Google Sheets
    if not run_script("upload_enhanced_analysis.py", "Uploading to Google Sheets"):
        print("\033[1;31m[FATAL]\033[0m Upload failed. Exiting.")
        return 1

    # 5. Generate and upload Report Tabs
    if not run_script("generate_report_tabs.py", "Generating and uploading Report Tabs"):
        print("\033[1;31m[FATAL]\033[0m Report tab generation failed. Exiting.")
        return 1

    print("\n\033[1;32m[SUCCESS]\033[0m Pipeline completed and data uploaded to Google Sheets.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
