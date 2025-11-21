# Price Analyser Enhancement: Exchange Comparison & Arbitrage Detection

## Summary

Enhanced the PrUn Price Analyser with two major new features:
1. **Exchange Comparison**: Shows prices, costs, and ROI across all exchanges
2. **Arbitrage Opportunities**: Identifies profitable buy-low-sell-high opportunities between exchanges

## Changes Made

### 1. Server-Side Functions (`AppsScript_PriceAnalyser.js`)

#### `getExchangeComparison(material, recipe, currentExchange)`
- Queries the "Price Analyser Data" sheet for all exchanges
- Collects Ask Price, Bid Price, Input Costs, and Workforce Costs per exchange
- Calculates profit and ROI for each exchange
- Sorts exchanges by ROI (descending)
- Returns best exchange and complete comparison data

#### `getArbitrageOpportunities(material)`
- Finds all exchange pairs where buy price < sell price
- Filters opportunities with >5% profit margin (accounts for transfer costs)
- Calculates profit per unit and profit percentage
- Sorts opportunities by profit percentage (descending)
- Returns top arbitrage routes

### 2. Client-Side Enhancements (`AppsScript_Index.html`)

#### New HTML Sections
- **Exchange Comparison Section**: Grid of exchange cards showing prices and ROI
- **Arbitrage Section**: Cards displaying profitable buy/sell routes

#### New CSS Styling
- `.exchange-card`: Card layout for each exchange
- `.exchange-card.best`: Highlights the exchange with best ROI (green border)
- `.exchange-card.current`: Shows the currently selected exchange (blue border)
- `.arbitrage-card`: Card layout for arbitrage opportunities (green left border)
- `.exchange-badge`: Badges for "BEST ROI" and "SELECTED" labels
- `.arbitrage-route`: Color-coded buy (red) and sell (green) exchanges
- `.arbitrage-profit`: Large percentage display with green background
- Hover effects: Cards lift and show shadow on hover

#### New JavaScript Functions

**Data Processing:**
- `getExchangeComparisonFromCache(material, recipe, currentExchange)`: Client-side processing of allData cache to group by exchange and calculate ROI
- `getArbitrageOpportunitiesFromCache(material)`: Client-side detection of profitable arbitrage routes from cached data

**Display Functions:**
- `displayExchangeComparison(data, currentExchange)`: Renders exchange comparison cards with visual indicators for best/current exchange
- `displayArbitrageOpportunities(data)`: Renders top 5 arbitrage opportunity cards with profit details

#### Modified Functions
- `calculate()`: Now calls exchange comparison and arbitrage functions after main calculation
- Data flow: Fetches from cache → Processes data → Displays results

## Feature Details

### Exchange Comparison Display
Each exchange card shows:
- Exchange name (AI1, CI1, CI2, IC1, NC1, NC2)
- Ask Price and Bid Price
- Production Cost (inputs + workforce)
- Profit (Ask Price - Production Cost)
- ROI percentage
- Visual badges for "BEST ROI" and "SELECTED" exchange

**Visual Indicators:**
- Green border: Best ROI exchange
- Blue border: Currently selected exchange
- Color-coded profit/ROI: Green for positive, red for negative

### Arbitrage Opportunities Display
Each arbitrage card shows:
- Buy Exchange → Sell Exchange route
- Large profit percentage display
- Buy Price at source exchange
- Sell Price at destination exchange
- Profit per unit

**Filtering:**
- Only shows opportunities with >5% profit margin
- Displays top 5 most profitable routes
- Shows count of total opportunities found

## Data Flow

```
User selects Material + Recipe + Exchange
↓
calculate() function triggered
↓
getExchangeComparisonFromCache() → Processes allData cache
↓
displayExchangeComparison() → Renders exchange cards
↓
getArbitrageOpportunitiesFromCache() → Finds arbitrage routes
↓
displayArbitrageOpportunities() → Renders arbitrage cards
```

## Deployment Instructions

### Option 1: Google Apps Script Editor
1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI/
2. Go to **Extensions** → **Apps Script**
3. Replace **Code.gs** content with `AppsScript_PriceAnalyser.js`
4. Replace **Index.html** content with `AppsScript_Index.html`
5. Click **Deploy** → **Test deployments** to verify
6. Once confirmed working, click **Deploy** → **New deployment**
7. Set type: **Web app**
8. Execute as: **Me**
9. Who has access: **Anyone**
10. Click **Deploy** and copy the new URL

### Option 2: Update Existing Deployment
1. Open Apps Script editor
2. Replace both files as above
3. Click **Deploy** → **Manage deployments**
4. Click pencil icon next to current deployment
5. Change **Version** to "New version"
6. Add description: "Added exchange comparison and arbitrage detection"
7. Click **Deploy**
8. Copy the updated URL (if changed)

### Update GitHub Pages (if URL changed)
1. Open `index.html` in repository root
2. Find the iframe src URL
3. Replace with new deployment URL
4. Commit and push to GitHub

## Testing Checklist

- [ ] Select any material (e.g., DW)
- [ ] Select a recipe (e.g., FP:1xDW-1xH2O=>1xDW)
- [ ] Select an exchange (e.g., IC1)
- [ ] Click **Calculate**
- [ ] Verify **Exchange Comparison** section appears below recipe details
- [ ] Verify current exchange (IC1) has blue "SELECTED" badge
- [ ] Verify best ROI exchange has green "BEST ROI" badge
- [ ] Verify all exchanges show prices, costs, profit, and ROI
- [ ] Verify **Arbitrage Opportunities** section appears (if opportunities exist)
- [ ] Verify arbitrage cards show buy/sell exchanges with profit percentage
- [ ] Verify profit percentages are >5%
- [ ] Verify cards have hover effects (lift on hover)

## Technical Notes

- **Cache Usage**: Both features use client-side `allData` cache to avoid repeated server calls
- **Performance**: All calculations happen in browser after initial data load
- **Threshold**: 5% minimum profit margin for arbitrage to account for transfer costs
- **Sorting**: Exchanges sorted by ROI descending, arbitrage by profit percentage descending
- **Limit**: Shows top 5 arbitrage opportunities (prevents overwhelming UI)
- **Error Handling**: Sections hidden if no data available

## Example Output

### Exchange Comparison
```
┌─────────────────────────┐
│ AI1        [BEST ROI]   │
│ Ask: ₡ 1250.00          │
│ Bid: ₡ 1200.00          │
│ Cost: ₡ 950.00          │
│ Profit: ₡ 300.00        │
│ ROI: 31.58%             │
└─────────────────────────┘

┌─────────────────────────┐
│ IC1        [SELECTED]   │
│ Ask: ₡ 1180.00          │
│ Bid: ₡ 1150.00          │
│ Cost: ₡ 980.00          │
│ Profit: ₡ 200.00        │
│ ROI: 20.41%             │
└─────────────────────────┘
```

### Arbitrage Opportunities
```
┌──────────────────────────────┐
│ Buy at CI1 → Sell at AI1     │ +25.0%
│ Buy Price: ₡ 1000.00         │
│ Sell Price: ₡ 1250.00        │
│ Profit: ₡ 250.00             │
└──────────────────────────────┘
```

## Future Enhancement Ideas

- Add transportation cost calculator
- Show supply/demand levels for each exchange
- Add "Execute Arbitrage" button that tracks trades
- Historical arbitrage profitability chart
- Alert system for high-profit arbitrage opportunities (>20%)
- Multi-hop arbitrage detection (A→B→C)
- Market depth analysis (not just best ask/bid)

## Files Modified

- `AppsScript_PriceAnalyser.js`: Added 2 server-side functions (150 lines)
- `AppsScript_Index.html`: Added HTML sections, CSS styles, 4 JavaScript functions (250 lines)

## Commit Message

```
feat: Add exchange comparison and arbitrage detection to Price Analyser

- Added getExchangeComparison() to show ROI across all exchanges
- Added getArbitrageOpportunities() to detect profitable trade routes
- Implemented visual indicators for best/current exchange
- Added filtering for >5% profit margin arbitrage
- Enhanced UI with exchange cards and arbitrage cards
- Added hover effects and color-coded profit displays
```
