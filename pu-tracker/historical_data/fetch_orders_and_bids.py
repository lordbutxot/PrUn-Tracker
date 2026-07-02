import sys
from pathlib import Path
import requests

def fetch_orders_csv():
    url = "https://rest.fnar.net/csv/orders"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    orders_file = cache_dir / "orders.csv"
    try:
        print("[Catch] Downloading orders.csv...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(orders_file, "wb") as f:
            f.write(response.content)
        print(f"[SUCCESS] Saved orders.csv ({orders_file})")
    except Exception as e:
        print(f"[ERROR] Failed to download orders.csv: {e}")

def fetch_bids_csv():
    url = "https://rest.fnar.net/csv/bids"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    bids_file = cache_dir / "bids.csv"
    try:
        print("[Catch] Downloading bids.csv...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(bids_file, "wb") as f:
            f.write(response.content)
        print(f"[SUCCESS] Saved bids.csv ({bids_file})")
    except Exception as e:
        print(f"[ERROR] Failed to download bids.csv: {e}")

def main():
    fetch_orders_csv()
    fetch_bids_csv()

if __name__ == "__main__":
    main()