import requests
import csv
from io import StringIO
import json
import os

def fetch_csv(url):
    response = requests.get(url)
    response.raise_for_status()
    return list(csv.DictReader(StringIO(response.text)))

def main():
    """Main function to generate chain dictionary."""
    try:
        # Fetch all required CSVs
        materials = fetch_csv("https://rest.fnar.net/csv/materials")
        buildings = fetch_csv("https://rest.fnar.net/csv/buildings")
        recipe_inputs = fetch_csv("https://rest.fnar.net/csv/recipeinputs")
        recipe_outputs = fetch_csv("https://rest.fnar.net/csv/recipeoutputs")
        buildingworkforces = fetch_csv("https://rest.fnar.net/csv/buildingworkforces")

        print(buildingworkforces[0].keys())

        # Map recipe key to inputs and outputs
        inputs_by_recipe = {}
        for row in recipe_inputs:
            rid = row['Key']
            inputs_by_recipe.setdefault(rid, []).append(row['Material'].lower())

        outputs_by_recipe = {}
        for row in recipe_outputs:
            rid = row['Key']
            outputs_by_recipe.setdefault(rid, []).append(row['Material'].lower())

        # Map recipe key to building
        building_by_recipe = {}
        for row in recipe_outputs:
            rid = row['Key']
            building = row.get('Building', '') or row.get('Key', '')
            building_by_recipe[rid] = building

        # Tier logic
        WORKFORCE_TIER = {
            "pioneer": 1,
            "settler": 2,
            "technician": 3,
            "engineer": 4,
            "scientist": 5,
        }

        workforce_by_building = {}
        for row in buildingworkforces:
            building = row['Building']
            workforce = row['Level'].strip().lower()
            tier = WORKFORCE_TIER.get(workforce, 0)
            prev_tier = workforce_by_building.get(building, 0)
            workforce_by_building[building] = max(prev_tier, tier)

        print(workforce_by_building)

        # Build chains dictionary
        chains = {}
        for row in materials:
            ticker = row['Ticker'].lower()
            producing_recipes = [rid for rid, outputs in outputs_by_recipe.items() if ticker in outputs]
            if producing_recipes:
                rid = producing_recipes[0]
                building = building_by_recipe.get(rid, "")
                building_code = building.split(":")[0] if ":" in building else building
                workforce_tier = workforce_by_building.get(building_code, 0)
                inputs = [i for i in inputs_by_recipe.get(rid, [])]
                if not inputs and workforce_tier == 1:
                    tier = 0
                else:
                    tier = workforce_tier

                print(f"Product: {ticker}, Building: {building}, Building Code: {building_code}, Workforce Tier: {workforce_tier}, Inputs: {inputs}, Assigned Tier: {tier}")

                chains[ticker] = {
                    "inputs": inputs,
                    "building": building.lower(),
                    "workforce_tier": workforce_tier,
                    "recipe_id": rid,
                    "tier": tier
                }
            else:
                print(f"Product: {ticker} has no recipe, assigned Tier: 0")
                chains[ticker] = {
                    "inputs": [],
                    "building": None,
                    "workforce_tier": None,
                    "recipe_id": None,
                    "tier": 0
                }

        # Save to cache
        cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Save chains.json
        chains_path = os.path.join(cache_dir, "chains.json")
        with open(chains_path, "w", encoding="utf-8") as f:
            json.dump(chains, f, indent=2)

        # Also save recipes.json (extracted from recipe data)
        recipes = {}
        for recipe_id, inputs in inputs_by_recipe.items():
            outputs = outputs_by_recipe.get(recipe_id, [])
            building = building_by_recipe.get(recipe_id, "")
            recipes[recipe_id] = {
                "inputs": inputs,
                "outputs": outputs,
                "building": building
            }
        
        recipes_path = os.path.join(cache_dir, "recipes.json")
        with open(recipes_path, "w", encoding="utf-8") as f:
            json.dump(recipes, f, indent=2)

        # Save tiers.json (tier mapping)
        tiers = {ticker: data["tier"] for ticker, data in chains.items()}
        tiers_path = os.path.join(cache_dir, "tiers.json")
        with open(tiers_path, "w", encoding="utf-8") as f:
            json.dump(tiers, f, indent=2)

        print(f"chains.json generated with {len(chains)} items in {cache_dir}")
        print(f"recipes.json generated with {len(recipes)} items in {cache_dir}")
        print(f"tiers.json generated with {len(tiers)} items in {cache_dir}")

    except Exception as e:
        print(f"Error generating chain dictionary: {e}")
        raise

if __name__ == "__main__":
    main()