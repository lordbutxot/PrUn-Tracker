# Extraction Recipe System

## Overview

The PrUn-Tracker now generates synthetic extraction recipes for all tier-0 (raw/extractable) materials. These recipes include:
- **Correct extraction buildings** (COL, EXT, RIG)
- **Workforce requirements** (Pioneer workers)
- **Planet-adjusted production times** based on actual resource concentration data

## How It Works

### 1. Extraction Buildings

Three building types extract raw materials from planets:

| Building | Type | Workforce | Capacity | Base Time | Resources Extracted |
|----------|------|-----------|----------|-----------|---------------------|
| **COL** (Collector) | Gas collection | 50 Pioneers | - | 24h/100 | Atmospheric gases (H, O, N, HE, AR, NE, etc.) |
| **EXT** (Extractor) | Surface mining | 60 Pioneers | - | 24h/100 | Ores and minerals (FEO, ALO, CUO, SIO, etc.) |
| **RIG** (Rig) | Deep extraction | 30 Pioneers | - | 48h/100 | Rare ores, water (H2O, AUO, GAL) |

### 2. Planet Resource Concentration

Real extraction times vary dramatically based on **planet resource concentration**.

**Data Source**: `https://rest.fnar.net/csv/planetresources`

Format:
```csv
Key,Planet,Ticker,Type,Factor
AJ-293b-FEO,AJ-293b,FEO,MINERAL,0.7174611687660217
AJ-135a-FEO,AJ-135a,FEO,MINERAL,0.011724736541509628
```

- **Factor**: Resource concentration (0.0 to 1.0+)
- Higher factor = better concentration = faster extraction
- Lower factor = poor concentration = slower extraction

### 3. Time Calculation Formula

```
Actual Extraction Time = Base Time / Average Concentration Factor
```

**Examples:**

**FEO (Iron Ore)**:
- Average factor across all planets: **0.333**
- Base time: 24h
- Actual time: 24 / 0.333 = **72.0 hours per 100 units**

**Argon (AR)**:
- Average factor: **0.092** (very poor)
- Base time: 24h
- Actual time: 24 / 0.092 = **240 hours** (capped at maximum)

**Limestone (LST)**:
- Average factor: **0.308** (good)
- Base time: 24h
- Actual time: 24 / 0.308 = **77.8 hours per 100 units**

### 4. Time Limits

To prevent extreme values:
- **Minimum**: 6 hours per 100 units
- **Maximum**: 240 hours per 100 units

### 5. Workforce Cost Impact

Longer extraction times = higher workforce costs:

**FEO (72h extraction)**:
- 60 Pioneers × 72 hours
- Consumables: DW (4/day), RAT (4/day), OVE (0.5/day)
- Luxury adds: COF (0.5/day), PWO (0.2/day)
- Total: ~240% more workforce cost than 24h extraction

**With luxury efficiency (100%)**:
- Cost = Base workforce consumables × 72h

**Without luxury (79% efficiency)**:
- Cost = (Base workforce consumables × 72h) × (1/0.79)
- ~26.6% additional penalty for poor satisfaction

## Extraction Recipe Format

Generated recipes follow this format:

**Recipe Key**: `BUILDING=>100xTICKER`

Example: `EXT=>100xFEO`

**buildingrecipes.csv**:
```csv
Key,Building,Duration
EXT=>100xFEO,EXT,259200
COL=>100xO,COL,544680
RIG=>100xH2O,RIG,633240
```

Duration in seconds: `hours × 3600`

**recipe_outputs.csv**:
```csv
Key,Material,Amount
EXT=>100xFEO,FEO,100
COL=>100xO,O,100
RIG=>100xH2O,H2O,100
```

## Pipeline Integration

### Data Collection (`catch_data.py`)

```python
def fetch_planetresources_csv():
    url = "https://rest.fnar.net/csv/planetresources"
    # Downloads planet resource concentration data
```

Called during pipeline Step 1 (Data Collection).

### Recipe Generation (`generate_extraction_recipes.py`)

```python
def load_planet_resource_factors():
    # Loads planetresources.csv
    # Calculates average factor per material
    # Returns: {'FEO': {'mean': 0.333, 'min': 0.011, 'max': 0.717}}

def calculate_extraction_time(base_hours, avg_factor_data):
    # Applies formula: base_time / concentration_factor
    # Returns: Adjusted extraction time with limits

def generate_extraction_recipes():
    # Creates synthetic recipes for all tier-0 materials
    # Applies planet-adjusted times
    # Merges into buildingrecipes.csv and recipe_outputs.csv
```

Called during pipeline Step 1.6 (After tier assignment).

### Pipeline Steps

```
1. Data Collection
   ├── Fetch market data
   ├── Fetch planetresources.csv ← NEW
   ├── Fetch workforceneeds.json
   └── Fetch bids/orders

2. Tier Assignment
   └── Assign tier 0 to extractable materials

3. Extraction Recipes ← NEW
   ├── Load planet resource factors
   ├── Calculate adjusted extraction times
   └── Generate synthetic recipes

4. Data Processing
   └── Process all data including extraction recipes

5. Analysis & Upload
   └── Calculate costs with adjusted extraction times
```

## Material Examples

### Fast Extraction (Good Concentration)

| Material | Factor | Building | Time/100 | Description |
|----------|--------|----------|----------|-------------|
| **FEO** | 0.333 | EXT | 72.0h | Iron ore - common, medium extraction |
| **SIO** | 0.314 | EXT | 76.4h | Silicon ore - abundant |
| **LST** | 0.308 | EXT | 77.8h | Limestone - common |
| **MGS** | 0.252 | EXT | 95.1h | Magnesium silicate |

### Medium Extraction

| Material | Factor | Building | Time/100 | Description |
|----------|--------|----------|----------|-------------|
| **H** | 0.166 | COL | 144.3h | Hydrogen gas |
| **O** | 0.159 | COL | 151.3h | Oxygen gas |
| **N** | 0.156 | COL | 153.7h | Nitrogen gas |
| **H2O** | 0.273 | RIG | 175.9h | Water - medium availability |

### Slow Extraction (Poor Concentration)

| Material | Factor | Building | Time/100 | Description |
|----------|--------|----------|----------|-------------|
| **BER** | 0.109 | EXT | 220.8h | Beryl - rare mineral |
| **BOR** | 0.101 | EXT | 238.4h | Borate - very rare |
| **AR** | 0.092 | COL | 240.0h | Argon - extremely rare gas |
| **HE** | 0.088 | COL | 240.0h | Helium - very rare |
| **LES** | 0.037 | EXT | 240.0h | Limestone - extremely poor |

## Benefits

### 1. Realistic Costs
- Materials with poor planet concentrations correctly show higher extraction costs
- Rare materials (AR, HE, BER) are now expensive to extract
- Common materials (FEO, SIO) are cheaper

### 2. Market Accuracy
- Extraction costs better reflect real game mechanics
- Price Analyser shows realistic workforce costs for tier-0 materials
- Better profitability analysis for extraction vs purchase decisions

### 3. Strategic Planning
- Players can identify which tier-0 materials are expensive to extract
- Helps decide: extract locally vs buy from market?
- Shows true cost of "free" raw materials

### 4. Complete Data Coverage
- All 49 tier-0 materials now have recipes
- No more "N/A" recipes for extractable resources
- Workforce costs calculated for all materials

## Configuration

### Adjusting Base Times

Edit `EXTRACTION_BUILDINGS` in `generate_extraction_recipes.py`:

```python
EXTRACTION_BUILDINGS = {
    'COL': {'workforce': 'PIONEER', 'capacity': 50, 'base_hours_per_100': 24},
    'EXT': {'workforce': 'PIONEER', 'capacity': 60, 'base_hours_per_100': 24},
    'RIG': {'workforce': 'PIONEER', 'capacity': 30, 'base_hours_per_100': 48}
}
```

### Adjusting Time Limits

Edit `calculate_extraction_time()`:

```python
# Cap at reasonable limits (6h minimum, 240h maximum per 100 units)
adjusted_hours = max(6, min(240, adjusted_hours))
```

### Building Assignment Logic

Edit `get_extraction_building_for_material()`:

```python
# Gas collectors
if 'gas' in category_lower or ticker in ['H', 'O', 'N', ...]:
    return 'COL'

# Deep rigs for specific ores
if ticker in ['AUO', 'GAL', 'TIT']:
    return 'RIG'

# Default extractor for ores/minerals
if 'ore' in category_lower or 'mineral' in category_lower:
    return 'EXT'
```

## Troubleshooting

### No planetresources.csv

If planetresources.csv is missing:
- System uses default base times without adjustment
- All materials of same building type get same time
- Run: `python historical_data/catch_data.py` to fetch it

### Extreme Extraction Times

If times seem wrong:
- Check planet resource factors in planetresources.csv
- Verify average calculations are correct
- Adjust min/max limits in `calculate_extraction_time()`

### Missing Materials

If some tier-0 materials don't have recipes:
- Check materials.csv for Tier=0.0
- Verify building assignment logic
- Check for NaN tickers (will skip)

## Future Enhancements

### 1. Planet-Specific Costs
Currently uses **average** concentration across all planets.

Could add:
- Best planet extraction cost (highest factor)
- Worst planet extraction cost (lowest factor)
- User selects their planet for accurate local costs

### 2. Resource Depletion
Planet resources deplete over time in-game.

Could add:
- Depletion rate tracking
- Time-based concentration adjustments
- Sustainability analysis

### 3. Extraction Efficiency Experts
Game has experts that boost extraction rates.

Could add:
- Expert bonus multipliers (similar to production efficiency)
- Cumulative expert effects
- Time reduction calculations

### 4. Advanced Rig Mechanics
Rigs have special mechanics (deep core access).

Could add:
- Rig upgrade levels
- Deep core vs surface extraction
- Equipment efficiency bonuses

---

**Last Updated**: November 20, 2025  
**Version**: v1.0 (Planet-adjusted extraction system)  
**Dependencies**: planetresources.csv from FnarAPI
