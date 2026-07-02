"""
Workforce Costs Module (Legacy Wrapper)
This module now wraps functions from loaders.py and calculators.py
Maintained for backward compatibility with unified_processor.py
"""

import pandas as pd
from loaders import (
    load_recipe_inputs,
    load_byproduct_recipes,
    load_chains,
    load_market_data as load_market_prices,
    load_workforceneeds as load_workforce_needs,
    get_market_price
)
from calculators import (
    calculate_workforce_consumable_cost,
    allocate_byproduct_costs
)

# --- Helper Functions ---

def get_cheapest_acquisition_cost(ticker, market_prices, wf_consumables, chains=None, exchange="AI1"):
    """
    Determine the cheapest way to acquire a material.
    Legacy function maintained for compatibility.
    """
    if chains is None:
        chains = load_chains()
    
    ticker_lower = ticker.lower()
    chain_info = chains.get(ticker_lower, {})
    
    # Option 1: Market price
    market_price = get_market_price(ticker, market_prices, exchange)
    
    # Option 2: Extractable (tier 0)
    if chain_info.get("is_extractable", False):
        extraction_cost = 0.1  # Nominal extraction cost
        return min(market_price, extraction_cost) if market_price > 0 else extraction_cost
    
    return market_price if market_price > 0 else 0.0


# --- Main Input Cost Calculation ---
def calculate_input_costs_for_recipe(recipe_row, market_prices, wf_consumables, exchange="AI1", stack_size=100, enable_byproduct_allocation=True):
    """
    recipe_row: a row from your recipes DataFrame, must have:
        - 'Recipe'
        - 'WorkforceType'
        - 'HoursPerRecipe'
        - 'UnitsPerRecipe'
        - 'InputMaterials': dict of {ticker: qty}
        - 'OutputMaterials': dict of {ticker: qty} (optional, for byproduct handling)
    """
    # 1. Direct input cost
    direct_input_cost = 0.0
    for ticker, qty in recipe_row['InputMaterials'].items():
        price = get_market_price(ticker, market_prices, exchange)
        direct_input_cost += qty * price

    # 2. Workforce consumable cost
    wf_type = recipe_row['WorkforceType']
    hours = recipe_row['HoursPerRecipe']
    workforce_amount = recipe_row.get('WorkforceAmount', 100)  # Default to 100 if not specified
    wf_cost = calculate_workforce_consumable_cost(wf_type, hours, workforce_amount, market_prices, wf_consumables, exchange)

    # 3. Total input cost for the recipe
    total_input_cost = direct_input_cost + wf_cost

    # 4. Handle byproduct cost allocation if enabled
    recipe_id = recipe_row.get('Recipe', '')
    allocated_costs = {}
    if enable_byproduct_allocation and recipe_id:
        allocated_costs = allocate_byproduct_costs(recipe_id, total_input_cost, market_prices, exchange)

    # 5. Per unit and per stack
    units_per_recipe = recipe_row['UnitsPerRecipe']
    
    # If this recipe has byproducts, the cost per unit should be the allocated cost
    # Otherwise, use the total input cost
    if allocated_costs and 'OutputMaterials' in recipe_row:
        # Get the primary output ticker
        output_materials = recipe_row.get('OutputMaterials', {})
        if output_materials and len(output_materials) > 0:
            primary_ticker = list(output_materials.keys())[0]
            allocated_cost = allocated_costs.get(primary_ticker, total_input_cost)
            input_cost_per_unit = allocated_cost / units_per_recipe if units_per_recipe else 0
        else:
            input_cost_per_unit = total_input_cost / units_per_recipe if units_per_recipe else 0
    else:
        input_cost_per_unit = total_input_cost / units_per_recipe if units_per_recipe else 0
    
    input_cost_per_stack = input_cost_per_unit * stack_size

    # 6. Per hour
    input_cost_per_hour = total_input_cost / hours if hours else 0

    return {
        "Input Cost per Recipe": total_input_cost,
        "Input Cost per Unit": input_cost_per_unit,
        "Input Cost per Stack": input_cost_per_stack,
        "Input Cost per Hour": input_cost_per_hour,
        "Direct Input Cost": direct_input_cost,
        "Workforce Consumable Cost": wf_cost,
        "Allocated Costs": allocated_costs if allocated_costs else None,
        "Has Byproducts": bool(allocated_costs)
    }

# --- Example Usage ---
def example():
    recipes = load_recipe_inputs()
    market_prices = load_market_prices()
    wf_consumables = load_workforce_needs()

    # You may need to join/merge to get 'WorkforceType', 'HoursPerRecipe', 'UnitsPerRecipe', and input materials per recipe
    # For demonstration, let's assume recipes DataFrame has these columns:
    # - 'Recipe', 'WorkforceType', 'HoursPerRecipe', 'UnitsPerRecipe', 'InputMaterials' (dict)
    for idx, row in recipes.iterrows():
        # You may need to build InputMaterials dict from your columns
        # Here, we assume you have a dict already
        if 'InputMaterials' not in row or not isinstance(row['InputMaterials'], dict):
            continue  # Skip or build the dict as needed
        costs = calculate_input_costs_for_recipe(row, market_prices, wf_consumables, exchange="AI1", stack_size=100)
        print(f"Recipe {row['Recipe']}: {costs}")

if __name__ == "__main__":
    example()