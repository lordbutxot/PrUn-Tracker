# Custom Workforce Efficiency Feature

## Overview
Added manual workforce efficiency override to the Price Analyser, allowing users to input custom efficiency percentages instead of using the default 79% for non-luxury consumables.

## UI Changes

### New Option: "⚙️ Use Custom Workforce Efficiency"
- **Location**: Between "Luxury Consumables" and "Self-Production Costs" options
- **Behavior**: 
  - When checked, reveals an input field for efficiency percentage (1-100%)
  - Default value: 79%
  - Automatically unchecks "Luxury Consumables" option
  - Mutual exclusivity: Checking "Luxury Consumables" disables custom efficiency

### Input Field
- **Type**: Number input (1-100%)
- **Default**: 79%
- **Step**: 1%
- **Validation**: Min 1%, Max 100%
- **Visibility**: Hidden until custom efficiency toggle is checked

## Calculation Logic

### Efficiency Multiplier Formula
```javascript
// Convert efficiency percentage to cost multiplier
const efficiencyMultiplier = 100 / customEfficiency;
workforceCostAsk *= efficiencyMultiplier;
```

### Examples
- **79% efficiency** (default): `100 / 79 = 1.266x` workforce costs
- **85% efficiency**: `100 / 85 = 1.176x` workforce costs
- **100% efficiency**: `100 / 100 = 1.0x` workforce costs (same as luxury)
- **50% efficiency**: `100 / 50 = 2.0x` workforce costs (very poor conditions)

### Priority Order
1. **Custom Efficiency** (if enabled) → Use user-provided percentage
2. **Luxury Consumables** (if checked) → 100% efficiency (1.0x multiplier)
3. **Default** → 79% efficiency (1.266x multiplier)

## Implementation Details

### Functions Modified
1. **`calculate()`** - Captures custom efficiency state and passes to calculations
2. **`calculateFromCache()`** - Applies custom efficiency to workforce costs
3. **`getExchangeComparisonFromCache()`** - Applies custom efficiency to exchange comparison
4. **`getRecommendationFromCache()`** - Applies custom efficiency to recipe recommendations

### Event Listeners Added
```javascript
// Toggle custom efficiency group visibility
document.getElementById('customEfficiencyToggle').addEventListener('change', ...)

// Recalculate on efficiency value change
document.getElementById('customEfficiency').addEventListener('input', calculate)

// Mutual exclusivity with luxury consumables
document.getElementById('includeLuxury').addEventListener('change', ...)
```

## User Workflows

### Use Case 1: Testing Different Workforce Qualities
1. Select material and recipe
2. Check "Use Custom Workforce Efficiency"
3. Try different efficiency values:
   - 90% = High-quality workforce
   - 79% = Basic workforce (default)
   - 60% = Poor workforce conditions

### Use Case 2: Matching Real-World Efficiency
1. Player knows their actual workforce efficiency from game
2. Check "Use Custom Workforce Efficiency"
3. Enter exact percentage (e.g., 83%)
4. See accurate profit calculations for their specific setup

### Use Case 3: Quick Comparison
1. Start with luxury consumables (100% efficiency)
2. Switch to custom efficiency
3. Set to 79% to see cost difference
4. Adjust up/down to find breakeven efficiency

## Testing Checklist
- [x] Custom efficiency toggle shows/hides input field
- [x] Luxury consumables checkbox disables custom efficiency
- [x] Custom efficiency unchecks luxury consumables
- [x] Efficiency value applies to main profit calculation
- [x] Efficiency value applies to exchange comparison
- [x] Efficiency value applies to recipe recommendations
- [x] Input validation (1-100 range)
- [x] Default value (79%) pre-filled
- [x] Real-time recalculation on value change

## Benefits
✅ **Flexibility**: Users can model any efficiency scenario  
✅ **Accuracy**: Match in-game workforce setup exactly  
✅ **Education**: See how efficiency impacts profitability  
✅ **Planning**: Determine minimum efficiency for profitability  
✅ **Non-Breaking**: Existing workflows unchanged (defaults to 79%)

## Future Enhancements
- Add efficiency presets (Basic, Good, Excellent)
- Show efficiency percentage in results display
- Add tooltip explaining efficiency calculation
- Save custom efficiency preference in browser localStorage
- Add efficiency impact comparison chart
