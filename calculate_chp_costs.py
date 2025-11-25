import csv
import json
import os

# Load market data
market_data = {}
with open('cache/daily_analysis_enhanced.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticker = row['Ticker']
        exchange = row['Exchange']
        if ticker in ['H2O', 'HAL', 'CL', 'NA'] and exchange == 'AI1':
            if ticker not in market_data:
                market_data[ticker] = row
                print(f'{ticker}: Ask={row["Ask_Price"]}, Bid={row["Bid_Price"]}')

print()
print('Recipe: CHP:1xH2O-3xHAL=>1xCL-2xNA')
print('Inputs: 1x H2O + 3x HAL')
print('Outputs: 1x CL + 2x NA')
print('Duration: 50,112 minutes (835.2 hours)')
print('Workforce: 20 Pioneers + 60 Settlers')
print()

# Calculate input costs
h2o_ask = float(market_data.get('H2O', {}).get('Ask_Price', 0))
h2o_bid = float(market_data.get('H2O', {}).get('Bid_Price', 0))
hal_ask = float(market_data.get('HAL', {}).get('Ask_Price', 0))
hal_bid = float(market_data.get('HAL', {}).get('Bid_Price', 0))

material_cost_ask = 1 * h2o_ask + 3 * hal_ask
material_cost_bid = 1 * h2o_bid + 3 * hal_bid

print(f'Material Input Cost (Ask prices): {material_cost_ask:.2f} ICA')
print(f'Material Input Cost (Bid prices): {material_cost_bid:.2f} ICA')
print()

# Load workforce cost data (from our previous calculation)
workforce_cost_ask = 76623.34  # From our calculation
workforce_cost_bid = 73542.14  # From our calculation

print(f'Workforce Cost (Ask prices): {workforce_cost_ask:.2f} ICA')
print(f'Workforce Cost (Bid prices): {workforce_cost_bid:.2f} ICA')
print()

total_cost_ask = material_cost_ask + workforce_cost_ask
total_cost_bid = material_cost_bid + workforce_cost_bid

print(f'Total Input Cost (Ask prices): {total_cost_ask:.2f} ICA')
print(f'Total Input Cost (Bid prices): {total_cost_bid:.2f} ICA')
print()

# Output values
cl_ask = float(market_data.get('CL', {}).get('Ask_Price', 0))
cl_bid = float(market_data.get('CL', {}).get('Bid_Price', 0))
na_ask = float(market_data.get('NA', {}).get('Ask_Price', 0))
na_bid = float(market_data.get('NA', {}).get('Bid_Price', 0))

print(f'CL value (Ask/Bid): {cl_ask:.2f} / {cl_bid:.2f} ICA')
print(f'NA value (Ask/Bid): {na_ask:.2f} / {na_bid:.2f} ICA')
print()

# Cost allocation - now includes workforce costs
cl_value_ask = cl_ask
na_value_ask = na_ask
total_value_ask = cl_value_ask + na_value_ask

cl_value_bid = cl_bid
na_value_bid = na_bid
total_value_bid = cl_value_bid + na_value_bid

if total_value_ask > 0:
    cl_cost_ask = total_cost_ask * (cl_value_ask / total_value_ask)
    na_cost_ask = total_cost_ask * (na_value_ask / total_value_ask)
else:
    cl_cost_ask = total_cost_ask / 2
    na_cost_ask = total_cost_ask / 2

if total_value_bid > 0:
    cl_cost_bid = total_cost_bid * (cl_value_bid / total_value_bid)
    na_cost_bid = total_cost_bid * (na_value_bid / total_value_bid)
else:
    cl_cost_bid = total_cost_bid / 2
    na_cost_bid = total_cost_bid / 2

print('Cost Allocation (Ask prices):')
print(f'  CL cost per unit: {cl_cost_ask:.2f} ICA')
print(f'  NA cost per unit: {na_cost_ask:.2f} ICA')
print()

print('Cost Allocation (Bid prices):')
print(f'  CL cost per unit: {cl_cost_bid:.2f} ICA')
print(f'  NA cost per unit: {na_cost_bid:.2f} ICA')
print()

print('Profitability (Ask prices):')
print(f'  CL profit: {cl_ask - cl_cost_ask:.2f} ICA/unit')
print(f'  NA profit: {na_ask - na_cost_ask:.2f} ICA/unit')
print()

print('Profitability (Bid prices):')
print(f'  CL profit: {cl_bid - cl_cost_bid:.2f} ICA/unit')
print(f'  NA profit: {na_bid - na_cost_bid:.2f} ICA/unit')
print()

# Profitability analysis
cl_profit_ask = cl_ask - cl_cost_ask
na_profit_ask = na_ask - na_cost_ask
cl_profit_bid = cl_bid - cl_cost_bid
na_profit_bid = na_bid - na_cost_bid

print('=== ANALYSIS ===')
print('BEFORE FIX (material costs only):')
print('  CL profit: ~2,767 ICA/unit (highly profitable)')
print('  NA profit: ~17 ICA/unit (marginally profitable)')
print()
print('AFTER FIX (material + workforce costs):')
print(f'  CL profit: {cl_profit_ask:.2f} ICA/unit (ask) / {cl_profit_bid:.2f} ICA/unit (bid)')
print(f'  NA profit: {na_profit_ask:.2f} ICA/unit (ask) / {na_profit_bid:.2f} ICA/unit (bid)')
print()
if cl_profit_ask < 0 and na_profit_ask < 0:
    print('CONCLUSION: CHP recipe is UNPROFITABLE when workforce costs are included!')
    print('The workforce costs (~76,000 ICA) dwarf the material costs (~1,200 ICA).')
elif cl_profit_ask > 0 or na_profit_ask > 0:
    print('CONCLUSION: CHP recipe may still be profitable for some outputs.')
else:
    print('CONCLUSION: Mixed profitability - check specific market conditions.')