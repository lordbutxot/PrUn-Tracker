# Oxygen and Byproduct Tracking Implementation

## Problem Statement

The PrUn-Tracker system previously had a limitation where materials like **Oxygen (O)** were only recognized through their primary production recipe, missing important characteristics:

1. **Oxygen can be both extracted AND crafted**: It's available as a planetary resource (Tier 0) AND produced via the TNP recipe from Technetium Oxide
2. **Oxygen is a byproduct**: The TNP recipe produces BOTH oxygen and technetium (dual output)
3. **Cost allocation was unclear**: When recipes produce multiple outputs, how should input costs be split?

## Solution Overview

The implementation adds comprehensive support for:
- ✅ **Multiple production methods** per material
- ✅ **Byproduct tracking** for recipes with multiple outputs
- ✅ **Extractable resource identification** from planet resources API
- ✅ **Cost allocation** for byproducts based on market value

## Changes Made

### 1. Enhanced `chain_dictionary_generator.py`

**What changed:**
- Now tracks **ALL recipes** for each material, not just the primary one
- Creates `byproduct_recipes.json` to identify multi-output recipes
- Populates `tier0_resources.json` from planet resources API
- Adds new fields to `chains.json`:
  - `all_recipes`: List of all production methods
  - `min_tier`: Lowest tier among all recipes
  - `has_byproduct_recipes`: Boolean flag
  - `is_extractable`: Whether material can be extracted from planets

**Example output for Oxygen in `chains.json`:**
```json
{
  "o": {
    "inputs": ["tco"],
    "building": "tnp:1xtco=>1xo-1xtc",
    "workforce_tier": 3,
    "recipe_id": "TNP:1xTCO=>1xO-1xTC",
    "tier": 0,  // Now tier 0 because it's extractable!
    "min_tier": 0,
    "is_extractable": true,
    "recipe_count": 1,
    "all_recipes": [
      {
        "recipe_id": "TNP:1xTCO=>1xO-1xTC",
        "building": "TNP:1xTCO=>1xO-1xTC",
        "inputs": ["tco"],
        "outputs": ["o", "tc"],
        "tier": 3,
        "workforce_tier": 3,
        "is_byproduct": true
      }
    ],
    "has_byproduct_recipes": true
  }
}
```

**New file: `byproduct_recipes.json`:**
```json
{
  "TNP:1xTCO=>1xO-1xTC": {
    "recipe_id": "TNP:1xTCO=>1xO-1xTC",
    "building": "TNP:1xTCO=>1xO-1xTC",
    "inputs": ["tco"],
    "outputs": ["o", "tc"],
    "output_materials": ["o", "tc"]
  }
}
```

### 2. Enhanced `workforce_costs.py`

**New functions added:**

#### `load_byproduct_recipes()`
Loads the byproduct recipes JSON for processing.

#### `load_chains()`
Loads the enhanced chains.json with all recipe information.

#### `allocate_byproduct_costs(recipe_id, total_input_cost, market_prices, exchange)`
Allocates input costs for multi-output recipes proportionally based on market value.

**Example:**
- TNP recipe costs 100 units total to run
- Outputs: Oxygen (market price 50) + Technetium (market price 150)
- Total output value: 200
- Oxygen allocated cost: 100 × (50/200) = 25
- Technetium allocated cost: 100 × (150/200) = 75

#### `get_cheapest_acquisition_cost(ticker, market_prices, wf_consumables, chains, exchange)`
Determines the cheapest way to acquire a material:
1. Direct extraction (if extractable) - minimal cost
2. Crafting from cheapest recipe
3. Buying from market

Returns the minimum cost per unit.

#### Enhanced `calculate_input_costs_for_recipe()`
Now includes:
- `enable_byproduct_allocation` parameter (default True)
- Returns `Allocated Costs` dict for byproducts
- Returns `Has Byproducts` boolean flag

## Usage Examples

### Running the Updated Pipeline

```powershell
# 1. Regenerate all cached data with new tracking
cd e:\Github\PrUn_Tracker\PrUn-Tracker\pu-tracker\historical_data
python chain_dictionary_generator.py

# 2. Run the full pipeline
cd ..
.\run_pipeline.bat
```

### Checking Oxygen's New Classification

```python
import json

# Load chains
with open('cache/chains.json', 'r') as f:
    chains = json.load(f)

oxygen = chains['o']
print(f"Oxygen is extractable: {oxygen['is_extractable']}")
print(f"Oxygen tier: {oxygen['tier']}")  # Should be 0 now
print(f"Has byproduct recipes: {oxygen['has_byproduct_recipes']}")
print(f"All recipes: {len(oxygen['all_recipes'])}")
```

### Using Byproduct Cost Allocation

```python
from workforce_costs import (
    load_market_prices, 
    load_workforce_needs, 
    calculate_input_costs_for_recipe,
    allocate_byproduct_costs
)

market_prices = load_market_prices()
wf_consumables = load_workforce_needs()

# Example TNP recipe
recipe_row = {
    'Recipe': 'TNP:1xTCO=>1xO-1xTC',
    'WorkforceType': 'technician',
    'HoursPerRecipe': 10,
    'UnitsPerRecipe': 2,  # Produces 1 O + 1 TC
    'InputMaterials': {'tco': 1},
    'OutputMaterials': {'o': 1, 'tc': 1}
}

costs = calculate_input_costs_for_recipe(
    recipe_row, 
    market_prices, 
    wf_consumables, 
    enable_byproduct_allocation=True
)

print(f"Total input cost: {costs['Input Cost per Recipe']}")
print(f"Has byproducts: {costs['Has Byproducts']}")
if costs['Allocated Costs']:
    print(f"Oxygen allocated cost: {costs['Allocated Costs'].get('o', 0)}")
    print(f"Technetium allocated cost: {costs['Allocated Costs'].get('tc', 0)}")
```

## Benefits

### 1. **Accurate Cost Calculations**
- Byproduct costs are no longer unfairly attributed to a single output
- Extraction costs are properly recognized as near-zero for tier 0 resources

### 2. **Better Decision Making**
- Players can see ALL ways to acquire a material
- Cost comparisons between extraction, crafting, and buying are possible

### 3. **Complete Data Model**
- No information loss about alternative production methods
- Full visibility into production chains

### 4. **Future Extensibility**
- Framework supports adding more complex cost allocation methods
- Can handle any number of byproducts in a recipe

## Files Modified

1. ✅ `pu-tracker/historical_data/chain_dictionary_generator.py`
2. ✅ `pu-tracker/historical_data/workforce_costs.py`

## New Files Created

1. ✅ `pu-tracker/cache/byproduct_recipes.json` (generated)
2. ✅ `pu-tracker/cache/tier0_resources.json` (populated from API)
3. ✅ `OXYGEN_AND_BYPRODUCTS_IMPLEMENTATION.md` (this file)

## Testing

To verify the implementation works correctly:

```python
# Test script
import json
from pathlib import Path

CACHE = Path('pu-tracker/cache')

# 1. Check byproduct_recipes.json exists and has TNP recipe
with open(CACHE / 'byproduct_recipes.json') as f:
    byproducts = json.load(f)
    assert 'TNP:1xTCO=>1xO-1xTC' in byproducts
    print("✓ Byproduct recipes tracking works")

# 2. Check tier0_resources.json is populated
with open(CACHE / 'tier0_resources.json') as f:
    tier0 = json.load(f)
    assert len(tier0) > 0
    print(f"✓ Found {len(tier0)} extractable resources")

# 3. Check oxygen is properly classified
with open(CACHE / 'chains.json') as f:
    chains = json.load(f)
    oxygen = chains['o']
    assert oxygen['is_extractable'] == True
    assert oxygen['has_byproduct_recipes'] == True
    assert oxygen['tier'] == 0  # Should be tier 0 if extractable
    print("✓ Oxygen properly classified as extractable with byproduct recipes")

print("\n✅ All tests passed!")
```

## Next Steps (Optional Enhancements)

1. **Recursive Cost Calculation**: Implement full recursive calculation in `get_cheapest_acquisition_cost()` to find true minimum cost across all production chains

2. **Multiple Allocation Methods**: Add options for different byproduct cost allocation strategies:
   - Market value proportional (current)
   - Equal split
   - Primary/secondary designation
   - Custom ratios

3. **UI Integration**: Update the Google Sheets reports to show:
   - "Multiple acquisition methods available" indicator
   - Byproduct cost breakdown
   - Extraction vs crafting cost comparison

4. **Historical Tracking**: Track changes in optimal acquisition method over time as market prices fluctuate

## Conclusion

The implementation successfully handles the oxygen scenario and provides a robust framework for tracking materials with multiple production methods and byproduct recipes. The system now accurately represents the true economics of Prosperous Universe's production chains.
