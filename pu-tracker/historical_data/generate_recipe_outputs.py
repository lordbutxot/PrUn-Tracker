import csv
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"

def generate_recipe_outputs():
    buildingrecipes_path = CACHE_DIR / "buildingrecipes.csv"
    recipe_outputs_path = CACHE_DIR / "recipe_outputs.csv"
    
    outputs = []
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
                        outputs.append({'Key': key, 'Material': ticker, 'Amount': amount})
    
    with open(recipe_outputs_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Key', 'Material', 'Amount'])
        writer.writeheader()
        writer.writerows(outputs)
    
    print(f"Generated {len(outputs)} recipe outputs")

if __name__ == "__main__":
    generate_recipe_outputs()