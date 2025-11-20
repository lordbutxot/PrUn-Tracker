# Multi-Recipe Selector Feature

## Overview
The Price Analyser now supports **multi-recipe selection** for materials that can be produced using different recipes. Instead of seeing only aggregated data, players can now:
1. Select a **Material** (e.g., AAR, DW, PE)
2. Choose a specific **Recipe** (e.g., BMP:1xC-2xH=>200xPE)
3. Select an **Exchange** (AI1, CI1, CI2, IC1, NC1, NC2)

This allows accurate cost comparison between different production methods.

## Implementation Details

### Frontend Changes (AppsScript_Index.html)
- Added third dropdown: **Recipe Selector**
- Layout changed from 2-column to 3-column grid
- Recipe dropdown dynamically populates when material is selected
- Shows "-- All Recipes (Best Cost) --" as default (selects lowest-cost recipe automatically)

### Backend Changes (AppsScript_PriceAnalyser.js)

#### New Function: `getRecipesForMaterial(material)`
**Purpose:** Fetch all unique recipes that produce the selected material

**Logic:**
1. Queries "Price Analyser Data" sheet
2. Filters rows where Ticker (column B) matches selected material
3. Extracts unique Recipe values (column C)
4. Parses building prefix from recipe format (e.g., "BMP:..." → "BMP")
5. Returns array of recipe objects: `{key, label, building}`

**Example Return:**
```javascript
[
  { key: "BMP:1xC-2xH=>200xPE", label: "BMP:1xC-2xH=>200xPE", building: "BMP" },
  { key: "PPF:100xC=>200xPE", label: "PPF:100xC=>200xPE", building: "PPF" }
]
```

#### Updated Function: `getCalculationData(material, exchange, recipe)`
**New Parameter:** `recipe` (optional)

**Logic:**
1. If `recipe` is provided: Find exact match on Ticker + Exchange + Recipe
2. If `recipe` is empty: Find **lowest-cost recipe** for Ticker + Exchange combination
   - Calculates total cost = Input Cost Ask + Workforce Cost Ask
   - Returns data for recipe with minimum cost
3. Returns comprehensive cost/profit data for the selected recipe

**Cost Selection Algorithm:**
```javascript
// For each matching Ticker + Exchange combination:
const totalCost = inputCostAsk + workforceCostAsk;
if (totalCost < lowestCost) {
  lowestCost = totalCost;
  bestRow = i; // Remember this row
}
```

### Data Structure Changes (generate_report_tabs.py)

#### Enhanced Reference DataFrame
**Added Column:** `Recipe` (column C)

**New Column Order:**
1. LookupKey (A) - Ticker+Exchange concatenation
2. Ticker (B) - Material code (e.g., "AAR")
3. **Recipe (C)** - Full recipe string (e.g., "BMP:1xC-2xH=>200xPE")
4. Material Name (D)
5. Exchange (E)
6. Ask_Price (F)
7. Bid_Price (G)
8. Input Cost Ask (H)
9. Input Cost Bid (I)
10. Workforce Cost Ask (J)
11. Workforce Cost Bid (K)
12. Amount per Recipe (L)
13. Supply (M)
14. Demand (N)

**Data Filling:**
- Numeric columns filled with `0` for NaN values
- Recipe column filled with `'N/A'` for missing values

## User Experience

### Workflow
1. **Select Material:** Choose from dropdown (e.g., "PE" - Polyethylene)
2. **Recipe Dropdown Populates:** Shows all available recipes:
   - "-- All Recipes (Best Cost) --" (default)
   - "BMP:1xC-2xH=>200xPE (BMP)"
   - "PPF:100xC=>200xPE (PPF)"
3. **Select Recipe:** 
   - Leave as "All Recipes" to auto-select cheapest
   - Or choose specific recipe to analyze
4. **Select Exchange:** Choose market (AI1, CI1, etc.)
5. **View Results:** Cost breakdown, profitability, ROI for selected recipe

### Example Scenario
**Material:** Polyethylene (PE)

**Available Recipes:**
- **BMP Recipe:** `1xC + 2xH => 200xPE`
- **PPF Recipe:** `100xC => 200xPE`

**Cost Comparison (CI1 Exchange):**
- BMP: Input Cost $50, Workforce Cost $5, **Total $55**
- PPF: Input Cost $80, Workforce Cost $3, **Total $83**

**Result:** Selecting "All Recipes" automatically shows BMP data (lowest cost).

## Recipe Format

### Standard Format
`BUILDING:inputs=>outputs`

**Examples:**
- `BMP:1xC-2xH=>200xPE` - Basic Material Plant: 1 Carbon + 2 Hydrogen → 200 Polyethylene
- `AAF:10xSAR-1xSNM-1000xSPT-1xSST-2xTOR-4xTRS=>1xGWS` - Advanced Assembly Facility recipe
- `PPF:100xC=>200xPE` - Polymer Processing Facility recipe

### Building Prefixes
Common building codes used in recipes:
- **BMP** - Basic Material Plant
- **PPF** - Polymer Processing Facility
- **AAF** - Advanced Assembly Facility
- **SPP** - Solar Panel Plant
- **EEP** - Electronic Equipment Plant
- And many more...

## Technical Benefits

### 1. Accurate Cost Analysis
- No more averaging costs across different recipes
- Players can see actual input requirements
- Workforce costs calculated per specific recipe

### 2. Strategic Decision Making
- Compare alternative production methods
- Identify most profitable recipe for current market conditions
- Evaluate tech tree investment decisions

### 3. Performance Optimization
- Single query fetches recipe-specific data
- Client-side filtering reduces server load
- Default "best cost" option provides quick answers

## Deployment Instructions

### 1. Update Python Pipeline
Run the data processing pipeline to regenerate sheets with Recipe column:
```bash
cd pu-tracker\historical_data
python main.py
```

### 2. Update Google Apps Script
1. Open Google Sheet: [PrUn-Profit Tracker](https://docs.google.com/spreadsheets/d/1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI/edit)
2. Go to **Extensions → Apps Script**
3. Replace code with `AppsScript_PriceAnalyser.js` content
4. Save and redeploy web app

### 3. Update HTML Interface
1. In Apps Script editor, go to **Files → Index.html**
2. Replace with `AppsScript_Index.html` content
3. Save changes

### 4. Test Deployment
1. Open deployed web app URL
2. Select a material with multiple recipes (e.g., PE, DW, AAR)
3. Verify recipe dropdown populates correctly
4. Test both "All Recipes" and specific recipe selection
5. Confirm cost data displays accurately

## Maintenance Notes

### Adding New Buildings/Recipes
1. Update `buildingrecipes.csv` cache with new recipes
2. Run pipeline to process new data
3. Recipe dropdown will automatically include new recipes

### Troubleshooting

**Issue:** Recipe dropdown shows no options
- **Check:** Material has recipes in processed_data.csv
- **Verify:** Recipe column (C) in "Price Analyser Data" sheet is populated
- **Debug:** Use `getRecipesForMaterial('TICKER')` in Apps Script console

**Issue:** Wrong recipe selected with "All Recipes"
- **Check:** Input Cost Ask and Workforce Cost Ask values
- **Verify:** Cost calculation in `getCalculationData()` logic
- **Debug:** Check `lowestCost` variable in script execution logs

**Issue:** Data shows "N/A" for recipe
- **Check:** Source data in processed_data.csv has Recipe column
- **Verify:** generate_report_tabs.py includes Recipe in reference_df
- **Fix:** Rerun pipeline to regenerate data

## Future Enhancements

### Potential Improvements
1. **Recipe Comparison View:** Show cost breakdown for all recipes side-by-side
2. **Building Filter:** Filter recipes by specific building types
3. **Input Material Links:** Click input materials to navigate to their analysis
4. **Historical Recipe Costs:** Track cost trends over time per recipe
5. **Recipe Efficiency Metrics:** Calculate material efficiency ratios
6. **Byproduct Credits:** Show revenue from recipe byproducts

### Data Structure Extensions
- Add `Building` column for faster filtering
- Include `Recipe Inputs` and `Recipe Outputs` columns
- Store `Recipe Duration` for throughput analysis
- Add `Tech Tree Requirement` metadata

## Version History

**v1.0 (Current)**
- Initial multi-recipe selector implementation
- Basic cost comparison functionality
- Auto-selection of lowest-cost recipe
- Recipe dropdown with building prefix display

---

*Last Updated: 2024*
*Author: PrUn-Tracker Development Team*
