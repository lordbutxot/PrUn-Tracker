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
        
        # Fetch planet resources to identify extractable materials (tier 0)
        try:
            planet_resources = fetch_csv("https://rest.fnar.net/csv/planetresources")
            extractable_materials = set(row['Material'].lower() for row in planet_resources)
            print(f"Found {len(extractable_materials)} extractable materials from planet resources")
        except Exception as e:
            print(f"Warning: Could not fetch planet resources: {e}")
            extractable_materials = set()
        
        # Manually add known extractable resources if API failed
        # These are common resources that can be extracted from planets
        known_extractables = {
            'h2o', 'h', 'o', 'n', 'he', 'ar', 'ne', 'kr', 'f', 'amm',
            'cuo', 'feo', 'alo', 'auo', 'lio', 'sio', 'tio', 'reo',
            'gal', 'hal', 'ber', 'bor', 'brm', 'cli', 'lst', 'mag',
            'mgs', 'scr', 'tai', 'tco', 'ts', 'zir', 'c', 's',
            'hex', 'les', 'bts'
        }
        
        if len(extractable_materials) == 0:
            print(f"Warning: Using fallback list of {len(known_extractables)} known extractable materials")
            extractable_materials = known_extractables
        else:
            # Merge API data with known extractables to ensure we have oxygen
            extractable_materials.update(known_extractables)
            print(f"Total extractable materials (API + known): {len(extractable_materials)}")

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
        byproduct_recipes = {}  # Track recipes with multiple outputs
        
        for row in materials:
            ticker = row['Ticker'].lower()
            producing_recipes = [rid for rid, outputs in outputs_by_recipe.items() if ticker in outputs]
            
            # Check if material is extractable from planets (tier 0)
            is_extractable = ticker in extractable_materials
            
            if producing_recipes:
                # Store ALL recipes for materials with multiple production methods
                all_recipe_data = []
                min_tier = 999
                primary_recipe = None
                primary_building = None
                primary_inputs = None
                
                for rid in producing_recipes:
                    building = building_by_recipe.get(rid, "")
                    building_code = building.split(":")[0] if ":" in building else building
                    workforce_tier = workforce_by_building.get(building_code, 0)
                    inputs = [i for i in inputs_by_recipe.get(rid, [])]
                    outputs = outputs_by_recipe.get(rid, [])
                    
                    # Determine tier for this recipe
                    if not inputs:
                        recipe_tier = 0  # No inputs = tier 0 (extractable/basic)
                    else:
                        recipe_tier = workforce_tier
                    
                    # Store recipe data
                    recipe_data = {
                        "recipe_id": rid,
                        "building": building,
                        "inputs": inputs,
                        "outputs": outputs,
                        "tier": recipe_tier,
                        "workforce_tier": workforce_tier,
                        "is_byproduct": len(outputs) > 1  # Multiple outputs = byproducts
                    }
                    all_recipe_data.append(recipe_data)
                    
                    # Track byproduct recipes separately
                    if len(outputs) > 1:
                        byproduct_recipes[rid] = {
                            "recipe_id": rid,
                            "building": building,
                            "inputs": inputs,
                            "outputs": outputs,
                            "output_materials": outputs  # All materials produced
                        }
                    
                    # Track the minimum tier (if any recipe is tier 0, material is tier 0)
                    if recipe_tier < min_tier:
                        min_tier = recipe_tier
                        primary_recipe = rid
                        primary_building = building
                        primary_inputs = inputs
                
                # If material is extractable from planets, it's always tier 0
                tier = 0 if is_extractable else min_tier
                
                extractable_flag = " [EXTRACTABLE]" if is_extractable else ""
                print(f"Product: {ticker}, Recipes: {len(producing_recipes)}, Primary Building: {primary_building}, Inputs: {primary_inputs}, Assigned Tier: {tier}{extractable_flag}")

                chains[ticker] = {
                    "inputs": primary_inputs,
                    "building": primary_building.lower() if primary_building else None,
                    "workforce_tier": workforce_by_building.get(primary_building.split(":")[0] if ":" in primary_building else primary_building, 0) if primary_building else 0,
                    "recipe_id": primary_recipe,
                    "tier": tier,
                    "min_tier": min_tier,  # Minimum tier among all recipes
                    "recipe_count": len(producing_recipes),  # Track how many recipes exist
                    "is_extractable": is_extractable,  # Flag for extractable materials
                    "all_recipes": all_recipe_data,  # Store all production methods
                    "has_byproduct_recipes": any(r["is_byproduct"] for r in all_recipe_data)
                }
            else:
                # No recipes found - check if extractable, otherwise tier 0 by default
                tier = 0
                extractable_flag = " [EXTRACTABLE]" if is_extractable else ""
                print(f"Product: {ticker} has no recipe, assigned Tier: {tier}{extractable_flag}")
                chains[ticker] = {
                    "inputs": [],
                    "building": None,
                    "workforce_tier": None,
                    "recipe_id": None,
                    "tier": tier,
                    "min_tier": tier,
                    "is_extractable": is_extractable,
                    "all_recipes": [],
                    "has_byproduct_recipes": False
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

        # Save byproduct_recipes.json for recipes with multiple outputs
        byproduct_path = os.path.join(cache_dir, "byproduct_recipes.json")
        with open(byproduct_path, "w", encoding="utf-8") as f:
            json.dump(byproduct_recipes, f, indent=2)

        # Save tier0_resources.json (extractable materials)
        tier0_resources = list(extractable_materials)
        tier0_path = os.path.join(cache_dir, "tier0_resources.json")
        with open(tier0_path, "w", encoding="utf-8") as f:
            json.dump(tier0_resources, f, indent=2)

        print(f"chains.json generated with {len(chains)} items in {cache_dir}")
        print(f"recipes.json generated with {len(recipes)} items in {cache_dir}")
        print(f"tiers.json generated with {len(tiers)} items in {cache_dir}")
        print(f"byproduct_recipes.json generated with {len(byproduct_recipes)} items in {cache_dir}")
        print(f"tier0_resources.json generated with {len(tier0_resources)} items in {cache_dir}")

    except Exception as e:
        print(f"Error generating chain dictionary: {e}")
        raise

if __name__ == "__main__":
    main()