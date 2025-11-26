# PrUn Arbitrage App

A dedicated web application for identifying and analyzing cross-exchange arbitrage opportunities in Prosperous Universe (PrUn).

## Features

- **Real-time Arbitrage Detection**: Automatically scans all exchanges for profitable arbitrage opportunities
- **Advanced Filtering**: Filter by material, buy/sell exchanges, minimum profit, and ROI
- **Interactive Table**: Sortable table with detailed arbitrage information
- **Statistics Dashboard**: Overview of total opportunities, average profit, ROI, and trading volume
- **Mobile Responsive**: Optimized for both desktop and mobile devices
- **Opportunity Levels**: Color-coded opportunity levels (Very High, High, Medium, Low, Very Low)

## How It Works

The app uses the same arbitrage calculation logic as the Python scripts:

1. **Order Book Analysis**: Compares ask prices (sell orders) on one exchange with bid prices (buy orders) on another
2. **Cross-Exchange Matching**: Finds profitable opportunities where you can buy low on one exchange and sell high on another
3. **Profit Calculation**: Calculates profit per unit and return on investment (ROI)
4. **Opportunity Sizing**: Determines the maximum tradeable quantity for each opportunity

## Data Sources

The app loads data from:
- `orders.csv` - Sell orders (asks) from all exchanges
- `bids.csv` - Buy orders (bids) from all exchanges
- `market_data.csv` - Aggregated market data with prices and availability

## Usage

### Running the App

1. Start the data server:
   ```bash
   python serve_cache.py
   ```

2. Open `arbitrage_app.html` in your web browser

3. The app will automatically load and analyze arbitrage opportunities

### Filtering Opportunities

- **Material**: Select specific materials to focus on
- **Buy Exchange**: Filter by where you want to buy
- **Sell Exchange**: Filter by where you want to sell
- **Min Profit**: Only show opportunities with profit above this threshold
- **Min ROI**: Only show opportunities with ROI percentage above this threshold

### Understanding the Results

- **Buy/Sell Price**: Average prices for the arbitrage opportunity
- **Profit**: Profit per unit
- **ROI**: Return on investment percentage
- **Size**: Maximum tradeable quantity
- **Level**: Opportunity classification based on profit and size

## Opportunity Levels

- **Very High**: ROI > 100% and Size >= 1000
- **High**: ROI > 50% and Size >= 500
- **Medium**: ROI > 20% and Size >= 100
- **Low**: ROI > 5% and Size >= 10
- **Very Low**: All other opportunities

## Technical Details

### Algorithm

The arbitrage detection uses an order book crossing algorithm:

1. Sort ask orders (sell) by price ascending on buy exchange
2. Sort bid orders (buy) by price descending on sell exchange
3. Match orders where bid price >= ask price
4. Calculate total profit and tradeable volume

### Data Processing

- CSV parsing for order book data
- Real-time calculation of arbitrage opportunities
- Client-side filtering and sorting for responsive UI

## Dependencies

- Modern web browser with JavaScript enabled
- Python 3.x for the data server
- Access to PrUn Tracker cache files

## Files

- `arbitrage_app.html` - Main web application
- `arbitrage_calculator.js` - Arbitrage calculation engine
- `serve_cache.py` - HTTP server for cache files

## Integration Options

### Option 1: Standalone App (Current Setup)
- **Files**: `arbitrage_app.html`, `arbitrage_calculator.js`
- **Data Source**: Local CSV files via Python server
- **Deployment**: Run `python serve_cache.py` and open `arbitrage_app.html`
- **Pros**: Fast, independent, works offline
- **Cons**: Requires Python server, manual data updates

### Option 2: Integrated Modal (Recommended for Personal Use)
- **Files**: Updated `index.html` with arbitrage modal
- **Data Source**: Local CSV files via Python server
- **Deployment**: Already integrated into main site - just click "Arbitrage Opportunities"
- **Pros**: Seamless user experience, consistent UI
- **Cons**: Requires Python server

### Option 3: Google Apps Script Integration (Most Integrated)
- **Files**: `web/AppsScript_Arbitrage.js`, `web/AppsScript_Arbitrage_Index.html`
- **Data Source**: Live Google Sheets data
- **Deployment**: Deploy as Google Apps Script web app
- **Pros**: Real-time data, no server needed, fully integrated
- **Cons**: Requires Google Apps Script deployment

## Google Apps Script Deployment

1. **Open your Google Sheet**
2. **Go to Extensions → Apps Script**
3. **Create new script file named "ArbitrageApp"**
4. **Paste the code from `web/AppsScript_Arbitrage.js`**
5. **Create HTML file named "ArbitrageIndex"**
6. **Paste the HTML from `web/AppsScript_Arbitrage_Index.html`**
7. **Click "Deploy" → "New deployment"**
8. **Select type "Web app"**
9. **Settings:**
   - Description: "Arbitrage Opportunities Tool"
   - Execute as: "Me"
   - Who has access: "Anyone"
10. **Deploy and copy the web app URL**
11. **Update `index.html` arbitrage modal iframe src with the new URL**

## Data Requirements

### For Standalone/Google Apps Script Versions:
- **Orders sheet/CSV**: MaterialTicker, ExchangeCode, ItemCount, ItemCost columns
- **Bids sheet/CSV**: Same structure for buy orders
- **Market Data sheet/CSV**: Material names and pricing information

## Deployment Recommendations

- **Personal Use**: Use the Integrated Modal (already set up)
- **Team Use**: Use Google Apps Script version for real-time collaboration
- **Development**: Use Standalone App for easy testing and modification