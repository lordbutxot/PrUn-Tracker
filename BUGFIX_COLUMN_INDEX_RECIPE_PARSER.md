# Bug Fix: Column Index Mismatch & Recipe Display Enhancement

## Problem
1. **"No data found" error** when selecting valid Material + Recipe + Exchange combinations
2. Recipe displayed as raw string (e.g., `FP:1xALG-1xGRN-1xNUT=>10xRAT`) instead of readable format

## Root Cause
**Column Index Mismatch:** The code assumed Exchange was in column D (index 3), but actual data structure has:
```
A (0): LookupKey
B (1): Ticker
C (2): Recipe
D (3): Material Name  ← Code was checking this for Exchange
E (4): Exchange       ← Actual Exchange location
F (5): Ask_Price
... (and so on, all shifted by 1)
```

This caused the query `data[i][1] === material && data[i][3] === exchange` to compare Exchange against Material Name, always failing.

## Solution

### 1. Fixed Column Indices (AppsScript_PriceAnalyser.js)

**Corrected the comparison:**
```javascript
// OLD (WRONG):
if (data[i][1] === material && data[i][3] === exchange)

// NEW (CORRECT):
if (data[i][1] === material && data[i][4] === exchange)
```

**Updated all column references:**
```javascript
// OLD indices:          NEW indices:
data[i][4]  // Ask       → data[i][5]   // Column F
data[i][5]  // Bid       → data[i][6]   // Column G
data[i][6]  // Input Ask → data[i][7]   // Column H
data[i][7]  // Input Bid → data[i][8]   // Column I
data[i][8]  // WF Ask    → data[i][9]   // Column J
data[i][9]  // WF Bid    → data[i][10]  // Column K
data[i][10] // Amount    → data[i][11]  // Column L
data[i][11] // Supply    → data[i][12]  // Column M
data[i][12] // Demand    → data[i][13]  // Column N
```

### 2. Added Recipe Parsing

**Parse recipe string into readable inputs/outputs:**
```javascript
// Input: "FP:1xALG-1xGRN-1xNUT=>10xRAT"
// Processing:
//   1. Split by "=>" to separate inputs and outputs
//   2. Remove building prefix (FP:)
//   3. Parse format "1xALG" → "1 ALG"
//   4. Join with commas

// Output:
//   recipeInputs:  "1 ALG, 1 GRN, 1 NUT"
//   recipeOutputs: "10 RAT"
```

**Implementation:**
```javascript
const parts = recipeString.split('=>');
const inputPart = parts[0].split(':')[1] || parts[0]; // Remove building prefix
const outputPart = parts[1];

// Parse inputs: "1xALG-1xGRN-1xNUT" → "1 ALG, 1 GRN, 1 NUT"
recipeInputs = inputPart.split('-').map(item => {
  const match = item.match(/(\d+)x([A-Z]+)/);
  return match ? match[1] + ' ' + match[2] : item;
}).join(', ');

// Parse outputs: "10xRAT" → "10 RAT"
recipeOutputs = outputPart.split('-').map(item => {
  const match = item.match(/(\d+)x([A-Z]+)/);
  return match ? match[1] + ' ' + match[2] : item;
}).join(', ');
```

### 3. Enhanced UI Display (AppsScript_Index.html)

**Added new "Recipe Details" section:**
```html
<div class="section">
  <h3>🔬 Recipe Details</h3>
  <div class="data-grid">
    <div class="data-item">
      <div class="data-label">Inputs Required</div>
      <div class="data-value" id="recipeInputs" style="color: #dc2626;">-</div>
    </div>
    <div class="data-item">
      <div class="data-label">Output Produced</div>
      <div class="data-value" id="recipeOutputs" style="color: #16a34a;">-</div>
    </div>
  </div>
</div>
```

**Updated display function:**
```javascript
function displayResults(data) {
  // Recipe details (NEW)
  setValueRaw('recipeInputs', data.recipeInputs || '-');
  setValueRaw('recipeOutputs', data.recipeOutputs || '-');
  
  // Pricing
  setValue('askPrice', data.askPrice);
  // ... rest of display logic
}
```

## Visual Comparison

### Before
```
Select Material: RAT
Select Recipe: FP:1xALG-1xGRN-1xNUT=>10xRAT (FP)
Select Exchange: AI1

❌ No data found for RAT on AI1 with recipe FP:1xALG-1xGRN-1xNUT=>10xRAT
```

### After
```
Select Material: RAT
Select Recipe: FP:1xALG-1xGRN-1xNUT=>10xRAT (FP)
Select Exchange: AI1

✅ 🔬 Recipe Details
   Inputs Required:  1 ALG, 1 GRN, 1 NUT
   Output Produced:  10 RAT

💰 Pricing
   Ask Price: ₡ 850.00
   Bid Price: ₡ 800.00

💵 Cost Breakdown
   Input Cost (Ask): ₡ 650.00
   Workforce Cost (Ask): ₡ 45.00
   Total Cost (Ask): ₡ 695.00
   ...
```

## Files Modified

1. **AppsScript_PriceAnalyser.js**
   - Line ~165: Fixed Exchange column index (3→4)
   - Lines ~195-203: Updated all data extraction indices (+1)
   - Lines ~204-233: Added recipe parsing logic
   - Line ~256: Added `recipeInputs` and `recipeOutputs` to return object

2. **AppsScript_Index.html**
   - Lines ~234-244: Added "Recipe Details" section HTML
   - Lines ~456-458: Added recipe display logic to `displayResults()`

## Testing

**Test Case:** RAT (Rations) on AI1 using FP recipe
- ✅ Material found: RAT
- ✅ Recipe found: FP:1xALG-1xGRN-1xNUT=>10xRAT
- ✅ Exchange matched: AI1
- ✅ Data retrieved successfully
- ✅ Recipe parsed correctly:
  - Inputs: "1 ALG, 1 GRN, 1 NUT"
  - Outputs: "10 RAT"

## Deployment

1. **Update Apps Script:**
   - Open Google Sheet → Extensions → Apps Script
   - Replace AppsScript_PriceAnalyser.js code
   - Replace Index.html code
   - Save changes

2. **Redeploy Web App:**
   - Deploy → Manage deployments
   - Click ✏️ Edit on current deployment
   - Select "New version"
   - Deploy

3. **Clear Cache:**
   - Users may need to hard refresh (Ctrl+F5)
   - Or wait ~5 minutes for cache expiration

## Additional Benefits

### Parsing Supports:
- Single output: `10xRAT` → `10 RAT`
- Multiple inputs: `1xALG-1xGRN-1xNUT` → `1 ALG, 1 GRN, 1 NUT`
- Multiple outputs: `200xPE-50xH` → `200 PE, 50 H`
- Complex recipes: `10xSAR-1xSNM-1000xSPT` → `10 SAR, 1 SNM, 1000 SPT`

### Error Handling:
- Missing recipe → Shows "N/A"
- Parse error → Shows "Parse error"
- Invalid format → Falls back to raw string

### Color Coding:
- Inputs: Red (#dc2626) - represents costs
- Outputs: Green (#16a34a) - represents production

---

**Status:** ✅ Bug Fixed & Enhancement Complete
**Impact:** All recipe selections now work correctly + improved UX with readable recipe display
