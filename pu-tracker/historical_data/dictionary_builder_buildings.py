import requests
import csv
import json
from io import StringIO
import os

def main():
    """Main function to build buildings dictionary."""
    try:
        # Fetch buildings data
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
                    'pioneers': int(row.get('Pioneers', 0) or 0),
                    'settlers': int(row.get('Settlers', 0) or 0),
                    'technicians': int(row.get('Technicians', 0) or 0),
                    'engineers': int(row.get('Engineers', 0) or 0),
                    'scientists': int(row.get('Scientists', 0) or 0)
                }
                categories_dict[ticker.lower()] = category.lower()
        
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