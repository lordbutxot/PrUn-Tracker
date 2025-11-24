# Extraction Formula Fix

## Problem

Current implementation incorrectly calculates extraction mechanics:
- **Wrong**: Variable time, fixed output (100 units)
- **Correct**: Fixed time, variable output (based on concentration)

## Game Data Verification

### In-Game Test Results (100% efficiency, luxury consumables, no experts)

| Planet | Material | Concentration | Output | Time | Calculated Base |
|--------|----------|---------------|--------|------|-----------------|
| ZV-307d | SIO | 0.300 | 11 units | 12h 12m | 11/0.30 = 36.67 |
| AM-462c | SIO | 0.026 | 1 unit | 13h 9m | 1/0.026 = 38.46 |
| YP-888b | SIO | 0.769 | 27 units | 12h 2m | 27/0.769 = 35.11 |
| UV-795b | SIO | 0.500 | 18 units | 12h 20m | 18/0.500 = 36.00 |

**Average base multiplier: ~35-37**

### Formula Testing (using base = 35)

| Planet | Concentration | Formula (×35) | Expected | Actual | Match |
|--------|---------------|---------------|----------|--------|-------|
| ZV-307d | 0.300 | 0.300 × 35 = 10.5 | 11 | 11 | ✓ |
| AM-462c | 0.026 | 0.026 × 35 = 0.91 | 1 | 1 | ✓ |
| YP-888b | 0.769 | 0.769 × 35 = 26.9 | 27 | 27 | ✓ |
| UV-795b | 0.500 | 0.500 × 35 = 17.5 | 18 | 18 | ✓ |

## Correct Formula (Official from PCT)

### Step 1: Calculate Daily Extraction
```
Gaseous (COL): DailyExtraction = (RawConcentration × 100) × 0.6
Other (RIG/EXT): DailyExtraction = (RawConcentration × 100) × 0.7
```

### Step 2: Base Cycle Times
```
RIG: 4.8 hours (4h48m)
COL: 6 hours
EXT: 12 hours
```

### Step 3: Calculate Units Per Cycle (at 100% efficiency)
```
UnitsPerCycle = DailyExtraction / CyclesPerDay
CyclesPerDay = 24h / BaseCycleTime

Example for EXT: CyclesPerDay = 24 / 12 = 2 cycles/day
```

### Step 4: Round Up and Adjust Time
```
1. RoundedUnits = ceil(UnitsPerCycle)  // Round up to next integer
2. Remainder = RoundedUnits - UnitsPerCycle
3. AdjustedTime = BaseCycleTime + (BaseCycleTime × (Remainder / UnitsPerCycle))
```

### Step 5: Apply Efficiency Bonus
```
FinalTime = AdjustedTime / EfficiencyMultiplier
FinalOutput = RoundedUnits (doesn't change with efficiency)

Where EfficiencyMultiplier = 1.0 + (Worker + Planet + CoGC + Experts) bonuses
Then multiply by HQ bonuses
```

### Complete Formula
```javascript
function calculateExtraction(concentration, building, efficiency) {
  // Step 1: Daily extraction
  const multiplier = (building === 'COL') ? 0.6 : 0.7;
  const dailyExtraction = (concentration * 100) * multiplier;
  
  // Step 2: Base cycle time
  const baseCycleTime = (building === 'RIG') ? 4.8 : (building === 'COL') ? 6 : 12;
  
  // Step 3: Units per cycle
  const cyclesPerDay = 24 / baseCycleTime;
  const unitsPerCycle = dailyExtraction / cyclesPerDay;
  
  // Step 4: Round up and adjust time
  const roundedUnits = Math.ceil(unitsPerCycle);
  const remainder = roundedUnits - unitsPerCycle;
  const adjustedTime = baseCycleTime + (baseCycleTime * (remainder / unitsPerCycle));
  
  // Step 5: Apply efficiency
  const finalTime = adjustedTime / efficiency;
  
  return {
    output: roundedUnits,
    time: finalTime,  // in hours
    efficiency: efficiency
  };
}
```

## Current vs Correct Implementation

### Current (WRONG) ❌
```python
# Python (generate_extraction_recipes.py)
base_hours = 24  # Fixed
output = 100  # Fixed
adjusted_hours = base_hours / concentration  # Variable
```

```javascript
// JavaScript (AppsScript_PriceAnalyser.js)
const planetFactor = getPlanetFactor(material, planetName);
const baseHours = building === 'RIG' ? 48 : 24;
const adjustedHours = Math.max(6, Math.min(240, baseHours / planetFactor));
const timeFactor = adjustedHours / baseHours;
workforceCostAsk *= timeFactor;  // Adjust cost by time
```

### Correct (NEW) ✓
```python
# Python (generate_extraction_recipes.py)
base_hours = 12  # Fixed
output = floor(concentration × 35)  # Variable per planet
# No time adjustment needed in recipe generation
```

```javascript
// JavaScript (AppsScript_PriceAnalyser.js)
const planetFactor = getPlanetFactor(material, planetName);
const baseHours = 12;  // Fixed for all extraction buildings
const output = Math.floor(planetFactor * 35);  // Variable output
const amountPerRecipe = output;  // Use actual output amount
// Workforce costs stay at base 12h, modified only by efficiency bonuses
```

## Files to Update

### 1. Frontend (AppsScript_Index.html)
**Location**: Client-side calculation functions

**Changes**:
- Remove time adjustment based on planet factor
- Add output adjustment based on planet factor
- Update display to show actual output per cycle

### 2. Backend (AppsScript_PriceAnalyser.js)
**Location**: `getCalculationData()` function (lines ~850-900)

**Current code**:
```javascript
if (isExtraction && planetName) {
  const planetFactor = getPlanetFactor(material, planetName);
  if (planetFactor > 0) {
    const building = recipeStr.split('=>')[0];
    const baseHours = building === 'RIG' ? 48 : 24;
    const adjustedHours = Math.max(6, Math.min(240, baseHours / planetFactor));
    const timeFactor = adjustedHours / baseHours;
    workforceCostAsk *= timeFactor;
    workforceCostBid *= timeFactor;
  }
}
```

**New code**:
```javascript
if (isExtraction && planetName) {
  const planetFactor = getPlanetFactor(material, planetName);
  if (planetFactor > 0) {
    // Output varies with concentration, time is fixed at 12h base
    const actualOutput = Math.floor(planetFactor * 35);
    const baseOutput = 100; // Recipe assumes 100 units
    
    // Adjust all prices by output ratio (less output = higher per-unit cost)
    const outputRatio = actualOutput / baseOutput;
    
    askPrice = askPrice / outputRatio;
    bidPrice = bidPrice / outputRatio;
    inputCostAsk = inputCostAsk / outputRatio;
    inputCostBid = inputCostBid / outputRatio;
    workforceCostAsk = workforceCostAsk / outputRatio;
    workforceCostBid = workforceCostBid / outputRatio;
    
    // Update amount per recipe to show actual output
    amountPerRecipe = actualOutput;
  }
}
```

### 3. Python Pipeline (generate_extraction_recipes.py)
**Location**: Main generation function

**Changes**:
- Change base hours from 24/48 to 12 for all extraction buildings
- Keep output at 100 (base reference, adjusted per-planet in frontend)
- Document that actual output varies by planet concentration

**Current**:
```python
EXTRACTION_BUILDINGS = {
    'COL': {'workforce': 'PIONEER', 'capacity': 50, 'base_hours_per_100': 24},
    'EXT': {'workforce': 'PIONEER', 'capacity': 60, 'base_hours_per_100': 24},
    'RIG': {'workforce': 'PIONEER', 'capacity': 30, 'base_hours_per_100': 48}
}
```

**New**:
```python
EXTRACTION_BUILDINGS = {
    'COL': {'workforce': 'PIONEER', 'capacity': 50, 'base_hours': 12},
    'EXT': {'workforce': 'PIONEER', 'capacity': 60, 'base_hours': 12},
    'RIG': {'workforce': 'PIONEER', 'capacity': 30, 'base_hours': 12}
}
# Note: Output per cycle = floor(concentration × 35), calculated per-planet in frontend
# Base output of 100 in recipes is reference value only
```

### 4. Documentation Updates
- README.md: Update extraction formula description
- FEATURES.md: Correct extraction mechanics explanation
- CHANGELOG.md: Document this bug fix

## Testing Plan

1. **Verify formula with more materials**:
   - Test different resource types (FEO, CLI, LIO, TAI, etc.)
   - Test different building types (EXT, RIG, COL)
   - Confirm base multiplier is 35 across all materials

2. **Check edge cases**:
   - Very low concentration (< 0.03) → output = 1
   - Very high concentration (> 1.0) → output > 35
   - Different efficiency levels (experts, luxury, CoGC)

3. **Validate workforce costs**:
   - Ensure costs scale correctly with output
   - Lower output = higher per-unit cost
   - 12h base time for all extraction buildings

4. **Cross-reference with game data**:
   - Compare calculated profits with actual in-game values
   - Verify ROI calculations are accurate
   - Test planet selector shows correct comparisons

## Implementation Status

- [ ] Update generate_extraction_recipes.py (base time 24h→12h)
- [ ] Update AppsScript_PriceAnalyser.js (add output scaling logic)
- [ ] Update AppsScript_Index.html (remove time scaling, add output scaling)
- [ ] Update documentation (README, FEATURES, CHANGELOG)
- [ ] Test with multiple materials and planets
- [ ] Verify workforce cost calculations
- [ ] Deploy to production

## Notes

- This fix affects ALL extraction recipes (COL, EXT, RIG)
- Workforce costs must be adjusted by output ratio, not time factor
- Market prices remain the same (per-unit basis)
- Planet comparison will show correct profitability differences
- Building comparison for extraction will show accurate alternatives

