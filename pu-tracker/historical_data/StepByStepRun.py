import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent  # This is 'historical_data'
HIST = ROOT  # Scripts are in this folder
CACHE = ROOT.parent / "cache"

def run_step(script, desc):
    print(f"\n{'='*60}\n[STEP] {desc}\n{'='*60}")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True
    )
    print(f"\n[RESULT] {script}: Exit code {result.returncode}\n")
    if result.returncode != 0:
        print(f"[ERROR] {script} failed. Check above for details.\n")
    return result.returncode

if __name__ == "__main__":
    # 1. Data Collection
    run_step(HIST / "catch_data.py", "Fetch all raw data (tickers, materials, chains, buildings, tiers, etc.)")

    # 2. Data Processing
    run_step(HIST / "unified_processor.py", "Process and merge all data")

    # 3. Enhanced Analysis
    run_step(HIST / "data_analyzer.py", "Generate enhanced analysis for upload")

    # 4. Fetch Orders and Bids
    run_step(HIST / "fetch_orders_and_bids.py", "Fetch orders.csv and bids.csv for arbitrage calculations")

    # 5. Upload to Google Sheets
    run_step(HIST / "upload_enhanced_analysis.py", "Upload enhanced analysis to Google Sheets")

    # 6. Generate and Upload Report Tabs
    run_step(HIST / "generate_report_tabs.py", "Generate and upload report tabs to Google Sheets")

    print("\nAll steps completed. Check above for any errors or warnings.")