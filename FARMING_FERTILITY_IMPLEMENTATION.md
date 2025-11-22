# Farming & Fertility Implementation Guide

## Problem
Farming buildings (FRM, ORC, VIN) have production times affected by **planet fertility**, similar to how extraction (COL, EXT, RIG) is affected by resource concentration. Currently, the Price Analyser doesn't account for fertility variations.

## Solution Overview

### 1. Data Source
**Planet fertility data should come from one of these FIO endpoints:**
- `https://rest.fnar.net/csv/planets` - Contains planet-level attributes including fertility
- `https://rest.fnar.net/csv/planetdetail` - More detailed planet information

**Expected columns in planets CSV:**
```
PlanetNaturalId, PlanetName, Fertility, Temperature, Pressure, Gravity, ...
```

### 2. How Fertility Works
- **Base production time**: e.g., FRM takes 24 hours to produce GRN
- **Fertility factor**: Ranges from ~0.0 to ~1.5 (similar to resource concentration)
- **Actual production time** = Base time / Fertility factor
- **High fertility (e.g., 1.2)** = Faster production = Lower workforce costs
- **Low fertility (e.g., 0.3)** = Slower production = Higher workforce costs

### 3. Farming Buildings
- **FRM** (Farm): Produces GRN, BEA, NUT, RCO
- **ORC** (Orchard): Produces PIN, APP, GRP
- **VIN** (Vineyard): Produces WIN

### 4. Implementation Steps

#### Step 1: Fetch Planet Fertility Data
Create `fetch_planet_fertility.py`:
```python
import requests
import csv
from pathlib import Path

def fetch_planet_fertility():
    """Fetch planet fertility data from FIO API"""
    url = "https://rest.fnar.net/csv/planets"
    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    outfile = cache_dir / "planet_fertility.csv"
    
    try:
        print("[Fetch] Downloading planet fertility data...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse CSV and extract relevant fields
        lines = response.text.strip().split('\n')
        header = lines[0].split(',')
        
        # Find fertility column index
        fertility_idx = header.index('Fertility') if 'Fertility' in header else None
        planet_idx = header.index('PlanetNaturalId') if 'PlanetNaturalId' in header else 0
        
        if fertility_idx is None:
            print("[WARN] Fertility column not found in planets endpoint")
            return False
        
        # Write filtered data
        with open(outfile, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Planet', 'Fertility'])
            
            for line in lines[1:]:
                if line.strip():
                    fields = line.split(',')
                    planet = fields[planet_idx]
                    fertility = float(fields[fertility_idx]) if fertility_idx < len(fields) else 1.0
                    writer.writerow([planet, fertility])
        
        print(f"[SUCCESS] Saved planet_fertility.csv with {len(lines)-1} planets")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch fertility data: {e}")
        return False

if __name__ == "__main__":
    fetch_planet_fertility()
```

#### Step 2: Update catch_data.py
Add fertility fetching to the data collection pipeline:
```python
# In catch_data.py main() function, after fetch_planetresources_csv():

log_step("Fetching planet fertility data...")
try:
    import fetch_planet_fertility
    fetch_planet_fertility.fetch_planet_fertility()
    print("[SUCCESS] Planet fertility data fetched")
except Exception as e:
    print(f"[WARN] Could not fetch fertility data: {e}")
```

#### Step 3: Update AppsScript to Include Fertility
In `AppsScript_PriceAnalyser.js`, add fertility data loading:
```javascript
function getAllData() {
  try {
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    
    // ... existing code ...
    
    // Load planet fertility
    let fertilityData = [];
    try {
      const fertilitySheet = ss.getSheetByName('Planet Fertility');
      if (fertilitySheet) {
        const fertilityRows = fertilitySheet.getDataRange().getValues();
        for (let i = 1; i < fertilityRows.length; i++) {
          const [planet, fertility] = fertilityRows[i];
          if (planet && fertility) {
            fertilityData.push({
              planet: planet,
              fertility: parseFloat(fertility) || 1.0
            });
          }
        }
      }
    } catch (e) {
      Logger.log('Fertility data not available: ' + e);
    }
    
    return {
      data: processedData,
      bids: bidsData,
      planets: planetData,
      fertility: fertilityData  // NEW
    };
  } catch (error) {
    return { error: error.toString() };
  }
}
```

#### Step 4: Update Frontend (AppsScript_Index.html)
```javascript
// Global data cache
let allData = [];
let allBids = [];
let planetData = [];
let fertilityData = [];  // NEW

function loadAllData() {
  google.script.run
    .withSuccessHandler(function(result) {
      if (result.error) {
        showError('Failed to load data: ' + result.error);
        return;
      }
      
      allData = result.data;
      allBids = result.bids || [];
      planetData = result.planets || [];
      fertilityData = result.fertility || [];  // NEW
      
      populateMaterials();
      populateExchanges();
    })
    .getAllData();
}

// Helper function to get planet fertility
function getPlanetFertilityClientSide(planetName) {
  if (!fertilityData || fertilityData.length === 0) return 1.0;
  
  const planetInfo = fertilityData.find(p => p.planet === planetName);
  return planetInfo ? planetInfo.fertility : 1.0;
}
```

#### Step 5: Apply Fertility to Farming Recipes
In `calculateFromCache()` function:
```javascript
// Check if this is a farming recipe
const recipeStr = bestRow.recipe || '';
const isFarming = recipeStr.startsWith('FRM:') || 
                  recipeStr.startsWith('ORC:') || 
                  recipeStr.startsWith('VIN:');

// Apply planet-specific farming time adjustment
if (isFarming && planet) {
  const fertility = getPlanetFertilityClientSide(planet);
  if (fertility > 0) {
    // Workforce costs in data are based on BASE farming time (24h typically)
    // Adjust for the specific planet's fertility
    const baseFarmingHours = 24;  // Default farming time
    const adjustedHours = Math.max(6, Math.min(240, baseFarmingHours / fertility));
    const timeFactor = adjustedHours / baseFarmingHours;
    
    // Adjust workforce costs based on planet-specific farming time
    workforceCostAsk *= timeFactor;
    workforceCostBid *= timeFactor;
  }
}
```

#### Step 6: Add Planet Selector for Farming
Update `checkExtractionRecipe()` to also show for farming:
```javascript
function checkExtractionRecipe() {
  const recipe = document.getElementById('recipeSelect').value;
  const planetGroup = document.getElementById('planetGroup');
  const planetSelect = document.getElementById('planetSelect');
  const planetLabel = planetGroup.querySelector('label');
  
  // Check if recipe is extraction OR farming
  const isExtraction = recipe && (recipe.startsWith('COL=>') || 
                                   recipe.startsWith('EXT=>') || 
                                   recipe.startsWith('RIG=>'));
  const isFarming = recipe && (recipe.startsWith('FRM:') ||
                                recipe.startsWith('ORC:') ||
                                recipe.startsWith('VIN:'));
  
  if (isExtraction) {
    planetLabel.textContent = '🌍 Select Planet (Extraction):';
    planetLabel.nextElementSibling.textContent = 
      'Planet concentration affects extraction time and workforce costs';
    planetGroup.style.display = 'block';
    loadPlanetsForExtraction(material);
  } else if (isFarming) {
    planetLabel.textContent = '🌾 Select Planet (Farming):';
    planetLabel.nextElementSibling.textContent = 
      'Planet fertility affects farming time and workforce costs';
    planetGroup.style.display = 'block';
    loadPlanetsForFarming();
  } else {
    planetGroup.style.display = 'none';
    planetSelect.innerHTML = '<option value="">-- Select Planet --</option>';
  }
}

function loadPlanetsForFarming() {
  const planetSelect = document.getElementById('planetSelect');
  
  if (!fertilityData || fertilityData.length === 0) {
    planetSelect.innerHTML = '<option value="">-- No Fertility Data --</option>';
    return;
  }
  
  // Sort planets by fertility descending (best first)
  const planets = [...fertilityData].sort((a, b) => b.fertility - a.fertility);
  
  planetSelect.innerHTML = '<option value="">-- Average (All Planets) --</option>';
  planets.forEach(function(planet) {
    const option = document.createElement('option');
    option.value = planet.planet;
    const fertilityPercent = (planet.fertility * 100).toFixed(1);
    option.textContent = planet.planet + ' (Fertility: ' + fertilityPercent + '%)';
    planetSelect.appendChild(option);
  });
}
```

### 5. Testing Plan
1. Verify `planet_fertility.csv` is fetched with correct data
2. Upload fertility data to Google Sheets (new tab: "Planet Fertility")
3. Select a farming recipe (e.g., FRM:1xH2O=>4xGRN)
4. Choose different planets with varying fertility
5. Verify workforce costs adjust correctly:
   - High fertility planet → Lower costs
   - Low fertility planet → Higher costs

### 6. Alternative: If Fertility Endpoint Unavailable
If the FIO API doesn't expose fertility directly:
1. **Hardcode typical fertility ranges** per planet type (Fertile, Barren, Rocky, etc.)
2. **Use community data** from PrUn wikis or databases
3. **Make it optional** - default to 100% fertility if not selected

## Expected Column Names
Based on PrUn API patterns, look for:
- `Fertility` or `FertilityFactor`
- `PlanetNaturalId` or `PlanetId` or `NaturalId`
- `PlanetName` or `Name`

## Notes
- Fertility works exactly like extraction concentration but for farming
- Base farming time is typically 24 hours
- Fertility ranges from 0-150% typically
- Some planets have NO fertility (can't farm there)
