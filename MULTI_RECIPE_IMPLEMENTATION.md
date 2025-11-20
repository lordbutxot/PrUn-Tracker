# Multi-Recipe Feature - Implementation Summary

## What Changed

### 🎨 User Interface (AppsScript_Index.html)
- **Added:** Recipe dropdown between Material and Exchange selectors
- **Layout:** Changed from 2-column to 3-column grid
- **Behavior:** Recipe dropdown populates dynamically when material is selected
- **Default:** "-- All Recipes (Best Cost) --" automatically selects cheapest recipe

### ⚙️ Backend API (AppsScript_PriceAnalyser.js)
- **New Function:** `getRecipesForMaterial(material)` - Returns all recipes for a material
- **Updated Function:** `getCalculationData(material, exchange, recipe)` - Now accepts optional recipe parameter
- **Smart Selection:** When no recipe specified, returns data for lowest-cost recipe
- **Response Enhancement:** Added `recipe` field to returned data object

### 📊 Data Pipeline (generate_report_tabs.py)
- **Added Column:** `Recipe` (column C) to "Price Analyser Data" sheet
- **Column Order Updated:** 
  - Old: LookupKey, Ticker, Material Name, Exchange, Ask_Price...
  - New: LookupKey, Ticker, **Recipe**, Material Name, Exchange, Ask_Price...
- **Data Handling:** Recipe column filled with 'N/A' for missing values

## Files Modified

1. **AppsScript_Index.html**
   - Added recipe dropdown HTML structure
   - Updated CSS grid from 2 to 3 columns
   - Added `loadRecipes()` JavaScript function
   - Updated `calculate()` to pass recipe parameter

2. **AppsScript_PriceAnalyser.js**
   - Added `getRecipesForMaterial()` function (47 lines)
   - Modified `getCalculationData()` to support recipe selection
   - Implemented lowest-cost recipe auto-selection logic

3. **generate_report_tabs.py**
   - Added 'Recipe' to reference_df column list (line ~2461)
   - Added Recipe NaN filling logic (line ~2475)
   - Updated column documentation comments

## Testing Checklist

- [ ] Run pipeline: `python pu-tracker\historical_data\main.py`
- [ ] Verify "Price Analyser Data" sheet has Recipe column (column C)
- [ ] Update Apps Script code (Extensions → Apps Script)
- [ ] Update Index.html in Apps Script
- [ ] Redeploy web app (Deploy → Manage deployments → Edit)
- [ ] Test with multi-recipe material (e.g., PE, DW, AAR)
- [ ] Verify recipe dropdown populates
- [ ] Test "All Recipes" default selection
- [ ] Test specific recipe selection
- [ ] Verify cost data accuracy

## Key Features

### 🎯 Automatic Best Recipe Selection
When users don't specify a recipe, the system automatically finds and displays the lowest-cost recipe:
```javascript
// Calculates: Input Cost Ask + Workforce Cost Ask
// Returns: Row with minimum total cost
```

### 📋 Recipe Display Format
Recipes shown with building prefix for clarity:
```
BMP:1xC-2xH=>200xPE (BMP)
PPF:100xC=>200xPE (PPF)
```

### 🔍 Smart Filtering
- Material selection → Triggers recipe loading
- Recipe selection → Updates cost display
- Empty recipe → Auto-selects best cost

## Example Usage

### Scenario: Polyethylene (PE) Production

**Step 1:** Select Material = "PE"
- Recipe dropdown populates with:
  - "-- All Recipes (Best Cost) --"
  - "BMP:1xC-2xH=>200xPE (BMP)"
  - "PPF:100xC=>200xPE (PPF)"

**Step 2:** Select Recipe = "All Recipes" (default)
- System calculates costs for both recipes
- Automatically displays BMP data (lower cost)

**Step 3:** Select Exchange = "CI1"
- Shows: Input Cost, Workforce Cost, Total Cost, Profitability

**Result:**
- Users see **actual costs** for BMP recipe specifically
- No averaging across different production methods
- Accurate ROI calculations

## Benefits

✅ **Accurate Costing:** No more averaged costs across recipes  
✅ **Recipe Comparison:** See which production method is most profitable  
✅ **Smart Defaults:** Auto-selects best option for quick decisions  
✅ **Strategic Planning:** Evaluate tech tree investments  
✅ **Market Adaptation:** Compare recipes under different market conditions

## Data Flow

```
processed_data.csv (Recipe column)
         ↓
generate_report_tabs.py (Extract Recipe)
         ↓
"Price Analyser Data" sheet (Column C)
         ↓
getRecipesForMaterial() (List unique recipes)
         ↓
Recipe Dropdown (User selects)
         ↓
getCalculationData() (Filter by recipe)
         ↓
Display Results (Recipe-specific costs)
```

## Deployment Commands

```powershell
# 1. Navigate to project directory
cd e:\Github\PrUn_Tracker\PrUn-Tracker

# 2. Run pipeline to regenerate data with Recipe column
cd pu-tracker\historical_data
python main.py

# 3. Wait for completion (~5 minutes)
# 4. Update Google Apps Script manually (see MULTI_RECIPE_SELECTOR.md)
```

## Technical Notes

### Recipe Column Requirements
- **Source:** `processed_data.csv` must have 'Recipe' column
- **Format:** "BUILDING:inputs=>outputs" (e.g., "BMP:1xC-2xH=>200xPE")
- **Missing Data:** Filled with 'N/A' string
- **Position:** Column C in "Price Analyser Data" sheet

### Cost Comparison Logic
```javascript
// Find lowest cost recipe
for each row where (Ticker === material && Exchange === exchange) {
  totalCost = inputCostAsk + workforceCostAsk
  if (totalCost < lowestCost) {
    lowestCost = totalCost
    bestRow = row
  }
}
return bestRow
```

### Backward Compatibility
- Old calls: `getCalculationData(material, exchange)` still work
- Empty recipe parameter → triggers auto-selection
- No breaking changes to existing functionality

---

**Status:** ✅ Implementation Complete  
**Next Step:** Deploy and test with live data
