# Multi-Recipe Selector - Visual Guide

## 🎯 User Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    PRICE ANALYSER                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Material   │  │    Recipe    │  │   Exchange   │      │
│  │   [▼ PE  ]   │  │ [▼ Select  ] │  │  [▼ CI1  ]   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
        ↓                    ↓                    ↓
    Select PE          Loads recipes         Select CI1
                            ↓
                    ┌──────────────┐
                    │ All Recipes  │ ← Default (best cost)
                    │ BMP:...      │
                    │ PPF:...      │
                    └──────────────┘
                            ↓
                    ┌──────────────────────────────────┐
                    │     Cost Breakdown (BMP)         │
                    │  Input Cost:      $1,000         │
                    │  Workforce Cost:    $100         │
                    │  Total Cost:      $1,100         │
                    │  Sell Price:      $1,500         │
                    │  Profit:            $400         │
                    │  ROI:              36.4%         │
                    └──────────────────────────────────┘
```

## 🔄 Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   PYTHON PIPELINE                             │
│                                                               │
│  processed_data.csv                                           │
│  ├─ Ticker: "PE"                                              │
│  ├─ Recipe: "BMP:1xC-2xH=>200xPE"                             │
│  ├─ Building: "BMP"                                           │
│  ├─ Input Cost Ask: 1000                                      │
│  ├─ Workforce Cost Ask: 100                                   │
│  └─ Exchange: "CI1"                                           │
│                                                               │
└───────────────────────────┬───────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────────┐
        │   generate_report_tabs.py             │
        │   create_price_analyser_tab()         │
        │                                       │
        │   reference_df = [                    │
        │     'LookupKey',  ← "PECI1"           │
        │     'Ticker',     ← "PE"              │
        │     'Recipe',     ← "BMP:1xC-2xH..." │
        │     'Material Name',                  │
        │     'Exchange',                       │
        │     'Ask_Price',                      │
        │     'Bid_Price',                      │
        │     'Input Cost Ask',                 │
        │     'Workforce Cost Ask',             │
        │     ...                               │
        │   ]                                   │
        └───────────────┬───────────────────────┘
                        ↓
        ┌───────────────────────────────────────┐
        │    GOOGLE SHEETS                      │
        │    "Price Analyser Data"              │
        │                                       │
        │    A         B      C                 │
        │  ┌─────────┬──────┬──────────────┐    │
        │  │LookupKey│Ticker│Recipe        │... │
        │  ├─────────┼──────┼──────────────┤    │
        │  │PECI1    │PE    │BMP:1xC-2x... │    │
        │  │PECI1    │PE    │PPF:100xC=... │    │
        │  │AARCI1   │AAR   │BMP:1xFEO=... │    │
        │  └─────────┴──────┴──────────────┘    │
        └───────────────┬───────────────────────┘
                        ↓
        ┌───────────────────────────────────────┐
        │    GOOGLE APPS SCRIPT                 │
        │    AppsScript_PriceAnalyser.js        │
        │                                       │
        │  function getRecipesForMaterial(mat)  │
        │    → Query column B (Ticker)          │
        │    → Extract unique column C (Recipe) │
        │    → Return [{key, label, building}]  │
        │                                       │
        │  function getCalculationData(m,e,r)   │
        │    → Filter: Ticker=m, Exchange=e     │
        │    → If recipe: Match column C        │
        │    → If no recipe: Find min cost      │
        │    → Return cost/profit data          │
        └───────────────┬───────────────────────┘
                        ↓
        ┌───────────────────────────────────────┐
        │    WEB INTERFACE                      │
        │    AppsScript_Index.html              │
        │                                       │
        │  1. User selects material             │
        │  2. loadRecipes() called              │
        │  3. Recipe dropdown populates         │
        │  4. User selects recipe (or default)  │
        │  5. calculate() called                │
        │  6. displayResults() shows data       │
        └───────────────────────────────────────┘
```

## 📊 Recipe Selection Logic

### Scenario 1: User Selects Specific Recipe
```
Input:
  material = "PE"
  recipe = "BMP:1xC-2xH=>200xPE"
  exchange = "CI1"

Query:
  Find row where:
    Ticker === "PE" AND
    Recipe === "BMP:1xC-2xH=>200xPE" AND
    Exchange === "CI1"

Output:
  Exact match data for BMP recipe
```

### Scenario 2: User Selects "All Recipes" (Default)
```
Input:
  material = "PE"
  recipe = "" (empty)
  exchange = "CI1"

Query:
  Find all rows where:
    Ticker === "PE" AND
    Exchange === "CI1"

Processing:
  Row 1 (BMP): totalCost = 1000 + 100 = 1100
  Row 2 (PPF): totalCost = 1200 + 80  = 1280
  
  Select: Row 1 (lowest cost)

Output:
  BMP recipe data (automatically selected)
```

## 🏗️ Column Structure

### "Price Analyser Data" Sheet Layout
```
 A          B       C                        D              E         F
┌──────────┬───────┬────────────────────────┬──────────────┬─────────┬─────────┐
│LookupKey │Ticker │Recipe                  │Material Name │Exchange │Ask_Price│
├──────────┼───────┼────────────────────────┼──────────────┼─────────┼─────────┤
│PECI1     │PE     │BMP:1xC-2xH=>200xPE     │Polyethylene  │CI1      │1500     │
│PECI1     │PE     │PPF:100xC=>200xPE       │Polyethylene  │CI1      │1500     │
│AARCI1    │AAR   │BMP:1xFEO=>1xAAR        │AAR           │CI1      │850      │
└──────────┴───────┴────────────────────────┴──────────────┴─────────┴─────────┘

 G              H              I                  J
┬───────────────┬──────────────┬──────────────────┬──────────────────┐
│Input Cost Ask │Input Cost Bid│Workforce Cost Ask│Workforce Cost Bid│...
┼───────────────┼──────────────┼──────────────────┼──────────────────┤
│1000           │950           │100               │100               │
│1200           │1150          │80                │80                │
│800            │750           │50                │50                │
┴───────────────┴──────────────┴──────────────────┴──────────────────┘
```

## 🎨 UI Component Interaction

### HTML Structure
```html
<div class="controls">
  <!-- Column 1: Material -->
  <div class="control-group">
    <label for="materialSelect">Select Material:</label>
    <select id="materialSelect">
      <option value="">Loading materials...</option>
      <option value="PE">PE - Polyethylene</option>
      <option value="AAR">AAR - Aggregate Assembly Robot</option>
      ...
    </select>
  </div>
  
  <!-- Column 2: Recipe (NEW!) -->
  <div class="control-group">
    <label for="recipeSelect">Select Recipe:</label>
    <select id="recipeSelect">
      <option value="">-- Select Material First --</option>
    </select>
  </div>
  
  <!-- Column 3: Exchange -->
  <div class="control-group">
    <label for="exchangeSelect">Select Exchange:</label>
    <select id="exchangeSelect">
      <option value="">Loading exchanges...</option>
      <option value="CI1">CI1</option>
      <option value="AI1">AI1</option>
      ...
    </select>
  </div>
</div>
```

### JavaScript Event Flow
```javascript
// Event 1: User selects material
materialSelect.addEventListener('change', function() {
  loadRecipes();  // Populate recipe dropdown
  calculate();    // Update display
});

// Event 2: Recipe dropdown populates
function loadRecipes() {
  const material = materialSelect.value;
  
  google.script.run
    .withSuccessHandler(function(recipes) {
      // recipes = [
      //   {key: "BMP:...", label: "BMP:...", building: "BMP"},
      //   {key: "PPF:...", label: "PPF:...", building: "PPF"}
      // ]
      
      recipeSelect.innerHTML = 
        '<option value="">-- All Recipes (Best Cost) --</option>';
      
      recipes.forEach(function(recipe) {
        const option = document.createElement('option');
        option.value = recipe.key;
        option.textContent = recipe.label + ' (' + recipe.building + ')';
        recipeSelect.appendChild(option);
      });
    })
    .getRecipesForMaterial(material);
}

// Event 3: User selects recipe
recipeSelect.addEventListener('change', calculate);

// Event 4: Calculate and display
function calculate() {
  const material = materialSelect.value;
  const recipe = recipeSelect.value;  // Empty = auto-select best
  const exchange = exchangeSelect.value;
  
  google.script.run
    .withSuccessHandler(displayResults)
    .getCalculationData(material, exchange, recipe);
}
```

## 🔍 Recipe Comparison Example

### Material: Polyethylene (PE) on CI1

#### Option A: BMP Recipe
```
Recipe: BMP:1xC-2xH=>200xPE
Inputs: 1 Carbon + 2 Hydrogen
Building: Basic Material Plant

Costs:
  Carbon (1):      $500
  Hydrogen (2):    $500
  Input Total:     $1,000
  Workforce:       $100
  ═════════════════════════
  Total Cost:      $1,100

Market:
  Ask Price:       $1,500
  Bid Price:       $1,400

Profit (Ask-Ask): $1,500 - $1,100 = $400
ROI (Ask-Ask):    ($400 / $1,100) × 100 = 36.4%
```

#### Option B: PPF Recipe
```
Recipe: PPF:100xC=>200xPE
Inputs: 100 Carbon
Building: Polymer Processing Facility

Costs:
  Carbon (100):    $1,200
  Input Total:     $1,200
  Workforce:       $80
  ═════════════════════════
  Total Cost:      $1,280

Market:
  Ask Price:       $1,500
  Bid Price:       $1,400

Profit (Ask-Ask): $1,500 - $1,280 = $220
ROI (Ask-Ask):    ($220 / $1,280) × 100 = 17.2%
```

#### Decision
**Winner: BMP Recipe**
- Lower total cost ($1,100 vs $1,280)
- Higher profit ($400 vs $220)
- Better ROI (36.4% vs 17.2%)

**Automatically selected when "All Recipes" chosen!**

## 🚀 Deployment Workflow

```
1. Update Python Code
   ├─ generate_report_tabs.py (add Recipe column)
   └─ Run: python main.py

2. Verify Data
   ├─ Check processed_data.csv has Recipe column
   └─ Verify "Price Analyser Data" sheet structure

3. Update Apps Script
   ├─ Open Google Sheet → Extensions → Apps Script
   ├─ Replace AppsScript_PriceAnalyser.js code
   └─ Replace Index.html code

4. Redeploy Web App
   ├─ Deploy → Manage deployments
   ├─ Click ✏️ Edit
   └─ Save as new version

5. Test
   ├─ Open web app URL
   ├─ Select material with multiple recipes
   ├─ Verify recipe dropdown works
   └─ Compare "All Recipes" vs specific selection
```

## 📈 Benefits Summary

| Feature | Before | After |
|---------|--------|-------|
| Recipe Selection | ❌ Not available | ✅ Full control |
| Cost Accuracy | ⚠️ Averaged | ✅ Recipe-specific |
| Comparison | ❌ Manual | ✅ Automatic |
| Best Recipe | 🤔 Unknown | ✅ Auto-selected |
| User Experience | 2 dropdowns | 3 dropdowns |
| Data Columns | 12 columns | 13 columns (+Recipe) |

---

*This visual guide complements MULTI_RECIPE_SELECTOR.md*
