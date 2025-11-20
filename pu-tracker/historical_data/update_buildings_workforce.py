import requests
import json
from pathlib import Path
import time

cache_dir = Path(__file__).parent.parent / "cache"

# Load current buildings.json
with open(cache_dir / "buildings.json", "r") as f:
    buildings = json.load(f)

print(f"Updating {len(buildings)} buildings with workforce data from FIO API...")

updated = 0
errors = 0

for ticker in buildings.keys():
    try:
        url = f'https://rest.fnar.net/building/{ticker}'
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Update workforce numbers
            buildings[ticker]['pioneers'] = data.get('Pioneers', 0)
            buildings[ticker]['settlers'] = data.get('Settlers', 0)
            buildings[ticker]['technicians'] = data.get('Technicians', 0)
            buildings[ticker]['engineers'] = data.get('Engineers', 0)
            buildings[ticker]['scientists'] = data.get('Scientists', 0)
            
            updated += 1
            if updated % 20 == 0:
                print(f"  Updated {updated} buildings...")
        else:
            print(f"  Failed to fetch {ticker}: HTTP {response.status_code}")
            errors += 1
            
        time.sleep(0.15)  # Rate limiting
        
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}")
        errors += 1

# Save updated buildings.json
with open(cache_dir / "buildings.json", "w") as f:
    json.dump(buildings, f, indent=2)

print(f"\n✅ Updated {updated} buildings with workforce data")
print(f"❌ {errors} errors")

# Show sample of updated data
print("\nSample updated buildings:")
for ticker in ['BMP', 'AAF', 'SME', 'FRM', 'REF', 'LAB', 'CLR']:
    if ticker in buildings:
        b = buildings[ticker]
        total = b['pioneers'] + b['settlers'] + b['technicians'] + b['engineers'] + b['scientists']
        print(f"{ticker}: P={b['pioneers']} S={b['settlers']} T={b['technicians']} E={b['engineers']} Sc={b['scientists']} (Total: {total})")
