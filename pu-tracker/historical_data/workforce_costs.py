import pandas as pd
import json
import os
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"

# --- Load Data ---
def load_recipe_inputs():
    return pd.read_csv(CACHE_DIR / "recipe_inputs.csv")

def load_byproduct_recipes():
    """Load recipes with multiple outputs (byproducts)"""
    byproduct_path = CACHE_DIR / "byproduct_recipes.json"
    if byproduct_path.exists():
        with open(byproduct_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_chains():
    """Load chains.json for material production information"""
    chains_path = CACHE_DIR / "chains.json"
    if chains_path.exists():
        with open(chains_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_market_prices():
    # Always use the standardised long format
    path = CACHE_DIR / "market_data_long.csv"
    if path.exists():
        return pd.read_csv(path)
    # fallback: transform and save
    path_wide = CACHE_DIR / "market_data.csv"
    df = pd.read_csv(path_wide)
    if 'Exchange' not in df.columns and 'AI1-AskPrice' in df.columns:
        exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
        records = []
        for _, row in df.iterrows():
            ticker = row['Ticker']
            for exch in exchanges:
                ask_col = f"{exch}-AskPrice"
                bid_col = f"{exch}-BidPrice"
                ask_price = row.get(ask_col, None)
                bid_price = row.get(bid_col, None)
                if pd.notnull(ask_price) or pd.notnull(bid_price):
                    records.append({
                        'Ticker': ticker,
                        'Exchange': exch,
                        'Ask_Price': pd.to_numeric(ask_price, errors='coerce') if pd.notnull(ask_price) else 0,
                        'Bid_Price': pd.to_numeric(bid_price, errors='coerce') if pd.notnull(bid_price) else 0,
                    })
        df_long = pd.DataFrame(records)
        df_long.to_csv(path, index=False)  # <-- FIXED: use 'path' not 'path_long'
        return df_long
    return df

def load_workforce_needs():
    with open(CACHE_DIR / "workforceneeds.json", "r", encoding="utf-8") as f:
        wf_needs_raw = json.load(f)
    wf_consumables = {}
    for entry in wf_needs_raw:
        wf_type = entry["WorkforceType"]
        needs = entry["Needs"]
        # JSON stores consumption per 100 workers per day
        # Convert to per single worker per hour: amount / 100 / 24
        wf_consumables[wf_type] = {need["MaterialTicker"]: need["Amount"] / 100.0 / 24.0 for need in needs}
    return wf_consumables

# --- Price Lookup ---
def get_market_price(ticker, market_prices, exchange="AI1"):
    row = market_prices[(market_prices['Ticker'] == ticker) & (market_prices['Exchange'] == exchange)]
    if not row.empty:
        # Use the correct column name with underscore
        return float(row.iloc[0]['Ask_Price'])  # or 'Bid_Price' as appropriate
    return 0.0

# --- Workforce Consumable Cost ---
def calculate_workforce_consumable_cost(wf_type, hours, workforce_amount, market_prices, wf_consumables, exchange="AI1"):
    """
    Calculate workforce consumable cost.
    
    Args:
        wf_type: Workforce type (PIONEER, SETTLER, etc.)
        hours: Recipe duration in hours
        workforce_amount: Number of workers (e.g., 100 for BMP)
        market_prices: DataFrame with market prices
        wf_consumables: Dict with per-worker per-hour consumption rates
        exchange: Exchange code (AI1, CI1, etc.)
    
    Returns:
        Total cost of workforce consumables for the recipe
    """
    total = 0.0
    consumables = wf_consumables.get(wf_type, {})
    for ticker, amt_per_hour_per_worker in consumables.items():
        qty = amt_per_hour_per_worker * workforce_amount * hours
        price = get_market_price(ticker, market_prices, exchange)
        total += qty * price
    return total

# --- Byproduct Cost Allocation ---
def allocate_byproduct_costs(recipe_id, total_input_cost, market_prices, exchange="AI1"):
    """
    Allocate costs for recipes with multiple outputs based on market value.
    Returns a dict of {ticker: allocated_cost_per_unit}
    """
    byproduct_recipes = load_byproduct_recipes()
    
    if recipe_id not in byproduct_recipes:
        return {}
    
    recipe_info = byproduct_recipes[recipe_id]
    outputs = recipe_info.get("outputs", [])
    
    if len(outputs) <= 1:
        return {}
    
    # Calculate total market value of all outputs
    output_values = {}
    total_value = 0.0
    
    for ticker in outputs:
        price = get_market_price(ticker, market_prices, exchange)
        output_values[ticker] = price
        total_value += price
    
    # Allocate costs proportionally based on market value
    allocated_costs = {}
    if total_value > 0:
        for ticker, value in output_values.items():
            proportion = value / total_value
            allocated_costs[ticker] = total_input_cost * proportion
    else:
        # If no market value available, split evenly
        equal_share = total_input_cost / len(outputs)
        for ticker in outputs:
            allocated_costs[ticker] = equal_share
    
    return allocated_costs

def get_cheapest_acquisition_cost(ticker, market_prices, wf_consumables, chains=None, exchange="AI1"):
    """
    Determine the cheapest way to acquire a material:
    - Direct extraction (if extractable)
    - Crafting from recipe
    - Buying from market
    Returns the minimum cost per unit.
    """
    if chains is None:
        chains = load_chains()
    
    ticker_lower = ticker.lower()
    chain_info = chains.get(ticker_lower, {})
    
    # Option 1: Market price
    market_price = get_market_price(ticker, market_prices, exchange)
    
    # Option 2: Extractable (tier 0)
    if chain_info.get("is_extractable", False):
        # Extractable materials have minimal cost (just workforce)
        # For now, assume extraction cost is negligible or use a base extraction cost
        extraction_cost = 0.1  # Nominal extraction cost
        return min(market_price, extraction_cost) if market_price > 0 else extraction_cost
    
    # Option 3: Crafting cost (if multiple recipes, use cheapest)
    min_craft_cost = float('inf')
    all_recipes = chain_info.get("all_recipes", [])
    
    for recipe in all_recipes:
        # Calculate crafting cost for this recipe
        # This would require recursive calculation of input costs
        # For now, return market price as fallback
        pass
    
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