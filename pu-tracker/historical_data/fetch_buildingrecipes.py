import requests
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
OUTFILE = CACHE_DIR / "buildingrecipes.csv"

def fetch_buildingrecipes():
    url = "https://rest.fnar.net/csv/buildingrecipes"
    print(f"Downloading {url} ...")
    resp = requests.get(url)
    resp.raise_for_status()
    OUTFILE.write_bytes(resp.content)
    print(f"Saved to {OUTFILE}")

if __name__ == "__main__":
    fetch_buildingrecipes()