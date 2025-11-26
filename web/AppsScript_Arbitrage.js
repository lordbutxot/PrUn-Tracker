// ====================================================================
// GOOGLE APPS SCRIPT - ARBITRAGE OPPORTUNITIES WEB APP
// ====================================================================
// 
// FEATURES:
// - 🔄 Real-time arbitrage calculation using Google Sheets data
// - 📊 Interactive table with sorting and filtering
// - 📱 Mobile responsive design
// - 🎯 Opportunity level classification (Very High/High/Medium/Low/Very Low)
// - 💰 Profit and ROI calculations
// - 🔍 Advanced filtering by material, exchanges, profit, and ROI
//
// DEPLOYMENT INSTRUCTIONS:
// 1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI/edit
// 2. Go to: Extensions → Apps Script
// 3. Create a new script file named "ArbitrageApp"
// 4. Delete any existing code and paste ALL this code
// 5. Click "Deploy" → "New deployment"
// 6. Select type: "Web app"
// 7. Settings:
//    - Description: "Arbitrage Opportunities Tool"
//    - Execute as: "Me"
//    - Who has access: "Anyone"
// 8. Click "Deploy"
// 9. Copy the Web App URL (ends with /exec)
// 10. Replace the iframe src in index.html with this URL
//
// DATA REQUIREMENTS:
// - Orders sheet (MaterialTicker, ExchangeCode, ItemCount, ItemCost columns)
// - Bids sheet (MaterialTicker, ExchangeCode, ItemCount, ItemCost columns)
// - Market Data sheet (for material names and additional info)
//
// ====================================================================

// Main function to serve the HTML page
function doGet(e) {
  // Check if this is an API request
  if (e.parameter.action === 'getArbitrageData') {
    return getArbitrageDataAPI();
  }

  // Otherwise serve the HTML page
  return HtmlService.createHtmlOutputFromFile('ArbitrageIndex')
    .setTitle('PrUn Arbitrage Opportunities')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .setContent(getHtmlWithData());
}

// API endpoint for arbitrage data
function getArbitrageDataAPI() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    // Get orders (sell orders/asks)
    const ordersSheet = ss.getSheetByName('Orders');
    if (!ordersSheet) {
      return ContentService
        .createTextOutput(JSON.stringify({ error: 'Orders sheet not found' }))
        .setMimeType(ContentService.MimeType.JSON)
        .setHeaders({'Access-Control-Allow-Origin': '*'});
    }
    const ordersData = ordersSheet.getDataRange().getValues();

    // Get bids (buy orders)
    const bidsSheet = ss.getSheetByName('Bids');
    if (!bidsSheet) {
      return ContentService
        .createTextOutput(JSON.stringify({ error: 'Bids sheet not found' }))
        .setMimeType(ContentService.MimeType.JSON)
        .setHeaders({'Access-Control-Allow-Origin': '*'});
    }
    const bidsData = bidsSheet.getDataRange().getValues();

    // Get market data for material names
    const marketSheet = ss.getSheetByName('Market Data');
    const marketData = marketSheet ? marketSheet.getDataRange().getValues() : [];

    // Process the data
    const arbitrageOpportunities = computeArbitrageOpportunities(ordersData, bidsData, marketData);

    const response = {
      success: true,
      data: arbitrageOpportunities,
      timestamp: new Date().toISOString(),
      totalOpportunities: arbitrageOpportunities.length
    };

    return ContentService
      .createTextOutput(JSON.stringify(response))
      .setMimeType(ContentService.MimeType.JSON)
      .setHeaders({'Access-Control-Allow-Origin': '*'});

  } catch (error) {
    const errorResponse = {
      error: error.toString(),
      timestamp: new Date().toISOString()
    };

    return ContentService
      .createTextOutput(JSON.stringify(errorResponse))
      .setMimeType(ContentService.MimeType.JSON)
      .setHeaders({'Access-Control-Allow-Origin': '*'});
  }
}

// Get arbitrage data from Google Sheets
function getArbitrageData() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    // Get orders (sell orders/asks)
    const ordersSheet = ss.getSheetByName('Orders');
    if (!ordersSheet) {
      return { error: 'Orders sheet not found' };
    }
    const ordersData = ordersSheet.getDataRange().getValues();

    // Get bids (buy orders)
    const bidsSheet = ss.getSheetByName('Bids');
    if (!bidsSheet) {
      return { error: 'Bids sheet not found' };
    }
    const bidsData = bidsSheet.getDataRange().getValues();

    // Get market data for material names
    const marketSheet = ss.getSheetByName('Market Data');
    const marketData = marketSheet ? marketSheet.getDataRange().getValues() : [];

    // Process the data
    const arbitrageOpportunities = computeArbitrageOpportunities(ordersData, bidsData, marketData);

    return {
      success: true,
      data: arbitrageOpportunities,
      timestamp: new Date().toISOString()
    };

  } catch (error) {
    return {
      error: error.toString(),
      timestamp: new Date().toISOString()
    };
  }
}

// Compute arbitrage opportunities using order book crossing
function computeArbitrageOpportunities(ordersData, bidsData, marketData) {
  const arbitrageRows = [];
  const exchanges = ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2'];
  const tickers = new Set();

  // Collect all unique tickers
  ordersData.slice(1).forEach(row => {
    if (row[0]) tickers.add(row[0]); // MaterialTicker
  });
  bidsData.slice(1).forEach(row => {
    if (row[0]) tickers.add(row[0]); // MaterialTicker
  });

  // Create material name lookup
  const materialNames = {};
  if (marketData.length > 0) {
    marketData.slice(1).forEach(row => {
      if (row[0] && row[1]) { // Ticker and Material Name
        materialNames[row[0]] = row[1];
      }
    });
  }

  for (const ticker of tickers) {
    for (const buyEx of exchanges) {
      for (const sellEx of exchanges) {
        if (buyEx === sellEx) continue;

        const size = computeArbitrageOpportunitySize(ticker, buyEx, sellEx, ordersData, bidsData);
        if (size.matchedQty > 0 && size.matches.length > 0) {
          const totalBuy = size.matches.reduce((sum, match) => sum + (match.askPrice * match.qty), 0);
          const totalSell = size.matches.reduce((sum, match) => sum + (match.bidPrice * match.qty), 0);
          const avgBuy = totalBuy / size.matchedQty;
          const avgSell = totalSell / size.matchedQty;
          const profitPerUnit = size.totalProfit / size.matchedQty;
          const roi = avgBuy > 0 ? (profitPerUnit / avgBuy) * 100 : 0;

          const name = materialNames[ticker] || ticker;

          arbitrageRows.push({
            ticker: ticker,
            name: name,
            product: ticker,
            buy_exchange: buyEx,
            sell_exchange: sellEx,
            buy_price: Number(avgBuy.toFixed(2)),
            sell_price: Number(avgSell.toFixed(2)),
            profit: Number(profitPerUnit.toFixed(2)),
            roi: Number(roi.toFixed(4)),
            size: Math.floor(size.matchedQty),
            level: null // Will be assigned later
          });
        }
      }
    }
  }

  // Assign opportunity levels
  const opportunitiesWithLevels = assignOpportunityLevels(arbitrageRows);

  // Sort by profit descending
  return opportunitiesWithLevels.sort((a, b) => b.profit - a.profit);
}

// Compute arbitrage opportunity size for specific ticker and exchanges
function computeArbitrageOpportunitySize(ticker, buyEx, sellEx, ordersData, bidsData) {
  // Get asks from buy exchange (where you buy) - sorted by price ascending
  const asks = ordersData
    .slice(1) // Skip header
    .filter(row => row[0] === ticker && row[1] === buyEx) // MaterialTicker, ExchangeCode
    .map(row => ({
      price: parseFloat(row[3]), // ItemCost
      quantity: parseInt(row[2]) // ItemCount
    }))
    .sort((a, b) => a.price - b.price);

  // Get bids from sell exchange (where you sell) - sorted by price descending
  const bids = bidsData
    .slice(1) // Skip header
    .filter(row => row[0] === ticker && row[1] === sellEx) // MaterialTicker, ExchangeCode
    .map(row => ({
      price: parseFloat(row[3]), // ItemCost
      quantity: parseInt(row[2]) // ItemCount
    }))
    .sort((a, b) => b.price - a.price);

  let askIdx = 0;
  let bidIdx = 0;
  let matchedQty = 0;
  let totalProfit = 0;
  const matches = [];

  while (askIdx < asks.length && bidIdx < bids.length) {
    const askPrice = asks[askIdx].price;
    const askQty = asks[askIdx].quantity;
    const bidPrice = bids[bidIdx].price;
    const bidQty = bids[bidIdx].quantity;

    if (bidPrice >= askPrice) {
      const qty = Math.min(askQty, bidQty);
      const profit = (bidPrice - askPrice) * qty;

      matches.push({
        askPrice: askPrice,
        bidPrice: bidPrice,
        qty: qty
      });

      matchedQty += qty;
      totalProfit += profit;

      // Update quantities
      asks[askIdx].quantity -= qty;
      bids[bidIdx].quantity -= qty;

      if (asks[askIdx].quantity <= 0) askIdx++;
      if (bids[bidIdx].quantity <= 0) bidIdx++;
    } else {
      break;
    }
  }

  return {
    matchedQty: matchedQty,
    totalProfit: totalProfit,
    matches: matches
  };
}

// Assign opportunity levels based on ROI and size
function assignOpportunityLevels(arbitrageData) {
  return arbitrageData.map(item => {
    const roi = item.roi;
    const size = item.size;

    let level = 'Very Low';
    if (roi > 100 && size >= 1000) {
      level = 'Very High';
    } else if (roi > 50 && size >= 500) {
      level = 'High';
    } else if (roi > 20 && size >= 100) {
      level = 'Medium';
    } else if (roi > 5 && size >= 10) {
      level = 'Low';
    }

    return { ...item, level: level };
  });
}