# PrUn-Tracker Features Guide

Complete guide to all features in the PrUn-Tracker Price Analyser.

## 🎯 Core Features

### Multi-Recipe Comparison
Compare all available production methods for a material to find the most profitable option.

**How it works:**
1. Select a material (e.g., PE, DW, RAT)
2. Choose an exchange (AI1, CI1, CI2, IC1, NC1, NC2)
3. See all recipes sorted by ROI (Return on Investment)

**Visual Indicators:**
- 💎 **BEST ROI Badge**: Highlights the most profitable recipe
- 🟢 **Green Background**: Better ROI than your selected recipe
- 🔴 **Red Background**: Worse ROI than your selected recipe
- 🔵 **Blue Background**: Currently selected recipe

### 4 ROI Scenarios

The calculator shows profitability under 4 different trading conditions:

| Scenario | You Sell At | You Buy Inputs At | Use Case |
|----------|-------------|-------------------|----------|
| **Ask/Ask** | Ask (higher) | Ask (higher) | Instant buy & sell, worst margins |
| **Ask/Bid** | Ask (higher) | Bid (lower) | Sell instantly, patient buying |
| **Bid/Ask** | Bid (lower) | Ask (higher) | Patient selling, instant buying |
| **Bid/Bid** | Bid (lower) | Bid (lower) | Patient both ways, best margins |

**Formula:**
```
Profit = Sell Price - (Input Cost + Workforce Cost)
ROI = (Profit / Total Cost) × 100%
Breakeven = Total Cost / |Profit|
```

## 🌍 Planet-Based Features

### Extraction Building Optimization

When using extraction buildings (EXT, RIG, COL), the system automatically filters recipes based on what's available on your selected planet.

**Example:**
- Planet: Montem
- Building: EXT
- Shows only: H2O, O, LST, CU (materials available on Montem)
- Hides: ALO, FE, other materials not found on Montem

**Extraction Types:**
- **EXT** - Standard Extractor (24h base, 0.7 multiplier)
- **RIG** - Heavy Rig (48h base, 0.7 multiplier)  
- **COL** - Collector (gaseous, 24h base, 0.6 multiplier)

**Time Adjustment Formula:**
```
Adjusted Hours = max(6, min(240, Base Hours / Concentration Factor))
Workforce Cost = Base Workforce Cost × (Adjusted Hours / Base Hours)
```

### Farming Fertility System

28 planets support farming with fertility modifiers affecting production efficiency.

**Official Formula (from PCT):**
```
Fertility Modifier = RawFertility × (10/33)
Efficiency = 100% + (Fertility Modifier × 100%)
```

**Example - ZV-759c:**
- Raw Fertility: -0.34
- Modifier: -0.34 × (10/33) = -0.103
- Efficiency: 100% + (-10.3%) = **89.7%**
- Cost Impact: 111.5% of base cost (11.5% slower)

**Best vs Worst:**
- Best: +0.4 fertility → 112.1% efficiency → 71% cost ✅
- Worst: -0.5 fertility → 84.8% efficiency → 200% cost ❌

**28 Farmable Planets:**
Only 0.8% of all planets in the game support farming. The system includes planets with fertility data even if they have no extraction resources (e.g., Demeter).

## 📊 Market Indicators

### Supply, Demand, Traded Volume

Real-time market data displayed for every material:

- **Supply**: Total available units (all sell orders)
- **Demand**: Total wanted units (all buy orders)
- **Traded Volume**: Units traded in last 24 hours

**Displayed in:**
1. Main market indicators section
2. Building comparison (each alternative recipe)
3. Exchange comparison (each exchange)

**Liquidity Analysis:**
```
Liquidity Ratio = Traded Volume / Supply
High liquidity (>0.5): Easy to sell large quantities
Low liquidity (<0.1): May take time to offload inventory
```

### Last Update Timestamp

Displays when data was last refreshed from the FIO API.

**Format:**
```
📊 Data last updated: 5m ago (24/11/2025, 14:30:45 local time)
```

**Features:**
- Human-readable "time ago" (e.g., "5m ago", "1h 23m ago")
- Full timestamp in your local timezone
- UTC source data for consistency across users
- Updates automatically when pipeline runs

## 🎨 UI/UX Features

### ROI Badge System

**Best ROI Badge (💎):**
- Automatically identifies highest ROI option
- Appears on the most profitable recipe in comparisons
- Helps quick decision-making

**Color Coding:**
- **Green (#d4edda)**: Better than selected (green border #28a745)
- **Red (#f8d7da)**: Worse than selected (red border #dc3545)
- **Blue (#cce5ff)**: Currently selected (blue border #004085)

### Mobile Responsive Design

Optimized for viewing on phones and tablets:

**Desktop:**
```
[Badge] [Badge] [Badge] - horizontal row
```

**Mobile (<768px):**
```
[Badge]
[Badge]
[Badge]
```
Badges stack vertically for easier reading on small screens.

**Scrollable Tables:**
Exchange comparison table scrolls horizontally on mobile to show all exchanges.

## ⚙️ Cost Calculation Options

### Include Luxury Consumables

Toggle workforce luxury items (PWO, COF, REP, etc.)

**Without Luxury:**
- Efficiency: 79%
- Workforce Cost: 1 / 0.79 = 1.266× higher
- Use case: Starting bases, emergency production

**With Luxury (default):**
- Efficiency: 100%
- Workforce Cost: Standard
- Use case: Established operations

### Self-Produced Inputs

Calculate costs assuming you produce all inputs yourself instead of buying from market.

**How it works:**
1. Recursively looks up production cost for each input material
2. Uses cheapest recipe for each input
3. Adds workforce costs at each production stage
4. Falls back to market price for tier-0 materials

**Example - PE (Polyethylene):**
```
Market Input Costs:
- 1 C (Carbon): 150 ICA
- 2 H (Hydrogen): 100 ICA each
Total Market Cost: 350 ICA

Self-Production:
- C production cost: 80 ICA + 20 workforce = 100 ICA
- H production cost: 40 ICA each + 15 workforce = 55 ICA each
Total Self-Production Cost: 210 ICA (40% savings!)
```

### CoGC Program Bonus

**Corporatist Governance Code (CoGC):**
- Flat +25% efficiency boost
- Additive with planet and expert bonuses
- Costs 1 permit per base per week

**Efficiency Stacking:**
```
Base: 100%
Planet Concentration: +100% (2.0 factor)
CoGC: +25%
5 Experts: +28.4%
─────────────────────
Additive Total: 253.4%

Then multiply by HQ bonuses:
Company HQ: ×1.26 (10% base × 2.6 specialization)
Corp HQ: ×1.10 (planet-specific)
─────────────────────
Final Efficiency: 351.2%
Cost: 28.5% of base (71.5% savings!)
```

### Expert Bonuses

Up to 5 experts per building category:

**Efficiency per Expert:**
| Experts | Bonus | Cumulative |
|---------|-------|------------|
| 1 | +8.0% | 8.0% |
| 2 | +6.4% | 14.4% |
| 3 | +5.1% | 19.5% |
| 4 | +4.1% | 23.6% |
| 5 | +4.8% | **28.4%** |

**Formula:**
```
Bonus = 0.80 × (0.80^(n-1))  for first 4 experts
Bonus = Custom value for 5th expert
```

## 🏢 Headquarters Bonuses

### Company HQ

**Faction-Specific Bonuses:**
- NEO/CAST: 10% (Agriculture, Food Industries, Resource Extraction)
- ICA/NC: 6% (Construction, Manufacturing)  
- CIS/IC: 4% (Electronics, Fuel Refining)

**Specialization Multiplier:**
- 1 base: 1.0× (0% bonus effectively)
- 2 bases: 1.3×
- 3 bases: 1.6×
- 4 bases: 1.95×
- 5 bases: 2.6×
- 6+ bases: 3.0×

**Input Methods:**
1. **Number of Bases**: Automatically calculates multiplier
2. **Number of Permits**: Calculates bases, then multiplier
3. **Direct Multiplier**: Enter final value directly

**Calculation:**
```
Company HQ Efficiency = Faction Bonus × Specialization Multiplier
Example: 10% × 2.6 = 26% bonus

Applied multiplicatively after additive bonuses:
253.4% additive × 1.26 Company HQ = 319.3%
```

### Corporation HQ (Corp HQ)

**Simple +10% Multiplicative Bonus:**
- Planet-specific (one Corp HQ per planet)
- Applied AFTER Company HQ
- Checkbox toggle in calculator

**Example:**
```
253.4% additive 
× 1.26 Company HQ 
× 1.10 Corp HQ 
= 351.2% total efficiency
```

## 🔍 Advanced Features

### Exchange Comparison

Compare profitability across all 6 exchanges to find best market:

**Shown for each exchange:**
- Ask Price (sell price)
- Bid Price (buy price)
- Total Production Cost
- Profit (Ask - Cost)
- ROI%
- Supply/Demand/Traded Volume

**Sorted by:** ROI (descending)

**Use Cases:**
- Find where to set up production
- Identify arbitrage opportunities
- Plan logistics routes

### Building Comparison

Compare all products you can make with the same building:

**Example - BMP (Basic Materials Plant):**
- Shows: C, H, O, H2O, N, Cl, F, S, etc.
- For each: Output amount, costs, profit, ROI
- Helps decide what to produce with your existing infrastructure

**Recipe Sorting:**
- Primary: ROI (descending)
- Shows ROI badges for quick identification

### Arbitrage Detection

Finds cross-exchange trading opportunities:

**Logic:**
```
Buy at Exchange A (Ask price)
Transport to Exchange B
Sell at Exchange B (Bid price)

Profit = B_Bid - A_Ask - Transport_Cost
```

**Filters:**
- Only shows opportunities >5% profit (covers ~5% transport cost)
- Sorted by profit percentage
- Displays both buy/sell exchanges and profit margins

### Breakeven Analysis

Shows how many production runs needed to recover costs:

**Formula:**
```
Breakeven = Total Cost / |Profit|
```

**Example:**
- Total Cost: 1000 ICA
- Profit per Run: 250 ICA
- Breakeven: 4 runs

**Interpretation:**
- Low breakeven (<5): Quick profit
- Medium (5-20): Reasonable investment
- High (>20): Consider alternatives

## 📋 Data Requirements

### Price Analyser Data Sheet

**15 Columns (A-O):**
| Column | Name | Description |
|--------|------|-------------|
| A | LookupKey | Ticker+Exchange (e.g., "AARCI1") |
| B | Ticker | Material code (e.g., "AAR") |
| C | Recipe | Full recipe string |
| D | Material Name | Human-readable name |
| E | Exchange | Exchange code |
| F | Ask_Price | Sell price |
| G | Bid_Price | Buy price |
| H | Input Cost Ask | Material costs (ask basis) |
| I | Input Cost Bid | Material costs (bid basis) |
| J | Workforce Cost Ask | Labor costs (ask basis) |
| K | Workforce Cost Bid | Labor costs (bid basis) |
| L | Amount per Recipe | Output quantity |
| M | Supply | Market supply |
| N | Demand | Market demand |
| O | **Traded Volume** | 24h traded units |

### Metadata Sheet

**Key-Value Format:**
```
Key                 | Value
--------------------|------------------------
Last Data Update    | 2025-11-24T14:30:45.123456+00:00
```

Timestamp format: ISO 8601 UTC

### Planet Resources Sheet

**Columns:**
- Key (auto-generated ID)
- Planet (planet name)
- Ticker (material code)
- Type (resource type)
- Factor (concentration factor)
- **Fertility** (farming fertility modifier)

**Example:**
```
Planet     | Ticker | Type    | Factor | Fertility
-----------|--------|---------|--------|----------
Montem     | H2O    | Liquid  | 2.45   | -0.12
Montem     | O      | Gaseous | 1.80   | -0.12
ZV-759c    | FARMING| N/A     | N/A    | -0.34
Demeter    | FARMING| N/A     | N/A    | 0.15
```

**Fertility-Only Planets:**
Planets without extraction resources but with farming capability use placeholder 'FARMING' ticker.

### Bids Sheet

Used for breakeven calculations (cumulative bid analysis):
- MaterialTicker
- ExchangeCode
- ItemCount (quantity)
- ItemCost (price per unit)

## 🔧 Technical Details

### Recipe Format Parsing

**Two formats supported:**

1. **Standard Building Recipe:**
   ```
   BMP:1xC-2xH=>200xPE
   │   │       └─ Outputs
   │   └─ Inputs
   └─ Building
   ```

2. **Extraction Recipe:**
   ```
   EXT=>H2O
   │    └─ Output (no inputs for extraction)
   └─ Building
   ```

**Regex Pattern:**
```javascript
/(\d+)x([A-Z0-9]+)/g
```
Matches: `1xC`, `200xPE`, `40xH2O`, `5xCO2`

### Client-Side Data Loading

All data loaded once via `getAllData()` to minimize API calls:

**Advantages:**
- Faster UI interactions (no server round-trips)
- Reduced quota usage on Google Apps Script
- Enables instant filtering and sorting
- Better offline experience

**Data Structure:**
```javascript
{
  success: true,
  data: [...],        // All price analyser rows
  bids: [...],        // Order book data
  planets: [...],     // Extraction resources
  fertility: [...],   // Farming data
  rowCount: 15000,
  lastUpdated: "2025-11-24T14:30:45.123456+00:00"
}
```

### Timezone Handling

**Python (Data Pipeline):**
```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()
# Output: "2025-11-24T14:30:45.123456+00:00"
```

**JavaScript (Frontend):**
```javascript
const updateDate = new Date(result.lastUpdated);
// Automatically parses ISO UTC and converts to local timezone
```

**Display:**
- Shows relative time ("5m ago", "1h 23m ago")
- Shows local timestamp with explicit "(local time)" label
- Eliminates timezone confusion

## 🐛 Recent Bug Fixes

### Traded Volume (Column O)

**Issue:** Column O showing 0 despite data in sheets  
**Cause:** Column named 'Traded' in code but 'Traded Volume' in upload  
**Fix:** Standardized to 'Traded Volume' throughout pipeline

### Recipe Parsing (Materials with Numbers)

**Issue:** H2O showing as "H" (regex only matched [A-Z])  
**Example:** "40 H2O" displayed as "40 H"  
**Fix:** Changed regex from `[A-Z]+` to `[A-Z0-9]+`

### Fertility Calculations

**Issue:** Wrong formula causing incorrect efficiency percentages  
**Example:** ZV-759c showing 66% instead of 89.7%  
**Fix:** Implemented official PCT formula: `RawFertility × (10/33)`

### Building Comparison Persistence

**Issue:** Comparison showing for previous material after switching  
**Cause:** No hide logic when new material has only one recipe  
**Fix:** Added else clauses to hide section when not applicable

### Report Deduplication

**Issue:** Same material appearing multiple times in TOP MATERIALS TO INVEST IN  
**Cause:** Multiple recipes per material counted separately  
**Fix:** Added `drop_duplicates(subset=['Ticker'], keep='first')`

---

## 🚀 Tips & Best Practices

1. **Use ROI for comparison, Profit for scale decisions**
   - ROI: Which recipe is most efficient
   - Profit: How much money per run

2. **Check Traded Volume before scaling production**
   - High volume: Safe to produce large quantities
   - Low volume: Market may not absorb your output

3. **Start with Bid/Bid scenario planning**
   - Most realistic for patient traders
   - Ask/Ask shows instant-gratification worst case

4. **Compare building alternatives regularly**
   - Market prices change
   - Best product today may not be best tomorrow

5. **Factor in transport costs for exchange arbitrage**
   - Rule of thumb: Need >5% margin
   - Consider time value of capital

6. **Use self-production toggle strategically**
   - Vertical integration can reduce costs
   - But ties up more capital and infrastructure

7. **Check timestamp before major decisions**
   - Ensure data is recent (<1 hour old)
   - Refresh if data seems stale

---

For more information, see:
- **[README.md](README.md)** - Project overview
- **[CHANGELOG.md](CHANGELOG.md)** - Recent updates
- **[WIKI.md](WIKI.md)** - Technical documentation
