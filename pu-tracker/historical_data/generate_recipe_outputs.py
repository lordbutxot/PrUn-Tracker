import csv
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"

def generate_recipe_outputs():
    buildingrecipes_path = CACHE_DIR / "buildingrecipes.csv"
    byproduct_recipes_path = CACHE_DIR / "byproduct_recipes.json"
    recipe_outputs_path = CACHE_DIR / "recipe_outputs.csv"
    
    outputs = []
    
    # Process buildingrecipes.csv
    if buildingrecipes_path.exists():
        with open(buildingrecipes_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row['Key']
                if '=>' in key:
                    output_part = key.split('=>')[1]
                    items = output_part.split('-')
                    for item in items:
                        if 'x' in item:
                            amount_str, ticker = item.split('x')
                            amount = int(amount_str)
                            outputs.append({'Key': key, 'Material': ticker.upper(), 'Amount': amount})
    
    # Process byproduct_recipes.json
    if byproduct_recipes_path.exists():
        with open(byproduct_recipes_path, 'r', encoding='utf-8') as f:
            byproduct_data = json.load(f)
            for recipe_key, recipe_info in byproduct_data.items():
                for output_ticker in recipe_info.get('output_materials', []):
                    # For byproducts, we need to determine amount. Check if it's in the recipe key
                    amount = 1  # Default amount
                    if '=>' in recipe_key:
                        output_part = recipe_key.split('=>')[1]
                        items = output_part.split('-')
                        for item in items:
                            if 'x' in item and output_ticker.upper() in item.upper():
                                amount_str = item.split('x')[0]
                                amount = int(amount_str)
                                break
                    outputs.append({'Key': recipe_key, 'Material': output_ticker.upper(), 'Amount': amount})
    
    # Remove duplicates (same recipe + material combination)
    seen = set()
    unique_outputs = []
    for output in outputs:
        key = (output['Key'], output['Material'])
        if key not in seen:
            seen.add(key)
            unique_outputs.append(output)
    
    # Write outputs
    with open(recipe_outputs_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Key', 'Material', 'Amount'])
        writer.writeheader()
        writer.writerows(unique_outputs)
    
    print(f"Generated {len(unique_outputs)} recipe outputs (including byproducts)")