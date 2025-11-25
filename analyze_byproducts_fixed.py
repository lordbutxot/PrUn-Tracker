#!/usr/bin/env python3
"""
Analyze byproduct recipes in PrUn Tracker data.
Finds recipes where all outputs are byproducts (materials that don't have dedicated production recipes).
"""

import json
import csv
from collections import defaultdict

def analyze_byproduct_recipes():
    # Load data
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(script_dir, 'pu-tracker', 'cache')

    # Load recipes
    with open(os.path.join(cache_dir, 'recipes.json'), 'r') as f:
        recipes_data = json.load(f)

    # Load materials
    materials = set()
    with open(os.path.join(cache_dir, 'materials.csv'), 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            materials.add(row['Ticker'].upper())

    # Find materials that are primary outputs of recipes
    primary_outputs = set()
    for recipe_key, recipe_info in recipes_data.items():
        if '=>' in recipe_key:
            output_part = recipe_key.split('=>')[1]
            # Get the first (primary) output
            primary_output = output_part.split('-')[0]
            if 'x' in primary_output:
                # Format: "1xMAT"
                parts = primary_output.split('x')
                if len(parts) == 2:
                    primary_outputs.add(parts[1].upper())
            else:
                # Just the ticker
                primary_outputs.add(primary_output.upper())

    # Byproducts are materials that appear as outputs but are never primary outputs
    all_outputs = set()
    for recipe_key, recipe_info in recipes_data.items():
        for output in recipe_info['outputs']:
            all_outputs.add(output.upper())

    byproducts = all_outputs - primary_outputs

    print("=== BYPRODUCT ANALYSIS ===")
    print(f"Total materials: {len(materials)}")
    print(f"Materials that are primary outputs: {len(primary_outputs)}")
    print(f"All materials that appear as outputs: {len(all_outputs)}")
    print(f"Byproducts (appear as outputs but never primary): {len(byproducts)}")
    print()

    print("Byproducts:")
    for byproduct in sorted(byproducts):
        print(f"  {byproduct}")
    print()

    # Find recipes where ALL outputs are byproducts
    byproduct_recipes = []
    for recipe_key, recipe_info in recipes_data.items():
        outputs = [out.upper() for out in recipe_info['outputs']]
        if all(output in byproducts for output in outputs):
            byproduct_recipes.append({
                'key': recipe_key,
                'building': recipe_key.split(':')[0],
                'inputs': recipe_info['inputs'],
                'outputs': outputs,
                'full_recipe': recipe_key
            })

    print(f"Recipes producing ONLY byproducts: {len(byproduct_recipes)}")
    print()

    # Group by building type
    building_counts = defaultdict(int)
    for recipe in byproduct_recipes:
        building_counts[recipe['building']] += 1

    print("By building type:")
    for building, count in sorted(building_counts.items()):
        print(f"  {building}: {count} recipes")
    print()

    # Look for specific example: CHP => NA + CL
    chp_na_cl_recipes = []
    for recipe in byproduct_recipes:
        if (recipe['building'] == 'CHP' and
            'NA' in recipe['outputs'] and
            'CL' in recipe['outputs']):
            chp_na_cl_recipes.append(recipe)

    print("=== SPECIFIC EXAMPLE: CHP => NA + CL ===")
    if chp_na_cl_recipes:
        print(f"Found {len(chp_na_cl_recipes)} CHP recipes producing NA and CL as byproducts:")
        for recipe in chp_na_cl_recipes:
            print(f"  {recipe['full_recipe']}")
    else:
        print("No CHP recipes found that produce NA and CL as byproducts")
    print()

    # Show some examples
    print("=== SAMPLE BYPRODUCT RECIPES ===")
    for i, recipe in enumerate(byproduct_recipes[:10]):
        print(f"{i+1}. {recipe['full_recipe']}")
        print(f"   Building: {recipe['building']}")
        print(f"   Outputs (byproducts): {', '.join(recipe['outputs'])}")
    print()

    if len(byproduct_recipes) > 10:
        print(f"... and {len(byproduct_recipes) - 10} more")

    return len(byproduct_recipes), len(chp_na_cl_recipes)

if __name__ == "__main__":
    total_byproduct_recipes, chp_na_cl_count = analyze_byproduct_recipes()
    print(f"\nSUMMARY:")
    print(f"Total recipes producing only byproducts: {total_byproduct_recipes}")
    print(f"CHP recipes producing NA + CL as byproducts: {chp_na_cl_count}")