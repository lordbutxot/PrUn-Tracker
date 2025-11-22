# Farming Fertility Feature - Implementation Summary

## Overview
This implementation adds planet fertility support to the Price Analyser, allowing farming buildings (FRM, ORC, VIN) to benefit from planet-specific calculations similar to how extraction buildings (COL, EXT, RIG) use planet concentration.

## Architecture

### Modular Design Principles
1. **Separate Data Fetching**: `fetch_planet_fertility.py` - standalone module for FIO API interaction
2. **Separate Upload Logic**: `upload_planet_fertility.py` - handles Google Sheets upload independently
3. **Pipeline Integration**: Added to `catch_data.py` and `main.py` with graceful fallbacks
4. **Frontend Separation**: Fertility and concentration logic kept parallel but distinct

## Files Modified

### Backend (Python)
1. **`pu-tracker/historical_data/fetch_planet_fertility.py`** (NEW)
   - Fetches fertility data from FIO API `/csv/planets` endpoint
   - Saves to `cache/planet_fertility.csv` (Planet, Fertility columns)
   - Handles API timeouts gracefully
   - Creates empty file with defaults if endpoint unavailable

2. **`pu-tracker/historical_data/upload_planet_fertility.py`** (NEW)
   - Uploads fertility data to Google Sheets "Planet Fertility" tab
   - Uses existing SheetsManager infrastructure
   - Includes detailed logging via DualLogger

3. **`pu-tracker/historical_data/catch_data.py`** (MODIFIED)
   - Added `fetch_planet_fertility()` function
   - Integrated into data collection pipeline (Step 8b)
   - Non-blocking: warns if fetch fails but continues pipeline

4. **`pu-tracker/historical_data/main.py`** (MODIFIED)
   - Added upload step for planet fertility (Step 8b)
   - Warns if upload fails but doesn't stop pipeline
   - Tracks timing for fertility upload

### Frontend (Google Apps Script)
5. **`AppsScript_PriceAnalyser.js`** (MODIFIED)
   - `getAllData()` now loads "Planet Fertility" sheet
   - Returns `fertility` array with planet name and fertility factor
   - Graceful handling if sheet doesn't exist (empty array)

6. **`AppsScript_Index.html`** (MODIFIED)
   - Added `fertilityData` global variable
   - Added `getPlanetFertilityClientSide(planetName)` helper
   - Added `loadPlanetsForFarming()` to populate planet dropdown sorted by fertility
   - Modified `checkExtractionRecipe()` to detect farming recipes (FRM:/ORC:/VIN:)
   - Updated planet selector label/hint dynamically:
     - "🌍 Select Planet (Extraction)" with "concentration" hint
     - "🌾 Select Planet (Farming)" with "fertility" hint
   - Applied fertility factor to workforce costs in main calculation
   - Applied fertility factor to exchange comparison calculations

## How It Works

### Data Flow
```
FIO API (/csv/planets)
  ↓
fetch_planet_fertility.py
  ↓
cache/planet_fertility.csv (Planet, Fertility)
  ↓
upload_planet_fertility.py
  ↓
Google Sheets "Planet Fertility" tab
  ↓
AppsScript_PriceAnalyser.js getAllData()
  ↓
AppsScript_Index.html (fertilityData global)
  ↓
User selects farming recipe (FRM:/ORC:/VIN:)
  ↓
Planet selector shows fertility percentages
  ↓
Workforce costs adjusted by fertility factor
```

### Calculation Logic

**Farming Time Adjustment:**
```javascript
const baseFarmingHours = 24;  // Base production time
const fertility = getPlanetFertilityClientSide(planet);  // e.g. 0.8
const adjustedHours = Math.max(6, Math.min(240, baseFarmingHours / fertility));
// Example: 24 / 0.8 = 30 hours (slower on low fertility planet)

const timeFactor = adjustedHours / baseFarmingHours;  // 30 / 24 = 1.25
workforceCostAsk *= timeFactor;  // Increase workforce costs by 25%
```

**Same logic applied to:**
- Main profit calculation (`calculate()`)
- Exchange comparison (`getExchangeComparisonFromCache()`)

### UI Behavior

**Recipe Detection:**
- Extraction: `recipe.startsWith('COL=>') || 'EXT=>' || 'RIG=>'`
- Farming: `recipe.startsWith('FRM:') || 'ORC:' || 'VIN:')`

**Planet Selector:**
- Hidden for manufacturing recipes
- Shows "Extraction" mode for COL/EXT/RIG with concentration %
- Shows "Farming" mode for FRM/ORC/VIN with fertility %
- Sorted descending (best planets first)
- Option: "-- Average (All Planets) --" uses base time (default)

## Fallback Behavior

### If FIO API Unavailable
- `fetch_planet_fertility.py` creates empty `planet_fertility.csv`
- Logs warning: "Created empty fertility file - farming calculations will use default (1.0)"
- Pipeline continues without errors

### If Sheet Not Created
- `getAllData()` returns empty `fertility: []` array
- `getPlanetFertilityClientSide()` returns `1.0` (no adjustment)
- Planet selector shows: "-- No Fertility Data --"

### If User Doesn't Select Planet
- Farming calculations use base 24-hour time
- Same as "average" planet scenario
- Workforce costs remain at base values

## Testing Steps

1. **Backend Testing:**
   ```powershell
   cd e:\Github\PrUn_Tracker\PrUn-Tracker\pu-tracker\historical_data
   python fetch_planet_fertility.py
   # Check cache/planet_fertility.csv created
   python upload_planet_fertility.py
   # Verify "Planet Fertility" sheet in Google Sheets
   ```

2. **Full Pipeline:**
   ```powershell
   cd e:\Github\PrUn_Tracker\PrUn-Tracker\pu-tracker
   .\run_pipeline.bat
   # Check logs for "Planet Fertility" upload step
   ```

3. **Frontend Testing:**
   - Open Price Analyser
   - Select material with farming recipe (GRN, BEA, NUT, etc.)
   - Select farming recipe (FRM:1xH2O=>4xGRN)
   - Verify planet selector appears with "🌾 Select Planet (Farming):"
   - Select high fertility planet → workforce costs should decrease
   - Select low fertility planet → workforce costs should increase
   - Check exchange comparison shows adjusted costs
   - Verify arbitrage opportunities reflect fertility adjustments

4. **Extraction Still Works:**
   - Select material with extraction (FE, O, H2O, etc.)
   - Select extraction recipe (COL=>1xFE, EXT=>1xO, etc.)
   - Verify planet selector shows "🌍 Select Planet (Extraction):"
   - Concentration-based calculations should work as before

## Data Structure

**planet_fertility.csv:**
```csv
Planet,Fertility
Montem,1.2
Vallis,0.8
...
```

**Google Sheets "Planet Fertility" tab:**
| Planet | Fertility |
|--------|-----------|
| Montem | 1.2       |
| Vallis | 0.8       |

## Key Features

✅ **Modular**: Each component is independent and can be maintained separately
✅ **Graceful Degradation**: System works even if fertility data unavailable
✅ **Consistent UX**: Farming follows same pattern as extraction
✅ **Non-Breaking**: Existing extraction functionality unchanged
✅ **Performance**: Fertility data cached client-side (no repeated server calls)
✅ **Logging**: Full visibility into fetch/upload process via DualLogger
✅ **Future-Proof**: Easy to extend for other planet-specific attributes

## Future Enhancements

- Add planet selector for other production types if FIO adds planet attributes
- Cache fertility data in browser localStorage for faster page loads
- Add planet comparison table showing fertility vs concentration side-by-side
- Integrate farming profitability into arbitrage calculations
- Add fertility heatmap visualization

## Troubleshooting

**"No Fertility Data" in planet selector:**
- Check if `cache/planet_fertility.csv` exists and has data
- Run `python fetch_planet_fertility.py` manually
- Check if "Planet Fertility" sheet exists in Google Sheets
- Verify FIO API is accessible: `Invoke-RestMethod https://rest.fnar.net/csv/planets`

**Workforce costs not adjusting:**
- Verify planet is selected (not "-- Average --")
- Check browser console for JavaScript errors
- Ensure `fertilityData` array is populated in console: `console.log(fertilityData)`
- Verify recipe detection: Recipe string should start with "FRM:", "ORC:", or "VIN:"

**Pipeline warnings:**
- "Planet fertility upload failed" → Check Google Sheets permissions
- "Could not fetch fertility data" → FIO API timeout, will retry next run
- "Fertility column not found" → FIO API structure changed, update parser

## Dependencies

- Python: `requests`, `pandas`, `pathlib`
- Google Apps Script: SpreadsheetApp, Logger
- Frontend: JavaScript ES6+, DOM manipulation
- External: FIO REST API (`https://rest.fnar.net`)

## Deployment Checklist

- [x] Create `fetch_planet_fertility.py`
- [x] Create `upload_planet_fertility.py`
- [x] Update `catch_data.py` with fetch call
- [x] Update `main.py` with upload step
- [x] Update `AppsScript_PriceAnalyser.js` to load fertility
- [x] Update `AppsScript_Index.html` with farming logic
- [ ] Run full pipeline: `.\run_pipeline.bat`
- [ ] Verify "Planet Fertility" sheet created
- [ ] Deploy updated Apps Script
- [ ] Test farming recipe selection
- [ ] Test planet selector for farming
- [ ] Verify workforce cost adjustments
- [ ] Test exchange comparison with farming
- [ ] Document in README.md

## Code Reuse

This implementation follows the project's existing patterns:

1. **Data Fetching**: Same structure as `fetch_planetresources_csv()`
2. **Upload Scripts**: Same pattern as `upload_planet_resources.py`
3. **Pipeline Integration**: Same approach as planet resources (Step 8/8b)
4. **Frontend Caching**: Same `allData` pattern used for fertility
5. **Error Handling**: Same try/except with logging strategy
6. **UI Components**: Reuses planet selector, just changes label/data source

**No new dependencies, no new architecture patterns, fully modular.**
