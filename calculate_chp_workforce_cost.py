import sys
import os
import json

# Simple workforce cost calculation test
cache_dir = os.path.join(os.path.dirname(__file__), 'pu-tracker', 'cache')

# Load required data
with open(os.path.join(cache_dir, 'buildings.json'), 'r') as f:
    buildings = json.load(f)

with open(os.path.join(cache_dir, 'workforceneeds.json'), 'r') as f:
    workforceneeds_raw = json.load(f)

with open(os.path.join(cache_dir, 'daily_analysis_enhanced.csv'), 'r') as f:
    # Simple CSV parsing for market prices
    lines = f.readlines()
    headers = lines[0].strip().split(',')
    market_data = {}
    for line in lines[1:]:
        values = line.strip().split(',')
        if len(values) > len(headers):
            continue
        row = dict(zip(headers, values))
        ticker = row.get('Ticker', '')
        exchange = row.get('Exchange', '')
        if ticker and exchange == 'AI1':
            market_data[ticker] = {
                'ask': float(row.get('Ask_Price', 0) or 0),
                'bid': float(row.get('Bid_Price', 0) or 0)
            }

# Convert workforceneeds to usable format
workforceneeds = {}
for wf in workforceneeds_raw:
    name = wf.get("WorkforceType")
    if name:
        needs = wf.get("Needs", [])
        necessary = {}
        luxury = {}
        for need in needs:
            ticker = need.get("MaterialTicker")
            amount = need.get("Amount", 0)
            material_name = need.get("MaterialName", "")
            if ticker and amount:
                # Convert from per-100-workers-per-day to per-worker-per-hour
                per_hour_per_worker = float(amount) / 100.0 / 24.0
                if "Luxury" in material_name:
                    luxury[ticker] = per_hour_per_worker
                else:
                    necessary[ticker] = per_hour_per_worker
        workforceneeds[name] = {"necessary": necessary, "luxury": luxury}

print("=== CHP Recipe Workforce Cost Calculation ===")

# Recipe details
recipe_duration_minutes = 50112  # From buildingrecipes.csv
recipe_duration_hours = recipe_duration_minutes / 60

# Get workforce requirements for CHP
workforce_reqs = {}
if 'CHP' in buildings:
    building = buildings['CHP']
    for wf_type in ['PIONEER', 'SETTLER', 'TECHNICIAN', 'ENGINEER', 'SCIENTIST']:
        wf_key = wf_type.lower() + 's'
        amount = building.get(wf_key, 0)
        if amount > 0:
            workforce_reqs[wf_type] = amount

print(f"Workforce requirements: {workforce_reqs}")
print(f"Recipe duration: {recipe_duration_minutes} minutes ({recipe_duration_hours:.1f} hours)")

# Calculate workforce costs
total_workforce_cost_ask = 0
total_workforce_cost_bid = 0

for wf_type, wf_amount in workforce_reqs.items():
    if wf_type in workforceneeds:
        wf_data = workforceneeds[wf_type]
        print(f"\n{wf_type} ({wf_amount} workers):")

        # Necessary consumables
        for item, per_hour in wf_data["necessary"].items():
            total_needed = per_hour * wf_amount * recipe_duration_hours
            ask_price = market_data.get(item, {}).get('ask', 0)
            bid_price = market_data.get(item, {}).get('bid', 0)
            ask_cost = total_needed * ask_price
            bid_cost = total_needed * bid_price
            total_workforce_cost_ask += ask_cost
            total_workforce_cost_bid += bid_cost
            print(f"  {item}: {total_needed:.1f} units @ {ask_price:.2f} ICA = {ask_cost:.2f} ICA (ask)")

        # Luxury consumables
        for item, per_hour in wf_data["luxury"].items():
            total_needed = per_hour * wf_amount * recipe_duration_hours
            ask_price = market_data.get(item, {}).get('ask', 0)
            bid_price = market_data.get(item, {}).get('bid', 0)
            ask_cost = total_needed * ask_price
            bid_cost = total_needed * bid_price
            total_workforce_cost_ask += ask_cost
            total_workforce_cost_bid += bid_cost
            print(f"  {item}: {total_needed:.1f} units @ {ask_price:.2f} ICA = {ask_cost:.2f} ICA (ask)")

print("\n=== Total Workforce Costs ===")
print(f"Total workforce cost (ask prices): {total_workforce_cost_ask:.2f} ICA")
print(f"Total workforce cost (bid prices): {total_workforce_cost_bid:.2f} ICA")

# Compare with material costs
h2o_ask = market_data.get('H2O', {}).get('ask', 0)
hal_ask = market_data.get('HAL', {}).get('ask', 0)
material_cost_ask = 1 * h2o_ask + 3 * hal_ask

print("\n=== Comparison ===")
print(f"Material input cost (ask): {material_cost_ask:.2f} ICA")
print(f"Workforce cost (ask): {total_workforce_cost_ask:.2f} ICA")
print(f"Total cost (ask): {material_cost_ask + total_workforce_cost_ask:.2f} ICA")

# Per unit costs (recipe produces 1 CL + 2 NA)
total_output_units = 3  # 1 CL + 2 NA
workforce_cost_per_unit_ask = total_workforce_cost_ask / total_output_units
print(f"Workforce cost per output unit: {workforce_cost_per_unit_ask:.2f} ICA")