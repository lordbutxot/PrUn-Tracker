import requests
import csv
import json
from io import StringIO
import os

def main():
    """Main function to build buildings dictionary."""
    try:
        # Fetch buildings data from CSV (basic info)
        buildings_url = "https://rest.fnar.net/csv/buildings"
        response = requests.get(buildings_url)
        response.raise_for_status()
        
        csvfile = StringIO(response.text)
        reader = csv.DictReader(csvfile)
        
        buildings_dict = {}
        categories_dict = {}
        
        for row in reader:
            ticker = row.get('Ticker', '').upper()
            name = row.get('Name', ticker)
            category = row.get('Category', 'Unknown')
            
            if ticker:
                buildings_dict[ticker] = {
                    'name': name,
                    'category': category,
                    'expertise': row.get('Expertise', ''),
                    'pioneers': 0,
                    'settlers': 0,
                    'technicians': 0,
                    'engineers': 0,
                    'scientists': 0
                }
                categories_dict[ticker.lower()] = category.lower()
        
        # Fetch workforce data from buildingworkforces CSV
        print("[INFO] Fetching workforce data from buildingworkforces API...")
        workforce_url = "https://rest.fnar.net/csv/buildingworkforces"
        response = requests.get(workforce_url)
        response.raise_for_status()
        
        csvfile = StringIO(response.text)
        workforce_reader = csv.DictReader(csvfile)
        
        # Update buildings with workforce data
        workforce_count = 0
        for row in workforce_reader:
            building = row.get('Building', '').upper()
            level = row.get('Level', '').lower()
            capacity = int(row.get('Capacity', 0))
            
            if building in buildings_dict and capacity > 0:
                # Map Level to workforce key (e.g., "PIONEER" -> "pioneers")
                workforce_key = level + 's'  # PIONEER -> pioneers, SETTLER -> settlers
                if workforce_key in buildings_dict[building]:
                    buildings_dict[building][workforce_key] = capacity
                    workforce_count += 1
        
        print(f"[INFO] Updated {workforce_count} workforce capacities for {len(buildings_dict)} buildings")
        
        # Save buildings dictionary
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
        os.makedirs(cache_dir, exist_ok=True)
        
        buildings_path = os.path.join(cache_dir, "buildings.json")
        with open(buildings_path, "w", encoding="utf-8") as f:
            json.dump(buildings_dict, f, indent=2)
        
        categories_path = os.path.join(cache_dir, "categories.json")
        with open(categories_path, "w", encoding="utf-8") as f:
            json.dump(categories_dict, f, indent=2)
        
        print(f"Generated buildings.json with {len(buildings_dict)} buildings in {cache_dir}")
        print(f"Generated categories.json with {len(categories_dict)} categories in {cache_dir}")
        
    except Exception as e:
        print(f"Error building buildings dictionary: {e}")
        raise

if __name__ == "__main__":
    main()