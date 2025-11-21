"""
Generate workforces.csv from buildings.json

This script reads the buildings.json file and creates a workforces.csv file with:
- Key: Building-Workforce combo (e.g., "EXT-PIONEER")
- Building: Building ticker (e.g., "EXT")
- Level: Workforce type (e.g., "PIONEER")
- Capacity: Number of workers (e.g., 60)

This file is required by unified_processor.py for workforce cost calculations.
"""

import json
import csv
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"
BUILDINGS_JSON = CACHE_DIR / "buildings.json"
WORKFORCES_CSV = CACHE_DIR / "workforces.csv"

# Workforce types in order of tier
WORKFORCE_TYPES = ['pioneers', 'settlers', 'technicians', 'engineers', 'scientists']
WORKFORCE_NAMES = ['PIONEER', 'SETTLER', 'TECHNICIAN', 'ENGINEER', 'SCIENTIST']

def generate_workforces():
    """Generate workforces.csv from buildings.json"""
    
    if not BUILDINGS_JSON.exists():
        print(f"[ERROR] buildings.json not found at {BUILDINGS_JSON}")
        return False
    
    print(f"[INFO] Reading buildings data from {BUILDINGS_JSON}")
    
    with open(BUILDINGS_JSON, 'r', encoding='utf-8') as f:
        buildings = json.load(f)
    
    workforce_rows = []
    
    # Process each building
    for building_ticker, building_data in buildings.items():
        # Check each workforce type
        for wf_key, wf_name in zip(WORKFORCE_TYPES, WORKFORCE_NAMES):
            capacity = building_data.get(wf_key, 0)
            
            if capacity > 0:
                workforce_rows.append({
                    'Key': f"{building_ticker}-{wf_name}",
                    'Building': building_ticker,
                    'Level': wf_name,
                    'Capacity': capacity
                })
    
    # Sort by building then by workforce level
    workforce_rows.sort(key=lambda x: (x['Building'], x['Level']))
    
    # Write to CSV
    print(f"[INFO] Writing {len(workforce_rows)} workforce entries to {WORKFORCES_CSV}")
    
    with open(WORKFORCES_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Key', 'Building', 'Level', 'Capacity'])
        writer.writeheader()
        writer.writerows(workforce_rows)
    
    print(f"[SUCCESS] Generated workforces.csv with {len(workforce_rows)} entries")
    
    # Show sample data
    print("\nSample workforce data:")
    for row in workforce_rows[:10]:
        print(f"  {row['Building']:4} {row['Level']:10} = {row['Capacity']:3} workers")
    
    return True

def main():
    """Main entry point"""
    try:
        return generate_workforces()
    except Exception as e:
        print(f"[ERROR] Failed to generate workforces.csv: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
