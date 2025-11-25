import requests
import csv
from io import StringIO
import json
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def fetch_csv(url):
    response = requests.get(url)
    response.raise_for_status()
    return list(csv.DictReader(StringIO(response.text)))

def upload_csv_to_google_sheets(csv_path, fieldnames):
    """Upload the generated CSV to Google Sheets 'Price Analyser Data' sheet."""
    try:
        print("Starting Google Sheets upload...")
        # Get spreadsheet ID from environment
        spreadsheet_id = os.environ.get('PRUN_SPREADSHEET_ID')
        if not spreadsheet_id:
            print("Warning: PRUN_SPREADSHEET_ID not set, skipping Google Sheets upload")
            return
        
        print(f"Spreadsheet ID: {spreadsheet_id}")
        # Load service account credentials (assuming prun-profit-*.json is in the same dir)
        creds_path = os.path.join(os.path.dirname(__file__), 'prun-profit-42c5889f620d.json')
        print(f"Loading creds from: {creds_path}")
        creds = Credentials.from_service_account_file(creds_path, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        service = build('sheets', 'v4', credentials=creds)
        
        # Read CSV data
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = [list(row.values()) for row in reader]
        
        # Add header
        header = list(fieldnames)
        data.insert(0, header)
        
        print(f"Data to upload: {len(data)} rows")
        # Clear and update the sheet
        range_name = 'Price Analyser Data!A:Z'  # Adjust range as needed
        print(f"Clearing and updating range: {range_name}")
        body = {'values': data}
        service.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=range_name).execute()
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption='RAW', body=body
        ).execute()
        
        print(f"Successfully uploaded {len(data)} rows to Google Sheets 'Price Analyser Data'")
    except Exception as e:
        print(f"Error uploading to Google Sheets: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to generate chain dictionary."""
    try:
        # Fetch all required CSVs strictly from FIO API
        try:
            materials = fetch_csv("https://rest.fnar.net/csv/materials")
            buildings = fetch_csv("https://rest.fnar.net/csv/buildings")
            recipe_inputs = fetch_csv("https://rest.fnar.net/csv/recipeinputs")
            recipe_outputs = fetch_csv("https://rest.fnar.net/csv/recipeoutputs")
            buildingworkforces = fetch_csv("https://rest.fnar.net/csv/buildingworkforces")
            planet_resources = fetch_csv("https://rest.fnar.net/csv/planetresources")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch required data from FIO API: {e}")

        # Build extractable materials set strictly from planetresources
        try:
            extractable_materials = set(row['Ticker'].lower() for row in planet_resources)
        except Exception as e:
            raise RuntimeError(f"Failed to parse extractable materials from planetresources: {e}")
        if len(extractable_materials) == 0:
            raise RuntimeError("Extractable materials set is empty after parsing planetresources. Aborting pipeline.")
        print(f"Total extractable materials fetched from planetresources: {len(extractable_materials)}")

        print(buildingworkforces[0].keys())

        # Map recipe key to inputs and outputs
        inputs_by_recipe = {}
        for row in recipe_inputs:
            rid = row['Key']
            inputs_by_recipe.setdefault(rid, []).append(row['Material'].lower())

        # Map each material to all recipe keys that produce it (universal, multi-output safe)
        recipes_by_material = {}
        outputs_by_recipe = {}
        for row in recipe_outputs:
            rid = row['Key']
            mat = row['Material'].lower()
            outputs_by_recipe.setdefault(rid, []).append(mat)
            if mat not in recipes_by_material:
                recipes_by_material[mat] = set()
            recipes_by_material[mat].add(rid)

        # Ensure every output material is present in the cache, even if only produced as a byproduct
        # This will be handled in the main material loop below, so no hardcoding needed

        # ...existing code...

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
            producing_recipes = list(recipes_by_material.get(ticker, []))

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

        # --- Universal Material Export for Google Sheets ---
        # Prepare rows for every output material of every recipe
        output_rows = []
        for recipe_id, outputs in outputs_by_recipe.items():
            inputs = inputs_by_recipe.get(recipe_id, [])
            building = building_by_recipe.get(recipe_id, "")
            for output_material in outputs:
                chain_data = chains.get(output_material, {})
                output_rows.append({
                    "Ticker": output_material,
                    "Recipe": recipe_id,
                    "Building": building,
                    "Inputs": ",".join(inputs),
                    "Outputs": ",".join(outputs),
                    "Tier": chain_data.get("tier", ""),
                    "Workforce": chain_data.get("workforce_tier", ""),
                    # Add more columns as needed for your sheet
                })

        # Write to CSV for Google Sheet upload
        csv_path = os.path.join(cache_dir, "price_analyser_data.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
            writer.writeheader()
            writer.writerows(output_rows)

        print(f"price_analyser_data.csv generated with {len(output_rows)} rows in {cache_dir}")

        # Upload to Google Sheets
        upload_csv_to_google_sheets(csv_path, output_rows[0].keys())
        
    except Exception as e:
        print(f"Error generating chain dictionary: {e}")
        raise

if __name__ == "__main__":
    main()