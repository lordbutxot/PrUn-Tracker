"""
Cost Calculation Module
Functions for calculating input costs, workforce costs, and profitability metrics
"""

import pandas as pd
from loaders import (
    load_recipe_inputs, load_recipe_outputs, load_buildingrecipes,
    load_workforceneeds, load_byproduct_recipes, load_chains,
    get_market_price
)


# ==================== WORKFORCE COST CALCULATIONS ====================

def calculate_workforce_consumable_cost(wf_type, hours, workforce_amount, market_prices, wf_consumables, exchange="AI1"):
    """
    Calculate workforce consumable cost.
    
    Args:
        wf_type: Workforce type (PIONEER, SETTLER, etc.)
        hours: Production time in hours
        workforce_amount: Number of workers (e.g., 100 for BMP)
        market_prices: DataFrame from load_market_data()
        wf_consumables: Dict from load_workforceneeds()
        exchange: Exchange code
    
    Returns:
        Total workforce consumable cost as float
    """
    if wf_type not in wf_consumables:
        return 0.0
    
    consumables = wf_consumables[wf_type]
    total = 0.0
    
    for ticker, amt_per_hour_per_worker in consumables.items():
        qty = amt_per_hour_per_worker * workforce_amount * hours
        price = get_market_price(ticker, market_prices, exchange)
        total += qty * price
    
    return total


def calculate_workforce_cost_for_recipe(recipe_key, buildingrecipes_df, workforceneeds, market_prices, exchange="AI1"):
    """
    Calculate workforce cost for a specific recipe.
    
    Args:
        recipe_key: Recipe identifier (e.g., "BMP:1xC-2xH=>200xPE")
        buildingrecipes_df: DataFrame from load_buildingrecipes()
        workforceneeds: Dict from load_workforceneeds()
        market_prices: DataFrame from load_market_data()
        exchange: Exchange code
    
    Returns:
        Workforce cost as float
    """
    if buildingrecipes_df is None or recipe_key not in buildingrecipes_df.index:
        return 0.0
    
    recipe_info = buildingrecipes_df.loc[recipe_key]
    
    try:
        time_minutes = float(recipe_info.get("Time", 0))
        time_hours = time_minutes / 60
        workforce_type = recipe_info.get("Workforce", None)
        workforce_amount = float(recipe_info.get("WorkforceAmount", 0))
        
        if workforce_type and workforce_amount > 0:
            return calculate_workforce_consumable_cost(
                workforce_type, time_hours, workforce_amount,
                market_prices, workforceneeds, exchange
            )
    except Exception as e:
        print(f"[WARN] Error calculating workforce cost for {recipe_key}: {e}")
    
    return 0.0


# ==================== INPUT COST CALCULATIONS ====================

def calculate_material_input_cost(recipe_key, recipe_inputs_df, market_prices, exchange="AI1"):
    """
    Calculate the cost of material inputs for a recipe.
    
    Args:
        recipe_key: Recipe identifier
        recipe_inputs_df: DataFrame from load_recipe_inputs()
        market_prices: DataFrame from load_market_data()
        exchange: Exchange code
    
    Returns:
        Material input cost as float
    """
    inputs = recipe_inputs_df[recipe_inputs_df['Key'] == recipe_key]
    total_cost = 0.0
    
    for _, inp in inputs.iterrows():
        input_ticker = inp['Material']
        try:
            amount = float(inp['Amount'])
        except Exception:
            amount = 0
        price = get_market_price(input_ticker, market_prices, exchange)
        total_cost += amount * price
    
    return total_cost


def calculate_input_cost(ticker, recipe_inputs_df, recipe_outputs_df, buildingrecipes_df, 
                        workforceneeds, market_prices, exchange="AI1"):
    """
    Calculate the minimum input cost for producing a material (best recipe).
    Includes both material inputs and workforce consumables.
    
    Args:
        ticker: Material ticker to calculate cost for
        recipe_inputs_df: DataFrame from load_recipe_inputs()
        recipe_outputs_df: DataFrame from load_recipe_outputs()
        buildingrecipes_df: DataFrame from load_buildingrecipes()
        workforceneeds: Dict from load_workforceneeds()
        market_prices: DataFrame from load_market_data()
        exchange: Exchange code
    
    Returns:
        Minimum input cost as float
    """
    recipes = recipe_outputs_df[recipe_outputs_df['Material'] == ticker]
    if recipes.empty:
        return 0  # No recipe found - raw material or tier 0

    min_cost = None
    
    for _, recipe_row in recipes.iterrows():
        recipe_key = recipe_row['Key']
        
        # Material input cost
        material_cost = calculate_material_input_cost(recipe_key, recipe_inputs_df, market_prices, exchange)
        
        # Workforce cost
        workforce_cost = calculate_workforce_cost_for_recipe(
            recipe_key, buildingrecipes_df, workforceneeds, market_prices, exchange
        )
        
        total_cost = material_cost + workforce_cost
        
        if min_cost is None or total_cost < min_cost:
            min_cost = total_cost
    
    return min_cost if min_cost is not None else 0


def calculate_detailed_costs(ticker, recipe_inputs_df, recipe_outputs_df, buildingrecipes_df,
                            workforceneeds, ask_prices, bid_prices, specific_recipe=None):
    """
    Calculate separate costs for Ask and Bid price scenarios.
    Returns per-unit costs for the specified recipe, or best (cheapest) recipe if not specified.
    
    Args:
        ticker: Material ticker
        recipe_inputs_df: DataFrame from load_recipe_inputs()
        recipe_outputs_df: DataFrame from load_recipe_outputs()
        buildingrecipes_df: DataFrame from load_buildingrecipes()
        workforceneeds: Dict from load_workforceneeds()
        ask_prices: DataFrame with Ask_Price column
        bid_prices: DataFrame with Bid_Price column
        specific_recipe: Optional - specific recipe string to calculate (e.g., "FP:1xALG-1xGRN-1xNUT=>10xRAT")
    
    Returns:
        Dict with keys: input_cost_ask, input_cost_bid, workforce_cost_ask, workforce_cost_bid
    """
    recipes = recipe_outputs_df[recipe_outputs_df['Material'] == ticker]
    if recipes.empty:
        return {
            'input_cost_ask': 0, 'input_cost_bid': 0,
            'workforce_cost_ask': 0, 'workforce_cost_bid': 0
        }

    # If specific recipe requested, filter to only that recipe
    if specific_recipe:
        recipes = recipes[recipes['Key'] == specific_recipe]
        if recipes.empty:
            return {
                'input_cost_ask': 0, 'input_cost_bid': 0,
                'workforce_cost_ask': 0, 'workforce_cost_bid': 0
            }

    min_total_cost = None
    best_costs = None
    
    for _, recipe_row in recipes.iterrows():
        recipe_key = recipe_row['Key']
        
        # Material input costs (Ask and Bid)
        inputs = recipe_inputs_df[recipe_inputs_df['Key'] == recipe_key]
        material_input_cost_ask = 0
        material_input_cost_bid = 0
        
        for _, inp in inputs.iterrows():
            input_ticker = inp['Material']
            try:
                amount = float(inp['Amount'])
            except Exception:
                amount = 0
            ask_price = float(ask_prices.get(input_ticker, 0))
            bid_price = float(bid_prices.get(input_ticker, 0))
            material_input_cost_ask += amount * ask_price
            material_input_cost_bid += amount * bid_price

        # Workforce costs (Ask and Bid)
        workforce_cost_ask = 0
        workforce_cost_bid = 0
        
        if buildingrecipes_df is not None and recipe_key in buildingrecipes_df.index:
            recipe_info = buildingrecipes_df.loc[recipe_key]
            try:
                time_minutes = float(recipe_info.get("Time", 0))
                time_hours = time_minutes / 60
                workforce_type = recipe_info.get("Workforce", None)
                workforce_amount = float(recipe_info.get("WorkforceAmount", 0))
                
                if workforce_type and workforce_type in workforceneeds:
                    consumables = workforceneeds[workforce_type]
                    for item, per_hour in consumables.items():
                        try:
                            total_needed = float(per_hour) * workforce_amount * time_hours
                        except Exception:
                            total_needed = 0
                        ask_price = float(ask_prices.get(item, 0))
                        bid_price = float(bid_prices.get(item, 0))
                        workforce_cost_ask += total_needed * ask_price
                        workforce_cost_bid += total_needed * bid_price
            except Exception as e:
                print(f"[WARN] Error calculating workforce cost for {recipe_key}: {e}")

        # Get units produced per recipe
        units_per_recipe = 1
        try:
            units_per_recipe = float(recipe_row.get('Amount', 1))
        except Exception:
            units_per_recipe = 1
        
        # Calculate per-unit costs
        input_cost_ask_per_unit = material_input_cost_ask / units_per_recipe if units_per_recipe > 0 else 0
        input_cost_bid_per_unit = material_input_cost_bid / units_per_recipe if units_per_recipe > 0 else 0
        workforce_cost_ask_per_unit = workforce_cost_ask / units_per_recipe if units_per_recipe > 0 else 0
        workforce_cost_bid_per_unit = workforce_cost_bid / units_per_recipe if units_per_recipe > 0 else 0
        
        # Use average for comparison to find best recipe
        total_cost_avg = (input_cost_ask_per_unit + input_cost_bid_per_unit) / 2 + \
                        (workforce_cost_ask_per_unit + workforce_cost_bid_per_unit) / 2
        
        if min_total_cost is None or total_cost_avg < min_total_cost:
            min_total_cost = total_cost_avg
            best_costs = {
                'input_cost_ask': input_cost_ask_per_unit,
                'input_cost_bid': input_cost_bid_per_unit,
                'workforce_cost_ask': workforce_cost_ask_per_unit,
                'workforce_cost_bid': workforce_cost_bid_per_unit
            }
    
    return best_costs if best_costs is not None else {
        'input_cost_ask': 0, 'input_cost_bid': 0,
        'workforce_cost_ask': 0, 'workforce_cost_bid': 0
    }


# ==================== BYPRODUCT COST ALLOCATION ====================

def allocate_byproduct_costs(recipe_id, total_input_cost, market_prices, exchange="AI1"):
    """
    Allocate costs for recipes with multiple outputs based on market value proportion.
    
    Args:
        recipe_id: Recipe identifier
        total_input_cost: Total cost of all inputs + workforce
        market_prices: DataFrame from load_market_data()
        exchange: Exchange code
    
    Returns:
        Dict of {ticker: allocated_cost_per_unit}
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


# ==================== PROFITABILITY CALCULATIONS ====================

def calculate_profit(ask_price, bid_price, input_cost):
    """
    Calculate profit for ask and bid scenarios.
    
    Args:
        ask_price: Market ask price
        bid_price: Market bid price
        input_cost: Total input cost (materials + workforce)
    
    Returns:
        Tuple of (profit_ask, profit_bid)
    """
    profit_ask = ask_price - input_cost
    profit_bid = bid_price - input_cost
    return profit_ask, profit_bid


def calculate_roi(ask_price, bid_price, input_cost):
    """
    Calculate ROI percentage for ask and bid scenarios.
    
    Args:
        ask_price: Market ask price
        bid_price: Market bid price
        input_cost: Total input cost
    
    Returns:
        Tuple of (roi_ask, roi_bid) as percentages
    """
    if input_cost == 0:
        return 0, 0
    
    roi_ask = ((ask_price - input_cost) / input_cost) * 100
    roi_bid = ((bid_price - input_cost) / input_cost) * 100
    
    return roi_ask, roi_bid


def calculate_investment_score(roi, liquidity, risk, weights=None):
    """
    Calculate investment score combining ROI, liquidity, and risk.
    
    Args:
        roi: Return on investment percentage
        liquidity: Liquidity ratio (0-1)
        risk: Risk level (0-1)
        weights: Dict with 'roi', 'liquidity', 'risk' weights (default: 0.4, 0.3, 0.3)
    
    Returns:
        Investment score (0-100)
    """
    if weights is None:
        weights = {'roi': 0.4, 'liquidity': 0.3, 'risk': 0.3}
    
    # Normalize ROI to 0-1 scale (assuming max ROI of 500%)
    roi_normalized = min(roi / 500, 1.0) if roi > 0 else 0
    
    # Risk is inverted (lower risk is better)
    risk_score = 1 - risk
    
    score = (roi_normalized * weights['roi'] + 
             liquidity * weights['liquidity'] + 
             risk_score * weights['risk']) * 100
    
    return max(0, min(100, score))


def calculate_viability(profit_ask, profit_bid, traded_volume, supply, demand):
    """
    Calculate production viability based on profitability and market conditions.
    
    Args:
        profit_ask: Profit when selling at ask price
        profit_bid: Profit when selling at bid price
        traded_volume: Recent traded volume
        supply: Market supply
        demand: Market demand
    
    Returns:
        Viability rating: "Highly Viable", "Viable", "Marginal", "Not Viable"
    """
    # Profitable?
    is_profitable = profit_ask > 0 or profit_bid > 0
    
    # Market activity
    has_volume = traded_volume > 0
    has_demand = demand > supply * 0.1  # Demand > 10% of supply
    
    if is_profitable and has_volume and has_demand:
        return "Highly Viable"
    elif is_profitable and (has_volume or has_demand):
        return "Viable"
    elif is_profitable:
        return "Marginal"
    else:
        return "Not Viable"


def calculate_risk_level(price_spread, saturation, volatility=None):
    """
    Calculate risk level based on market conditions.
    
    Args:
        price_spread: Difference between ask and bid prices
        saturation: Market saturation (supply/demand ratio)
        volatility: Price volatility (optional)
    
    Returns:
        Risk level: "Very Low", "Low", "Medium", "High", "Very High"
    """
    risk_score = 0
    
    # Spread risk (higher spread = higher risk)
    if price_spread > 0:
        spread_ratio = price_spread / (price_spread + 1)  # Normalize
        risk_score += spread_ratio * 0.4
    
    # Saturation risk
    if saturation > 2:
        risk_score += 0.3
    elif saturation > 1.5:
        risk_score += 0.2
    elif saturation > 1:
        risk_score += 0.1
    
    # Volatility risk (if available)
    if volatility is not None:
        risk_score += volatility * 0.3
    
    # Convert to category
    if risk_score < 0.2:
        return "Very Low"
    elif risk_score < 0.4:
        return "Low"
    elif risk_score < 0.6:
        return "Medium"
    elif risk_score < 0.8:
        return "High"
    else:
        return "Very High"


# ==================== PER-UNIT COST BREAKDOWN ====================

def calculate_cost_per_unit(recipe_key, recipe_inputs_df, recipe_outputs_df, buildingrecipes_df,
                           workforceneeds, market_prices, exchange="AI1"):
    """
    Calculate detailed cost breakdown per unit of output.
    
    Args:
        recipe_key: Recipe identifier
        recipe_inputs_df: DataFrame from load_recipe_inputs()
        recipe_outputs_df: DataFrame from load_recipe_outputs()
        buildingrecipes_df: DataFrame from load_buildingrecipes()
        workforceneeds: Dict from load_workforceneeds()
        market_prices: DataFrame from load_market_data()
        exchange: Exchange code
    
    Returns:
        Dict with: material_cost_per_unit, workforce_cost_per_unit, total_cost_per_unit, units_produced
    """
    # Material cost
    material_cost = calculate_material_input_cost(recipe_key, recipe_inputs_df, market_prices, exchange)
    
    # Workforce cost
    workforce_cost = calculate_workforce_cost_for_recipe(
        recipe_key, buildingrecipes_df, workforceneeds, market_prices, exchange
    )
    
    # Units produced
    output_row = recipe_outputs_df[recipe_outputs_df['Key'] == recipe_key]
    units_produced = float(output_row.iloc[0]['Amount']) if not output_row.empty else 1
    
    # Per-unit costs
    material_cost_per_unit = material_cost / units_produced if units_produced > 0 else 0
    workforce_cost_per_unit = workforce_cost / units_produced if units_produced > 0 else 0
    total_cost_per_unit = material_cost_per_unit + workforce_cost_per_unit
    
    return {
        'material_cost_per_unit': material_cost_per_unit,
        'workforce_cost_per_unit': workforce_cost_per_unit,
        'total_cost_per_unit': total_cost_per_unit,
        'units_produced': units_produced,
        'material_cost_total': material_cost,
        'workforce_cost_total': workforce_cost
    }
