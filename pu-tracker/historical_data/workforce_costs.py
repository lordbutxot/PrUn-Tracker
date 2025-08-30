import pandas as pd
import json
import os
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"

# --- Load Data ---
def load_recipe_inputs():
    return pd.read_csv(CACHE_DIR / "recipe_inputs.csv")

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
        # If your JSON is per day, convert to per hour here:
        wf_consumables[wf_type] = {need["MaterialTicker"]: need["Amount"] / 24 for need in needs}
        # If your JSON is per hour, just use need["Amount"]
    return wf_consumables

# --- Price Lookup ---
def get_market_price(ticker, market_prices, exchange="AI1"):
    row = market_prices[(market_prices['Ticker'] == ticker) & (market_prices['Exchange'] == exchange)]
    if not row.empty:
        # Use the correct column name with underscore
        return float(row.iloc[0]['Ask_Price'])  # or 'Bid_Price' as appropriate
    return 0.0

# --- Workforce Consumable Cost ---
def calculate_workforce_consumable_cost(wf_type, hours, market_prices, wf_consumables, exchange="AI1"):
    total = 0.0
    consumables = wf_consumables.get(wf_type, {})
    for ticker, amt_per_hour in consumables.items():
        qty = amt_per_hour * hours
        price = get_market_price(ticker, market_prices, exchange)
        total += qty * price
    return total

# --- Main Input Cost Calculation ---
def calculate_input_costs_for_recipe(recipe_row, market_prices, wf_consumables, exchange="AI1", stack_size=100):
    """
    recipe_row: a row from your recipes DataFrame, must have:
        - 'Recipe'
        - 'WorkforceType'
        - 'HoursPerRecipe'
        - 'UnitsPerRecipe'
        - 'InputMaterials': dict of {ticker: qty}
    """
    # 1. Direct input cost
    direct_input_cost = 0.0
    for ticker, qty in recipe_row['InputMaterials'].items():
        price = get_market_price(ticker, market_prices, exchange)
        direct_input_cost += qty * price

    # 2. Workforce consumable cost
    wf_type = recipe_row['WorkforceType']
    hours = recipe_row['HoursPerRecipe']
    wf_cost = calculate_workforce_consumable_cost(wf_type, hours, market_prices, wf_consumables, exchange)

    # 3. Total input cost for the recipe
    total_input_cost = direct_input_cost + wf_cost

    # 4. Per unit and per stack
    units_per_recipe = recipe_row['UnitsPerRecipe']
    input_cost_per_unit = total_input_cost / units_per_recipe if units_per_recipe else 0
    input_cost_per_stack = input_cost_per_unit * stack_size

    # 5. Per hour
    input_cost_per_hour = total_input_cost / hours if hours else 0

    return {
        "Input Cost per Recipe": total_input_cost,
        "Input Cost per Unit": input_cost_per_unit,
        "Input Cost per Stack": input_cost_per_stack,
        "Input Cost per Hour": input_cost_per_hour,
        "Direct Input Cost": direct_input_cost,
        "Workforce Consumable Cost": wf_cost
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