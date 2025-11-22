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
    url = "https://rest.fnar.net/csv/planetdetail"  # Changed from /planets to /planetdetail
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
        print(f"[INFO] Found {len(header)} columns in planetdetail endpoint")
        
        # Find required column indices
        try:
            # Look for PlanetName or PlanetNaturalId column (NOT PlanetId which is a GUID)
            planet_idx = next((i for i, col in enumerate(header) 
                              if col.strip().lower() in ['planetname', 'planetnaturalid']), None)
            if planet_idx is None:
                # Default to PlanetName (column index 2 based on API structure)
                planet_idx = 2
                print(f"[INFO] Planet name column not found in header, defaulting to index 2")
                
            fertility_idx = next((i for i, col in enumerate(header) 
                                if 'fertility' in col.strip().lower()), None)
            
            if fertility_idx is None:
                print("[ERROR] Fertility column not found in planetdetail endpoint")
                print(f"[INFO] Available columns: {[col.strip() for col in header[:10]]}")
                # Create empty file with default values
                with open(outfile, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Planet', 'Fertility'])
                print("[WARN] Created empty fertility file - farming calculations will use default (1.0)")
                return False
                
            print(f"[INFO] Using planet column index {planet_idx}, fertility column index {fertility_idx}")
        except StopIteration:
            print("[ERROR] Required columns not found in planetdetail endpoint")
            print(f"[INFO] Available columns: {[col.strip() for col in header[:10]]}")
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
                            # Include ALL planets with fertility data (negative values are multipliers)
                            # Only exclude -1 which means "no farming possible"
                            if fertility > -1:
                                writer.writerow([planet, fertility])
                                planet_count += 1
                        except ValueError:
                            # Skip invalid fertility values
                            continue
        
        if planet_count == 0:
            print("[WARN] No planets with valid fertility found (all planets may have fertility = -1)")
            print("[INFO] Creating empty file - farming calculations will use default values")
            return False
        
        print(f"[SUCCESS] Saved planet_fertility.csv with {planet_count} planets to {outfile}")
        print(f"[INFO] Note: Only planets with fertility >= 0 are included (planets with -1 cannot farm)")
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
