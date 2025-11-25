#!/usr/bin/env python3
"""
Analyze byproduct recipes in PrUn Tracker data.
Finds recipes where all outputs are byproducts (materials with no recipes).
"""

import json
import csv
import os
from collections import defaultdict

def analyze_byproduct_recipes():
    # Load data
    cache_dir = os.path.join(os.path.dirname(__file__), 'pu-tracker', 'cache')

    # Load recipes
    recipes_file = os.path.join(cache_dir, 'recipes.json')
    with open(recipes_file, 'r') as f:
        recipes_data = json.load(f)

    # Load materials
    materials_file = os.path.join(cache_dir, 'materials.csv')
    materials = set()
    with open(materials_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            materials.add(row['Ticker'].upper())

    # Identify materials that have recipes (producers)
    materials_with_recipes = set()
    all_recipes = []

    for recipe_key, recipe_info in recipes_data.items():
        # Extract the output material from the recipe key
        # Format: "BUILDING:input1-input2=>output1-output2"
        if '=>' in recipe_key:
            output_part = recipe_key.split('=>')[1]
            # Parse outputs like "1xMAT" or just "MAT"
            outputs = []
            for item in output_part.split('-'):
                if 'x' in item:
                    # Format: "1xMAT"
                    parts = item.split('x')
                    if len(parts) == 2:
                        outputs.append(parts[1].upper())
                else:
                    # Just the ticker
                    outputs.append(item.upper())

            # Add all outputs as having recipes (they are produced)
            for output in outputs:
                materials_with_recipes.add(output)

            all_recipes.append({
                'key': recipe_key,
                'building': recipe_key.split(':')[0],
                'inputs': recipe_info['inputs'],
                'outputs': outputs,
                'full_recipe': recipe_key
            })

    # Identify byproducts (materials that appear but have no recipes)
    byproducts = set()
    for material in materials:
        if material not in materials_with_recipes:
            byproducts.add(material)

    print(f"=== BYPRODUCT RECIPE ANALYSIS ===")
    print(f"Total materials: {len(materials)}")
    print(f"Materials with recipes: {len(materials_with_recipes)}")
    print(f"Byproducts (no recipes): {len(byproducts)}")
    print()

    print("Byproducts:")
    for byproduct in sorted(byproducts):
        print(f"  {byproduct}")
    print()

    # Find recipes where ALL outputs are byproducts
    byproduct_recipes = []
    for recipe in all_recipes:
        if all(output in byproducts for output in recipe['outputs']):
            byproduct_recipes.append(recipe)

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