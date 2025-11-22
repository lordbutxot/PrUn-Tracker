"""
Fetch planet fertility data from FIO API.
Downloads planet-level fertility factors that affect farming building production times.
"""

import requests
import csv
from pathlib import Path

def fetch_planet_fertility():
    """
    Fetch planet fertility data from FIO API.
    Fertility affects farming building (FRM, ORC, VIN) production times.
    Returns True if successful, False otherwise.
    """
    url = "https://rest.fnar.net/csv/planets"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    outfile = cache_dir / "planet_fertility.csv"
    
    try:
        print("[Fetch] Downloading planet fertility data from FIO API...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse CSV response
        lines = response.text.strip().split('\n')
        if len(lines) < 2:
            print("[WARN] No planet data received from API")
            return False
        
        header = lines[0].split(',')
        print(f"[INFO] Columns available: {', '.join(header)}")
        
        # Find required column indices
        try:
            planet_idx = next((i for i, col in enumerate(header) 
                              if col.lower() in ['planetnaturalid', 'planetid', 'naturalid', 'name']), 0)
            fertility_idx = next(i for i, col in enumerate(header) 
                                if 'fertility' in col.lower())
        except StopIteration:
            print("[ERROR] Fertility column not found in planets endpoint")
            print(f"[INFO] Available columns: {header}")
            # Create empty file with default values
            with open(outfile, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Planet', 'Fertility'])
            print("[WARN] Created empty fertility file - farming calculations will use default (1.0)")
            return False
        
        # Write filtered data
        planet_count = 0
        with open(outfile, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Planet', 'Fertility'])
            
            for line in lines[1:]:
                if line.strip():
                    fields = line.split(',')
                    if len(fields) > max(planet_idx, fertility_idx):
                        planet = fields[planet_idx].strip()
                        fertility_str = fields[fertility_idx].strip()
                        
                        try:
                            fertility = float(fertility_str)
                            writer.writerow([planet, fertility])
                            planet_count += 1
                        except ValueError:
                            print(f"[WARN] Invalid fertility value for planet {planet}: {fertility_str}")
                            continue
        
        print(f"[SUCCESS] Saved planet_fertility.csv with {planet_count} planets to {outfile}")
        return True
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout while fetching fertility data from {url}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch fertility data: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error while processing fertility data: {e}")
        return False

if __name__ == "__main__":
    success = fetch_planet_fertility()
    exit(0 if success else 1)
