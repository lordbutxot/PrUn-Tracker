# Workforce Efficiency System

## Overview

Workforce efficiency in Prosperous Universe is based on **worker satisfaction**, which directly affects production time and consumable usage. The Price Analyser now accurately models this system.

## How It Works

### Worker Satisfaction

Workers have two types of needs:
- **Essential consumables**: Required for basic operations (DW, RAT, OVE, etc.)
- **Luxury consumables**: Optional items that boost satisfaction (COF, PWO, KOM, ALE, etc.)

Satisfaction is checked every 24 hours per consumable type:
- **100% satisfaction** = All needs met (essentials + luxuries)
- **~79% satisfaction** = Only essentials met (no luxuries) for Pioneers
- **Lower satisfaction** = Production halts if essentials reach zero

### Efficiency Impact

**Base efficiency = Worker satisfaction %**

- With luxury consumables: **100% efficiency** (base production time)
- Without luxury consumables: **~79% efficiency** (longer production time)

### Cost Calculation

Lower efficiency means:
1. **Longer production time** → More hours to produce same output
2. **Higher consumable usage** → More workforce needs consumed
3. **Higher costs** → Total cost increases

**Formula:**
```
Actual Cost = Base Cost × (1 / Efficiency)
```

**Example for Pioneers:**
- Base workforce cost: 100 ICA
- With luxury (100% efficiency): 100 ICA total
- Without luxury (79% efficiency): 100 × (1/0.79) = **126.6 ICA total** (+26.6% cost)

## Workforce Tier Efficiency Levels

### Confirmed Values
- **Pioneers (without luxury)**: ~79% efficiency
  - Essential only: DW (4/day/100), RAT (4), OVE (0.5)
  - Luxury adds: COF (0.5), PWO (0.2)
  - PWO alone: ~87% satisfaction
  - COF alone: ~91% satisfaction
  - Both together: 100% satisfaction

### Other Tiers (Estimated)
These values may vary by workforce tier:
- **Settlers**: TBD (likely similar ~75-80% range)
- **Technicians**: TBD
- **Engineers**: TBD
- **Scientists**: TBD

> **Note**: Currently, the Price Analyser uses 79% efficiency for all workforce tiers when luxury is disabled. This is based on Pioneer data and provides a reasonable approximation.

## Expert Bonuses (Not Yet Implemented)

Expert bonuses are a **separate multiplicative system** applied on top of base efficiency:
- Up to 5 experts per industry
- Bonuses accumulate: +3.06% (1st), +6.96% (2nd), up to +28.40% (5th)
- Formula: `Final Efficiency = Base Efficiency × (100% + Expert Bonus %)`

**Future Enhancement**: Expert bonuses could be added as an additional toggle/input.

## Price Analyser Implementation

### UI Toggle
- **Checkbox**: "Provide Luxury Consumables (100% Workforce Efficiency)"
- **Checked** (default): Workers get all needs → 100% efficiency → base costs
- **Unchecked**: Workers get only essentials → 79% efficiency → higher costs (~26.6% increase)

### Code Implementation

**Frontend (AppsScript_Index.html):**
```javascript
// Apply efficiency penalty if no luxury (79% efficiency = 1/0.79 = ~1.266x cost)
if (!includeLuxury) {
  workforceCostAsk *= (1 / 0.79);
  workforceCostBid *= (1 / 0.79);
}
```

**Backend (AppsScript_PriceAnalyser.js):**
```javascript
// Apply efficiency penalty if no luxury (79% efficiency = 1/0.79 = ~1.266x cost)
if (!includeLuxury) {
  workforceCostAsk *= (1 / 0.79);
}
```

### Previous Implementation (Incorrect)

The old system used a simple 0.7 multiplier:
```javascript
// OLD (WRONG): Reduced cost by 30%
if (!includeLuxury) workforceCostAsk *= 0.7;
```

This was backwards - it made excluding luxury consumables **cheaper**, when it should be **more expensive** due to reduced efficiency.

## Data Sources

### Essential Consumables per Workforce Tier
From `workforceneeds.json`:
- Categorized by MaterialName containing "Luxury" or "luxury"
- **Necessary** = Essential consumables (DW, RAT, OVE, EXO, etc.)
- **Luxury** = Optional consumables (PWO, COF, KOM, ALE, WIN, etc.)

### Production Times
From `buildingrecipes.csv`:
- **Duration** column = Production time in seconds
- Used to calculate total consumable usage per recipe

## Testing Recommendations

1. **Compare costs with/without luxury**:
   - Select a material (e.g., RAT - Rations)
   - Check workforce cost with luxury enabled (base cost)
   - Uncheck luxury option
   - Workforce cost should increase by ~26.6%

2. **Verify material profitability changes**:
   - High workforce cost materials (e.g., complex electronics)
   - Should show significantly reduced profit without luxury
   - May flip from profitable to unprofitable

3. **Recipe comparison**:
   - Materials with multiple recipes
   - Best recipe may change based on luxury toggle
   - Recipe with lower workforce cost becomes more attractive without luxury

## Future Enhancements

1. **Tier-specific efficiency values**:
   - Research actual efficiency for Settlers, Technicians, etc.
   - Implement lookup table: `EFFICIENCY_WITHOUT_LUXURY[workforce_tier]`

2. **Expert bonus system**:
   - Add expert count input (0-5 per industry)
   - Calculate cumulative bonus percentage
   - Apply multiplicatively: `cost / (efficiency * expertBonus)`

3. **Partial luxury fulfillment**:
   - Model scenarios with some but not all luxury items
   - E.g., PWO only = 87% efficiency, COF only = 91%

4. **Building-specific workforce tiers**:
   - Parse building code from recipe
   - Look up workforce tier from `workforces.csv`
   - Apply correct efficiency multiplier per tier

## References

- Game Documentation: Worker Satisfaction System
- FIO (fio.fnar.net): Community tools and calculators
- FnarAPI: `workforceneeds.json` endpoint for consumable data
- Community Research: Efficiency percentages per tier

---

**Last Updated**: November 20, 2025  
**Implementation Version**: v2.0 (Efficiency-based system)
