import requests
import csv
import json
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
    
    # Generate recipe_outputs.csv from buildingrecipes.csv
    generate_recipe_outputs()

def generate_recipe_outputs():
    recipe_outputs_path = CACHE_DIR / "recipe_outputs.csv"
    recipe_inputs_path = CACHE_DIR / "recipe_inputs.csv"
    byproduct_recipes_path = CACHE_DIR / "byproduct_recipes.json"
    
    outputs = []
    inputs = []
    
    # Process buildingrecipes.csv
    with open(OUTFILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row['Key']
            if '=>' in key:
                parts = key.split('=>')
                input_part = parts[0]
                output_part = parts[1]
                
                # Generate inputs
                if ':' in input_part:
                    input_part = input_part.split(':')[1]
                    items = input_part.split('-')
                    for item in items:
                        if 'x' in item:
                            amount_str, ticker = item.split('x')
                            amount = int(amount_str)
                            inputs.append({'Key': key, 'Material': ticker.upper(), 'Amount': amount})
                
                # Generate outputs
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
                # Add inputs for byproducts
                for input_ticker in recipe_info.get('inputs', []):
                    amount = 1  # Default, could be improved
                    if '=>' in recipe_key:
                        input_part = recipe_key.split('=>')[0]
                        if ':' in input_part:
                            input_part = input_part.split(':')[1]
                            items = input_part.split('-')
                            for item in items:
                                if 'x' in item and input_ticker.upper() in item.upper():
                                    amount_str = item.split('x')[0]
                                    amount = int(amount_str)
                                    break
                    inputs.append({'Key': recipe_key, 'Material': input_ticker.upper(), 'Amount': amount})
                
                # Add outputs for byproducts
                for output_ticker in recipe_info.get('output_materials', []):
                    amount = 1  # Default
                    if '=>' in recipe_key:
                        output_part = recipe_key.split('=>')[1]
                        items = output_part.split('-')
                        for item in items:
                            if 'x' in item and output_ticker.upper() in item.upper():
                                amount_str = item.split('x')[0]
                                amount = int(amount_str)
                                break
                    outputs.append({'Key': recipe_key, 'Material': output_ticker.upper(), 'Amount': amount})
    
    # Remove duplicates
    seen_inputs = set()
    unique_inputs = []
    for inp in inputs:
        key = (inp['Key'], inp['Material'])
        if key not in seen_inputs:
            seen_inputs.add(key)
            unique_inputs.append(inp)
    
    seen_outputs = set()
    unique_outputs = []
    for out in outputs:
        key = (out['Key'], out['Material'])
        if key not in seen_outputs:
            seen_outputs.add(key)
            unique_outputs.append(out)
    
    # Write inputs
    with open(recipe_inputs_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Key', 'Material', 'Amount'])
        writer.writeheader()
        writer.writerows(unique_inputs)
    print(f"Generated {len(unique_inputs)} recipe inputs to {recipe_inputs_path}")
    
    # Write outputs
    with open(recipe_outputs_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Key', 'Material', 'Amount'])
        writer.writeheader()
        writer.writerows(unique_outputs)
    print(f"Generated {len(unique_outputs)} recipe outputs to {recipe_outputs_path}")

if __name__ == "__main__":
    fetch_buildingrecipes()