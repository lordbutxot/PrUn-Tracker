"""
PrUn-Tracker Unified Pipeline
"""
import sys
from pathlib import Path
import subprocess
import time
import os

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

def run_script(script_name, description=None, log_file=None):
    if description:
        print(f"\n\033[1;36m[STEP]\033[0m {description}")
    print(f"\033[1;33m[RUNNING]\033[0m {script_name}")
    start = time.time()
    process = subprocess.Popen(
        [sys.executable, "-u", script_name],
        cwd=current_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8"
    )
    if process.stdout is not None:
        for line in process.stdout:
            print(line, end='')
            if log_file:
                with open(log_file, "a", encoding="utf-8") as lf:
                    lf.write(line)
    process.wait()
    elapsed = time.time() - start
    msg = f"\033[1;32m[SUCCESS]\033[0m {script_name} completed in {elapsed:.2f} seconds." if process.returncode == 0 else f"\033[1;31m[ERROR]\033[0m {script_name} failed in {elapsed:.2f} seconds."
    print(msg)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(msg + "\n")
    return process.returncode == 0, elapsed

def main(mode='full'):
    log_file = os.environ.get("PRUN_PIPELINE_LOGFILE", None)
    print("\n\033[1;35m========================================\033[0m")
    print("\033[1;35m   PrUn-Tracker Unified Pipeline\033[0m")
    print("\033[1;35m========================================\033[0m")
    print(f"Starting at {Path(__file__).parent} | Mode: {mode}\n")

    step_times = []

    # 1. Ensure market data is present
    if not is_market_data_ready():
        print("\033[1;36m[STEP]\033[0m Market data missing. Fetching market data...")
        fetchers = ["fetch_all_tickers.py", "catch_data.py"]
        for fetcher in fetchers:
            fetcher_path = current_dir / fetcher
            if fetcher_path.exists():
                ok, elapsed = run_script(fetcher, f"Fetching data with {fetcher}", log_file)
                step_times.append((f"Fetch ({fetcher})", elapsed))
                if not ok:
                    print(f"\033[1;31m[ERROR]\033[0m {fetcher} failed. Cannot proceed.")
                    return 1
                if is_market_data_ready():
                    break
        if not is_market_data_ready():
            print("\033[1;31m[FATAL]\033[0m Market data still missing after fetch attempts. Exiting.")
            return 1
    else:
        print("\033[1;32m[INFO]\033[0m Market data found.")

    # --- ADD THIS STEP ---
    ok, elapsed = run_script("add_tier_to_materials.py", "Assigning tiers to materials", log_file)
    step_times.append(("Assign Tiers", elapsed))
    if not ok:
        print("\033[1;31m[FATAL]\033[0m Tier assignment failed. Exiting.")
        return 1

    # 2. Process data
    ok, elapsed = run_script("unified_processor.py", "Processing and merging all data", log_file)
    step_times.append(("Process", elapsed))
    if not ok:
        print("\033[1;31m[FATAL]\033[0m Data processing failed. Exiting.")
        return 1

    # 3. Run enhanced analysis
    ok, elapsed = run_script("data_analyzer.py", "Generating enhanced analysis for upload", log_file)
    step_times.append(("Analyze", elapsed))
    if not ok:
        print("\033[1;31m[FATAL]\033[0m Enhanced analysis failed. Exiting.")
        return 1

    # 4. Fetch only orders.csv and bids.csv for arbitrage calculations
    ok, elapsed = run_script("fetch_orders_and_bids.py", "Fetching orders.csv and bids.csv for arbitrage calculations", log_file)
    step_times.append(("Fetch Orders/Bids", elapsed))
    if not ok:
        print("\033[1;31m[ERROR]\033[0m Failed to fetch orders/bids. Arbitrage opportunity sizes may be inaccurate.")

    # 5. Upload to Google Sheets
    ok, elapsed = run_script("upload_enhanced_analysis.py", "Uploading to Google Sheets", log_file)
    step_times.append(("Upload", elapsed))
    if not ok:
        print("\033[1;31m[FATAL]\033[0m Upload failed. Exiting.")
        return 1

    # 6. Generate and upload Report Tabs
    skip_arbitrage = os.environ.get("PRUN_SKIP_ARBITRAGE", "0") == "1"
    if not skip_arbitrage:
        ok, elapsed = run_script("generate_report_tabs.py", "Generating and uploading Report Tabs", log_file)
        step_times.append(("Report Tabs", elapsed))
        if not ok:
            print("\033[1;31m[FATAL]\033[0m Report tab generation failed. Exiting.")
            return 1

    print("\n\033[1;32m[SUCCESS]\033[0m Pipeline completed and data uploaded to Google Sheets.")
    print("\nStep timings:")
    total = 0
    for name, t in step_times:
        print(f"  {name:20s}: {t:.2f} seconds")
        total += t
    print(f"  {'Total':20s}: {total:.2f} seconds")
    if log_file:
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write("\nStep timings:\n")
            for name, t in step_times:
                lf.write(f"  {name:20s}: {t:.2f} seconds\n")
            lf.write(f"  {'Total':20s}: {total:.2f} seconds\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
