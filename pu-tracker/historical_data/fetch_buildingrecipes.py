import requests
import csv
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
    
    outputs = []
    inputs = []
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
                            inputs.append({'Key': key, 'Material': ticker, 'Amount': amount})
                # Generate outputs
                items = output_part.split('-')
                for item in items:
                    if 'x' in item:
                        amount_str, ticker = item.split('x')
                        amount = int(amount_str)
                        outputs.append({'Key': key, 'Material': ticker, 'Amount': amount})
    
    # Write inputs
    with open(recipe_inputs_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Key', 'Material', 'Amount'])
        writer.writeheader()
        writer.writerows(inputs)
    print(f"Generated {len(inputs)} recipe inputs to {recipe_inputs_path}")
    
    # Write outputs
    with open(recipe_outputs_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Key', 'Material', 'Amount'])
        writer.writeheader()
        writer.writerows(outputs)
    print(f"Generated {len(outputs)} recipe outputs to {recipe_outputs_path}")

if __name__ == "__main__":
    fetch_buildingrecipes()