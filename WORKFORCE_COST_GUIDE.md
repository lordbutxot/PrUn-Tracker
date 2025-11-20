# Workforce Cost Analysis Implementation Guide

## ✅ What's Been Added

### 1. **New Cost Calculation Method** (`data_analyzer.py`)
Added `calculate_detailed_costs()` method that calculates:
- **Input Cost Ask**: Cost of all recipe inputs bought at Ask prices (instant buy)
- **Input Cost Bid**: Cost of all recipe inputs bought at Bid prices (place buy orders)
- **Workforce Cost Ask**: Cost of workforce consumables at Ask prices
- **Workforce Cost Bid**: Cost of workforce consumables at Bid prices

### 2. **Enhanced Price Analyser Data** (`generate_report_tabs.py`)
The "Price Analyser Data" sheet now includes:
- Separate Ask/Bid input costs
- Separate Ask/Bid workforce costs
- Proper cost breakdown per exchange

### 3. **Updated AppsScript** (`AppsScript_PriceAnalyser.js`)
Reads the new columns correctly and displays:
- Precise input costs for Ask vs Bid scenarios
- Real workforce costs calculated from market data
- Accurate total production costs for all 4 scenarios

## 📊 New Column Structure

**"Price Analyser Data" Sheet:**
```
A: LookupKey (e.g., "AARCI1")
B: Ticker (e.g., "AAR")
C: Material Name
D: Exchange (e.g., "CI1")
E: Ask_Price
F: Bid_Price
G: Input Cost Ask        ← NEW - Real cost of inputs at Ask prices
H: Input Cost Bid        ← NEW - Real cost of inputs at Bid prices
I: Workforce Cost Ask    ← NEW - Real workforce consumables cost at Ask
J: Workforce Cost Bid    ← NEW - Real workforce consumables cost at Bid
K: Amount per Recipe
L: Supply
M: Demand
```

## 🚀 How to Use

### Step 1: Run the Data Pipeline
```powershell
cd e:\Github\PrUn_Tracker\PrUn-Tracker\pu-tracker\historical_data
python main.py
```

This will:
1. Fetch all market data
2. Calculate input costs at Ask prices
3. Calculate input costs at Bid prices
4. Calculate workforce consumable costs at Ask prices
5. Calculate workforce consumable costs at Bid prices
6. Upload to Google Sheets with new columns

### Step 2: Deploy Updated AppsScript
1. Open your Google Sheet
2. Go to **Extensions → Apps Script**
3. Replace the code with updated `AppsScript_PriceAnalyser.js`
4. Replace the HTML with updated `AppsScript_Index.html`
5. **Deploy → Manage deployments → Edit → New version → Deploy**

### Step 3: Test the Price Analyser
1. Open the web app
2. Select a material (e.g., "AAR")
3. Select an exchange (e.g., "CI1")
4. Verify you see:
   - Different values for Input Cost Ask vs Bid
   - Different values for Workforce Cost Ask vs Bid
   - Accurate profit calculations for all 4 scenarios

## 📈 What Users Will See

### Cost Breakdown Section:
```
Input Cost (Ask Prices):     $245.50  ← Real cost buying inputs instantly
Input Cost (Bid Prices):     $198.20  ← Real cost if waiting for orders
Workforce Cost (Ask):        $12.75   ← Real workforce consumables (Ask)
Workforce Cost (Bid):        $10.30   ← Real workforce consumables (Bid)
Total Production Cost (Ask): $258.25
Total Production Cost (Bid): $208.50
```

### Profitability - All Scenarios:
```
Profit (Ask + Ask):  $41.75   ← Sell fast, buy fast (highest cost, instant)
Profit (Ask + Bid):  $91.50   ← Sell fast, wait for inputs (best margin)
Profit (Bid + Ask):  -$8.25   ← Wait to sell, buy fast (risky)
Profit (Bid + Bid):  $41.50   ← Wait to sell, wait for inputs (patient)
```

## 🔧 How It Works

### Workforce Cost Calculation:
1. **Identify recipe**: Find the recipe for the material
2. **Get workforce type**: Pioneers, Settlers, Technicians, etc.
3. **Get recipe duration**: Time to produce one batch
4. **Load workforce needs**: What consumables each workforce type needs per hour
5. **Calculate consumption**: `consumables_per_hour * workers * hours`
6. **Price at market**: Look up Ask/Bid prices for DW, RAT, PWO, etc.
7. **Sum totals**: Total workforce cost for the recipe

### Example (Pioneers making AAR):
```
Recipe: AAR (4 hours, 100 workers type: Pioneers)

Pioneers need per hour per 100 workers:
- 12 DW  (Drinking Water)
- 8  RAT (Rations)
- 3  HE  (H-E Fuel)

For 4 hours:
- DW:  12 * 4 = 48 units needed
- RAT:  8 * 4 = 32 units needed
- HE:   3 * 4 = 12 units needed

At Ask prices (CI1):
- DW:  48 * $2.50 = $120
- RAT: 32 * $5.75 = $184
- HE:  12 * $8.20 = $98.40
Total Workforce Cost Ask = $402.40

At Bid prices (CI1):
- DW:  48 * $2.10 = $100.80
- RAT: 32 * $4.90 = $156.80
- HE:  12 * $7.50 = $90
Total Workforce Cost Bid = $347.60

Difference: $54.80 savings by placing orders!
```

## 🎯 Benefits

### For Players:
1. **Accurate cost analysis**: See real production costs
2. **Strategy planning**: Compare instant vs patient production
3. **Profit optimization**: Find the best buy/sell combination
4. **Market timing**: Understand when to place orders vs instant buy

### For Production Planning:
1. **True breakeven**: Know exactly when production becomes profitable
2. **ROI accuracy**: Real return on investment calculations
3. **Risk assessment**: See cost variance between scenarios
4. **Resource allocation**: Optimize which materials to produce

## 🔍 Troubleshooting

### If workforce costs show as 0:
1. Check that `workforceneeds.json` exists in cache
2. Verify recipe has workforce type assigned
3. Ensure workforce consumables have market prices

### If Ask/Bid costs are identical:
1. Check that market data has both Ask and Bid prices
2. Verify the data pipeline ran completely
3. Look for errors in console during calculation

### If calculations seem wrong:
1. Check the recipe inputs are correct
2. Verify market prices are recent
3. Review the workforce needs JSON structure

## 📚 Data Sources

- **Recipe data**: `buildingrecipes.csv`, `recipe_inputs.csv`, `recipe_outputs.csv`
- **Workforce needs**: `workforceneeds.json`
- **Market prices**: `market_data_long.csv` (per exchange, Ask & Bid)
- **Material info**: `materials.csv`

## 🎉 Success Indicators

You'll know it's working when:
- ✅ Input Cost Ask ≠ Input Cost Bid (different values)
- ✅ Workforce Cost Ask ≠ Workforce Cost Bid (different values)
- ✅ All 4 profit scenarios show different amounts
- ✅ Breakeven calculations reflect real cost differences
- ✅ Players can see potential savings by waiting for orders

---

**Note**: The first run will calculate costs for all materials and exchanges. This may take a few minutes. Subsequent runs use cached data and are much faster.
