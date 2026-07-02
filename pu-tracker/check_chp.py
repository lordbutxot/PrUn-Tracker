import sys
sys.path.append('.')
sys.path.append('./historical_data')
from historical_data.loaders import load_buildingrecipes, load_workforceneeds, load_market_data
from historical_data.calculators import calculate_workforce_cost_for_recipe

# Load data
recipes_df = load_buildingrecipes()
workforce_needs = load_workforceneeds()
market_prices = load_market_data()

print(f"Market prices loaded: {len(market_prices)} rows")
print(f"Workforce needs loaded: {len(workforce_needs)} types")

# Find CHP recipe
chp_recipe = recipes_df[recipes_df.index.str.contains('CHP:1xH2O-3xHAL')]
if not chp_recipe.empty:
    recipe_key = chp_recipe.index[0]
    recipe = chp_recipe.iloc[0]

    print(f'CHP Recipe: {recipe_key}')
    print(f'Duration: {recipe.get("Duration", "N/A")} seconds')
    print(f'Time: {recipe.get("Time", "N/A")} minutes')
    print(f'WorkforceRequirements: {recipe.get("WorkforceRequirements", {})}')

    # Calculate workforce cost
    workforce_cost = calculate_workforce_cost_for_recipe(recipe_key, recipes_df, workforce_needs, market_prices)
    print(f'Workforce Cost: {workforce_cost:.2f} ICA')

    # Show breakdown
    if recipe.get('WorkforceRequirements'):
        print('Workforce breakdown:')
        for wf_type, amount in recipe['WorkforceRequirements'].items():
            print(f'  {wf_type}: {amount}')
else:
    print('CHP recipe not found')