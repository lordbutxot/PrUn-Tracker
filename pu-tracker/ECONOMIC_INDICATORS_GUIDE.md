# Economic Indicators Guide - PrUn Tracker

## Overview
This document explains the economic indicators calculated by the Financial Overview tab and how they extrapolate real-world economic concepts to the Prosperous Universe game economy.

---

## I. CALCULATED ECONOMIC INDICATORS

### 1. GDP Proxy Metrics (Gross Domestic Product)

**What is GDP?**
In real-world economics, GDP measures the total economic output of a country. In PrUn, we calculate it as:

**GDP = Sum of (Material Ask Price × Number of Materials)**

This represents the total "market capitalization" of all tracked materials.

**Metrics Provided:**
- **Total Market Capitalization**: Sum of all Ask prices across all materials
- **Total Profit Potential**: Sum of all profit margins (economic activity indicator)
- **Exchange GDP Contribution**: How much each exchange contributes to total market value
  - Higher % = that exchange is more economically significant
  - Helps identify which exchanges dominate the economy

**Interpretation:**
- Rising GDP = Economy expanding (more production, higher prices)
- Falling GDP = Economy contracting (less production, lower prices)
- Exchange with highest GDP% = Most important trading hub

---

### 2. Purchasing Power Parity (PPP)

**What is PPP?**
PPP measures how much "purchasing power" a currency has by comparing the cost of the same basket of goods across different markets.

**How We Calculate It:**
1. Use AI1 (Moria Station) as the **base exchange** (index = 1.00)
2. Calculate average price of all materials on each exchange
3. Compare each exchange's prices to AI1
4. Formula: `PPP Index = Avg Price on Exchange / Avg Price on AI1`

**Interpretation:**

| PPP Index | Meaning | Example |
|-----------|---------|---------|
| **< 0.95** | **CHEAP (Strong Purchasing Power)** | Goods cost less than AI1, your money goes further |
| **0.95 - 1.05** | **NEUTRAL** | Prices similar to AI1 |
| **> 1.05** | **EXPENSIVE (Weak Purchasing Power)** | Goods cost more than AI1, your money buys less |

**Real-World Example:**
If IC1 has PPP = 0.85, it means goods cost 15% less than AI1 on average.
If NC2 has PPP = 1.20, it means goods cost 20% more than AI1 on average.

**Strategic Use:**
- **Buy materials** from exchanges with **low PPP** (cheaper)
- **Sell materials** to exchanges with **high PPP** (more expensive)
- **Relocate production** to low PPP exchanges (lower input costs)

---

### 3. Exchange Competitiveness Analysis

**What It Measures:**
How attractive each exchange is for economic activity based on:
- **Avg/Median Profit**: How much profit can be made per material
- **Material Diversity**: How many different materials are available (market depth)
- **Avg Price**: General price level (lower = more cost-competitive)
- **Profit/Material**: Efficiency metric (higher = more profitable on average)

**Interpretation:**

| High Value | Meaning |
|------------|---------|
| **High Profit/Material** | Very profitable exchange, good for producers |
| **High Material Diversity** | Liquid market, many trading opportunities |
| **Low Avg Price** | Cost-competitive, good for buyers |
| **High Median Profit** | Consistently profitable (not just a few outliers) |

**Strategic Use:**
- Set up production bases on exchanges with high Profit/Material
- Source materials from exchanges with high Material Diversity (more options)
- Avoid exchanges with low diversity (limited market)

---

### 4. Inflation Proxy (Price Volatility)

**What is Inflation?**
Inflation = general increase in prices over time, reducing purchasing power.

**How We Estimate It:**
Since we don't have historical time-series data yet, we use **price volatility** as a proxy:
- **High Volatility** = Unstable prices, inflation-like pressure
- **Low Volatility** = Stable prices, low inflation

**Formula:**
`Volatility % = (Standard Deviation of Prices / Average Price) × 100`

**Metrics:**
- **Category-level volatility**: Which sectors have unstable pricing
- **Sample Size**: How many materials in each category

**Interpretation:**

| Volatility % | Interpretation |
|--------------|----------------|
| **< 20%** | Stable prices (low inflation risk) |
| **20% - 50%** | Moderate instability |
| **> 50%** | High instability (potential inflation/deflation) |

**Note:** This is a **proxy**. True inflation requires comparing prices over time:
- If you have historical data: Calculate `(Current Price - Old Price) / Old Price × 100`
- Future Enhancement: Store daily snapshots to calculate real inflation rates

---

## II. DATA ACQUISITION FROM EXTERNAL SPREADSHEET

### What Data Is Fetched?

The script automatically fetches **all sheets** from the external Google Spreadsheet:
```
Spreadsheet ID: 17MvM86qR-mN7fSPX86L7TbvDXLBYRCT5IlCd5zfXddA
```

**Expected Data Types:**
1. **Currency Exchange Rates**: Conversion rates between ICA, AIC, NCC, CIS, BEN
2. **Historical Price Data**: Time-series price data for key commodities
3. **Production Statistics**: Sector-level output data
4. **Trade Volumes**: Transaction volumes per exchange
5. **Economic Indicators**: Community-maintained economic metrics

### How to Add Custom Metrics

If you want to calculate additional indicators:

1. **Add to external spreadsheet** (manually maintained)
2. **Fetch automatically** (script downloads all sheets)
3. **Calculate from existing data** (add function to `generate_report_tabs.py`)

---

## III. FUTURE ENHANCEMENTS

### Real Inflation Calculation (Requires Historical Data)

```python
def calculate_real_inflation(current_df, historical_df):
    """
    Calculate true inflation rate by comparing prices over time.
    
    Formula: Inflation = ((Current Price - Historical Price) / Historical Price) × 100
    """
    # Merge current and historical data
    merged = current_df.merge(historical_df, on='Ticker', suffixes=('_now', '_past'))
    
    # Calculate inflation per material
    merged['Inflation_Rate'] = ((merged['Ask_Price_now'] - merged['Ask_Price_past']) 
                                / merged['Ask_Price_past'] * 100)
    
    # Overall inflation (weighted by market cap)
    total_inflation = merged['Inflation_Rate'].mean()
    
    return total_inflation, merged[['Ticker', 'Inflation_Rate']]
```

### GDP Growth Rate

```python
def calculate_gdp_growth(current_gdp, historical_gdp):
    """
    Calculate GDP growth rate.
    
    Formula: Growth Rate = ((Current GDP - Past GDP) / Past GDP) × 100
    """
    return ((current_gdp - historical_gdp) / historical_gdp * 100)
```

### Exchange Rate Analysis

```python
def calculate_implied_exchange_rates(all_df):
    """
    Calculate implied exchange rates from arbitrage price differences.
    
    Example: If PE costs 100 ICA on AI1 but 120 NCC on NC1,
    implied rate = 1 ICA = 1.2 NCC
    """
    # Find common materials traded on multiple exchanges
    common_tickers = all_df.groupby('Ticker').filter(lambda x: len(x) > 1)['Ticker'].unique()
    
    exchange_rates = {}
    for ticker in common_tickers:
        ticker_data = all_df[all_df['Ticker'] == ticker]
        # Calculate price ratios between exchanges
        # ...
    
    return exchange_rates
```

---

## IV. STRATEGIC APPLICATIONS

### For Producers
1. **Check PPP**: Produce on low-PPP exchanges (lower costs)
2. **Check Competitiveness**: Set up on high Profit/Material exchanges
3. **Monitor Volatility**: Avoid high-volatility categories (risky pricing)

### For Traders
1. **Arbitrage**: Buy on low-PPP exchanges, sell on high-PPP exchanges
2. **Market Selection**: Trade on high Material Diversity exchanges (more opportunities)
3. **Price Timing**: Buy during low volatility (stable prices)

### For Investors
1. **GDP Growth**: Invest in economies with rising GDP (expanding markets)
2. **Inflation Hedge**: Stockpile materials in high-inflation categories
3. **Exchange Selection**: Focus capital on high-competitiveness exchanges

---

## V. TECHNICAL NOTES

### Data Sources
- **Internal Data**: Calculated from `daily_analysis_enhanced.csv`
- **External Data**: Fetched from Google Sheets
- **Cache**: Stored in `cache/financial_data/*.csv`

### Calculation Frequency
- Real-time: PPP, Competitiveness (based on current market data)
- Batch: GDP, Inflation (requires full dataset scan)
- Manual: External data (updated when spreadsheet changes)

### Known Limitations
1. **No Time-Series**: Can't calculate true inflation yet (need historical snapshots)
2. **Sample Bias**: Only includes materials with profitable recipes
3. **Currency Assumption**: All prices in ICA equivalent
4. **Static External Data**: Manual spreadsheet updates required

---

## VI. INTERPRETATION EXAMPLE

```
Exchange: IC1 (Insitor)
- PPP Index: 0.88 → CHEAP (goods 12% cheaper than AI1)
- Avg Profit: 1,250 ICA → Good profit margins
- Material Diversity: 289 → Very liquid market
- Volatility: 35% → Moderate price instability

Strategic Interpretation:
✓ Excellent for PRODUCTION (low costs due to low PPP)
✓ Good for TRADING (many materials available)
⚠ Moderate risk due to price volatility
→ Recommended for established producers with buffer capital
```

---

## VII. GLOSSARY

| Term | Definition |
|------|------------|
| **GDP** | Total market value of all goods |
| **PPP** | Relative purchasing power between markets |
| **Inflation** | Rate of price increases over time |
| **Volatility** | Price instability (standard deviation) |
| **Market Cap** | Total value of all materials (Price × Quantity) |
| **ROI** | Return on Investment (Profit / Cost × 100) |
| **Competitiveness** | How attractive a market is for economic activity |
| **Arbitrage** | Buying cheap in one market, selling expensive in another |

---

## Contact & Updates
For questions or suggestions, see main README.md
