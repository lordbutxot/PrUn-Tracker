// ====================================================================
// GOOGLE APPS SCRIPT - UNIFIED ROUTER FOR MULTIPLE APPS
// ====================================================================
// 
// This file replaces your existing Code.gs and adds routing support
// for multiple web apps in a single project.
//
// APPS:
// - Price Analyser (default, ?page=priceanalyser or no parameter)
// - Arbitrage Calculator (?page=arbitrage)
//
// SETUP INSTRUCTIONS:
// 1. Open your existing Apps Script project
// 2. Replace Code.gs content with this file
// 3. Add ArbitrageCalculator.html to your project
// 4. Keep your existing Index.html (Price Analyser)
// 5. Redeploy (Deploy → Manage deployments → Edit → New version)
//
// URLS:
// - Price Analyser: https://script.google.com/.../exec
// - Arbitrage: https://script.google.com/.../exec?page=arbitrage
//
// ====================================================================

// ==================== ROUTER ====================

function doGet(e) {
  const page = e.parameter.page || 'priceanalyser';
  
  let htmlFile, title;
  
  switch(page.toLowerCase()) {
    case 'arbitrage':
      htmlFile = 'ArbitrageCalculator';
      title = 'PrUn Arbitrage Calculator';
      break;
    case 'traderoute':
    case 'trade-route':
      htmlFile = 'TradeRouteCalculator';
      title = 'PrUn Trade Route Planner';
      break;
    case 'priceanalyser':
    case 'price':
    default:
      htmlFile = 'Index';
      title = 'PrUn Price Analyser';
      break;
  }
  
  return HtmlService.createHtmlOutputFromFile(htmlFile)
    .setTitle(title)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ==================== ARBITRAGE CALCULATOR FUNCTIONS ====================

function getExchanges() {
  return ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2'];
}

function getExchangeName(code) {
  const names = {
    'AI1': 'Antares (AI1)',
    'CI1': 'Katoa (CI1)',
    'CI2': 'Vallis (CI2)',
    'IC1': 'Moria (IC1)',
    'NC1': 'Montem (NC1)',
    'NC2': 'Hubur (NC2)'
  };
  return names[code] || code;
}

function calculateArbitrage(originExchange, destExchange, minProfit, minROI, transportCostPerUnit) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return { error: 'Price Analyser Data sheet not found' };
    }
    
    const data = sheet.getDataRange().getValues();
    const headers = data[0];
    
    // Find column indices
    const tickerIdx = headers.indexOf('Ticker');
    const nameIdx = headers.indexOf('Name');
    const exchangeIdx = headers.indexOf('Exchange');
    const askIdx = headers.indexOf('Ask Price');
    const bidIdx = headers.indexOf('Bid Price');
    const supplyIdx = headers.indexOf('Supply');
    const demandIdx = headers.indexOf('Demand');
    const tradedIdx = headers.indexOf('Traded Volume');
    const volumeIdx = headers.indexOf('Volume per Unit') !== -1 ? headers.indexOf('Volume per Unit') : headers.indexOf('Volume');
    
    if (tickerIdx === -1 || exchangeIdx === -1) {
      return { error: 'Required columns not found' };
    }
    
    // Parse parameters
    const minProfitValue = parseFloat(minProfit) || 0;
    const minROIValue = parseFloat(minROI) || 0;
    const transportCost = parseFloat(transportCostPerUnit) || 0;
    
    // Group data by ticker and exchange
    const priceMap = {};
    
    for (let i = 1; i < data.length; i++) {
      const ticker = data[i][tickerIdx];
      const name = data[i][nameIdx] || ticker;
      const exchange = data[i][exchangeIdx];
      const askPrice = parseFloat(data[i][askIdx]) || 0;
      const bidPrice = parseFloat(data[i][bidIdx]) || 0;
      const supply = parseFloat(data[i][supplyIdx]) || 0;
      const demand = parseFloat(data[i][demandIdx]) || 0;
      const traded = parseFloat(data[i][tradedIdx]) || 0;
      const volume = volumeIdx !== -1 ? (parseFloat(data[i][volumeIdx]) || 0) : 0;
      
      if (!ticker || !exchange) continue;
      
      if (!priceMap[ticker]) {
        priceMap[ticker] = {
          name: name,
          exchanges: {}
        };
      }
      
      priceMap[ticker].exchanges[exchange] = {
        askPrice: askPrice,
        bidPrice: bidPrice,
        supply: supply,
        demand: demand,
        traded: traded,
        volume: volume
      };
    }
    
    // Calculate arbitrage opportunities
    const opportunities = [];
    const uniqueExchanges = Array.from(new Set(
      Object.values(priceMap).flatMap(material => Object.keys(material.exchanges))
    )).filter(Boolean);
    const originList = originExchange ? [originExchange] : uniqueExchanges;
    const destList = destExchange ? [destExchange] : uniqueExchanges;
    const allMode = !originExchange || !destExchange;
    
    for (const ticker in priceMap) {
      const material = priceMap[ticker];
      
      for (const originCode of originList) {
        for (const destCode of destList) {
          if (originCode === destCode) continue;
          
          const originData = material.exchanges[originCode];
          const destData = material.exchanges[destCode];
          if (!originData || !destData) continue;
          
          // Buy at origin Ask price, sell at destination Bid price
          const buyPrice = originData.askPrice;
          const sellPrice = destData.bidPrice;
          if (buyPrice <= 0 || sellPrice <= 0) continue;
          
          // Calculate profit per unit (including transport cost)
          const profit = sellPrice - buyPrice - transportCost;
          const volume = originData.volume || destData.volume || 0;
          const profitPerM3 = volume > 0 ? profit / volume : 0;
          
          if (profit <= minProfitValue) continue;
          
          // Calculate ROI
          const roi = (profit / (buyPrice + transportCost)) * 100;
          if (roi < minROIValue) continue;
          
          // Calculate opportunity size (limited by supply at origin and demand at destination)
          const maxVolume = Math.min(originData.supply, destData.demand);
          const totalProfit = profit * maxVolume;
          
          // Calculate opportunity level
          let opportunityLevel = 'Low';
          if (totalProfit >= 100000) opportunityLevel = 'Very High';
          else if (totalProfit >= 50000) opportunityLevel = 'High';
          else if (totalProfit >= 10000) opportunityLevel = 'Medium';
          
          // Calculate liquidity score (based on traded volume)
          const avgTraded = (originData.traded + destData.traded) / 2;
          let liquidityLevel = 'Low';
          if (avgTraded >= 1000) liquidityLevel = 'High';
          else if (avgTraded >= 100) liquidityLevel = 'Medium';
          
          opportunities.push({
            ticker: ticker,
            name: material.name,
            buyExchange: originCode,
            sellExchange: destCode,
            buyPrice: buyPrice,
            sellPrice: sellPrice,
            profit: profit,
            profitPerM3: profitPerM3,
            roi: roi,
            supply: originData.supply,
            demand: destData.demand,
            maxVolume: maxVolume,
            totalProfit: totalProfit,
            opportunityLevel: opportunityLevel,
            liquidityLevel: liquidityLevel,
            originTraded: originData.traded,
            destTraded: destData.traded,
            avgTraded: avgTraded
          });
        }
      }
    }
    
    // Sort by total profit (descending)
    opportunities.sort((a, b) => b.totalProfit - a.totalProfit);
    
    return {
      opportunities: opportunities,
      count: opportunities.length,
      originExchange: originExchange || (allMode ? 'ALL' : originExchange),
      destExchange: destExchange || (allMode ? 'ALL' : destExchange),
      transportCost: transportCost
    };
    
  } catch (error) {
    return { error: error.toString() };
  }
}

function getMetadata() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Metadata');
    
    if (!sheet) {
      return { lastUpdate: 'Unknown' };
    }
    
    const data = sheet.getDataRange().getValues();
    const metadata = {};
    
    for (let i = 0; i < data.length; i++) {
      const key = data[i][0];
      const value = data[i][1];
      if (key) {
        metadata[key] = value;
      }
    }
    
    return metadata;
    
  } catch (error) {
    return { error: error.toString() };
  }
}

function getArbitrageSummary(originExchange, destExchange) {
  const result = calculateArbitrage(originExchange, destExchange, 0, 0, 0);
  
  if (result.error) {
    return result;
  }
  
  const opportunities = result.opportunities;
  
  if (opportunities.length === 0) {
    return {
      count: 0,
      totalPotentialProfit: 0,
      avgROI: 0,
      topOpportunity: null
    };
  }
  
  const totalPotentialProfit = opportunities.reduce((sum, opp) => sum + opp.totalProfit, 0);
  const avgROI = opportunities.reduce((sum, opp) => sum + opp.roi, 0) / opportunities.length;
  
  return {
    count: opportunities.length,
    totalPotentialProfit: totalPotentialProfit,
    avgROI: avgROI,
    topOpportunity: opportunities[0]
  };
}

function exportArbitrageToSheet(originExchange, destExchange, minProfit, minROI, transportCost) {
  try {
    const result = calculateArbitrage(originExchange, destExchange, minProfit, minROI, transportCost);
    
    if (result.error) {
      return { error: result.error };
    }
    
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheetName = `Arbitrage ${originExchange}-${destExchange}`;
    
    // Delete existing sheet if it exists
    let sheet = ss.getSheetByName(sheetName);
    if (sheet) {
      ss.deleteSheet(sheet);
    }
    
    // Create new sheet
    sheet = ss.insertSheet(sheetName);
    
    // Add headers
    const headers = [
      'Ticker', 'Name', 'Buy Exchange', 'Sell Exchange', 'Buy Price', 'Sell Price', 'Profit/Unit', 
      'ROI %', 'Supply', 'Demand', 'Max Volume', 'Total Profit',
      'Opportunity Level', 'Liquidity', 'Origin Traded', 'Dest Traded'
    ];
    
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.getRange(1, 1, 1, headers.length).setBackground('#1e40af');
    sheet.getRange(1, 1, 1, headers.length).setFontColor('#ffffff');
    
    // Add data
    const rows = result.opportunities.map(opp => [
      opp.ticker,
      opp.name,
      opp.buyExchange || originExchange,
      opp.sellExchange || destExchange,
      opp.buyPrice,
      opp.sellPrice,
      opp.profit,
      opp.roi,
      opp.supply,
      opp.demand,
      opp.maxVolume,
      opp.totalProfit,
      opp.opportunityLevel,
      opp.liquidityLevel,
      opp.originTraded,
      opp.destTraded
    ]);
    
    if (rows.length > 0) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      
      // Format numbers
      sheet.getRange(2, 5, rows.length, 2).setNumberFormat('#,##0.00'); // Prices
      sheet.getRange(2, 7, rows.length, 1).setNumberFormat('#,##0.00'); // Profit
      sheet.getRange(2, 8, rows.length, 1).setNumberFormat('#,##0.00"%"'); // ROI
      sheet.getRange(2, 9, rows.length, 4).setNumberFormat('#,##0'); // Volumes
      sheet.getRange(2, 12, rows.length, 1).setNumberFormat('#,##0.00'); // Total profit
      sheet.getRange(2, 15, rows.length, 2).setNumberFormat('#,##0'); // Traded volumes
    }
    
    // Auto-resize columns
    sheet.autoResizeColumns(1, headers.length);
    
    // Freeze header row
    sheet.setFrozenRows(1);
    
    return { 
      success: true, 
      sheetName: sheetName,
      rowCount: rows.length 
    };
    
  } catch (error) {
    return { error: error.toString() };
  }
}

function getTradeRouteMaterials(query) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    if (!sheet) {
      return [];
    }

    const data = sheet.getDataRange().getValues();
    if (!data || data.length < 2) {
      return [];
    }

    const headers = data[0].map(String);
    const tickerIdx = headers.indexOf('Ticker');
    const nameIdx = headers.indexOf('Material Name') !== -1 ? headers.indexOf('Material Name') : headers.indexOf('Name');

    const term = String(query || '').trim().toLowerCase();
    const seen = new Set();
    const materials = [];

    for (let i = 1; i < data.length; i++) {
      const ticker = String(data[i][tickerIdx] || '').trim();
      if (!ticker || seen.has(ticker)) continue;
      const name = nameIdx !== -1 ? String(data[i][nameIdx] || ticker).trim() : ticker;
      const label = `${ticker} - ${name}`;
      if (term && !label.toLowerCase().includes(term) && !ticker.toLowerCase().includes(term) && !name.toLowerCase().includes(term)) {
        continue;
      }
      seen.add(ticker);
      materials.push({
        ticker,
        name,
        label
      });
      if (materials.length >= 100) {
        break;
      }
    }

    return materials.sort((a, b) => a.label.localeCompare(b.label));
  } catch (error) {
    return [];
  }
}

function getTradeRouteExchanges() {
  try {
    return getExchanges().map(code => ({
      code: code,
      label: getExchangeName(code)
    }));
  } catch (error) {
    return [];
  }
}

function calculateTradeRoute(originExchange, destinationExchange, materialsJson, routeMode) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    if (!sheet) {
      return { error: 'Price Analyser Data sheet not found' };
    }

    const cargo = Array.isArray(materialsJson) ? materialsJson : JSON.parse(materialsJson || '[]');
    if (!cargo.length) {
      return { error: 'Add at least one material to build a route' };
    }

    const data = sheet.getDataRange().getValues();
    if (!data || data.length < 2) {
      return { error: 'Price Analyser Data is empty' };
    }

    const headers = data[0];
    const tickerIdx = headers.indexOf('Ticker');
    const nameIdx = headers.indexOf('Material Name') !== -1 ? headers.indexOf('Material Name') : headers.indexOf('Name');
    const exchangeIdx = headers.indexOf('Exchange');
    const askIdx = headers.indexOf('Ask Price');
    const bidIdx = headers.indexOf('Bid Price');
    const supplyIdx = headers.indexOf('Supply');
    const demandIdx = headers.indexOf('Demand');
    const tradedIdx = headers.indexOf('Traded Volume');
    const volumeIdx = headers.indexOf('Volume per Unit') !== -1 ? headers.indexOf('Volume per Unit') : headers.indexOf('Volume');

    if (tickerIdx === -1 || exchangeIdx === -1 || askIdx === -1 || bidIdx === -1) {
      return { error: 'Required columns not found in Price Analyser Data' };
    }

    const marketMap = {};
    const exchangeSet = new Set();

    for (let i = 1; i < data.length; i++) {
      const ticker = String(data[i][tickerIdx] || '').trim();
      const exchange = String(data[i][exchangeIdx] || '').trim();
      if (!ticker || !exchange) continue;

      exchangeSet.add(exchange);

      if (!marketMap[ticker]) {
        marketMap[ticker] = {
          ticker: ticker,
          name: nameIdx !== -1 ? String(data[i][nameIdx] || ticker).trim() : ticker,
          exchanges: {}
        };
      }

      marketMap[ticker].exchanges[exchange] = {
        askPrice: parseFloat(data[i][askIdx]) || 0,
        bidPrice: parseFloat(data[i][bidIdx]) || 0,
        supply: parseFloat(data[i][supplyIdx]) || 0,
        demand: parseFloat(data[i][demandIdx]) || 0,
        traded: parseFloat(data[i][tradedIdx]) || 0,
        volume: volumeIdx !== -1 ? (parseFloat(data[i][volumeIdx]) || 0) : 0
      };
    }

    const originList = originExchange ? [originExchange] : Array.from(exchangeSet);
    const destinationList = destinationExchange ? [destinationExchange] : Array.from(exchangeSet);
    const mode = String(routeMode || 'shortest_profit');
    const routeBuckets = new Map();
    const missingMaterials = [];

    cargo.forEach(item => {
      const ticker = String(item.ticker || '').trim();
      const qty = Math.max(1, parseFloat(item.qty) || 1);
      if (!ticker) return;

      const material = marketMap[ticker];
      if (!material) {
        missingMaterials.push({ ticker, qty, reason: 'No market data found' });
        return;
      }

      const availableOrigins = originList.filter(code => material.exchanges[code]);
      const availableDestinations = destinationList.filter(code => material.exchanges[code]);

      if (!availableOrigins.length || !availableDestinations.length) {
        missingMaterials.push({
          ticker: ticker,
          qty: qty,
          reason: 'No matching origin/destination exchange for this material'
        });
        return;
      }

      availableOrigins.forEach(originCode => {
        availableDestinations.forEach(destCode => {
          if (originCode === destCode) return;

          const originData = material.exchanges[originCode];
          const destData = material.exchanges[destCode];
          const buyPrice = originData.askPrice;
          const sellPrice = destData.bidPrice;
          if (buyPrice <= 0 || sellPrice <= 0) return;

          const unitProfit = sellPrice - buyPrice;
          const totalCost = buyPrice * qty;
          const totalRevenue = sellPrice * qty;
          const totalProfit = unitProfit * qty;
          const roi = totalCost > 0 ? (totalProfit / totalCost) * 100 : 0;
          const liquidity = Math.min(originData.supply || qty, destData.demand || qty, qty);
          const routeKey = `${originCode}__${destCode}`;

          if (!routeBuckets.has(routeKey)) {
            routeBuckets.set(routeKey, {
              originExchange: originCode,
              destinationExchange: destCode,
              routeMode: mode,
              items: [],
              totalUnits: 0,
              totalCost: 0,
              totalRevenue: 0,
              totalProfit: 0,
              avgROI: 0,
              routeScore: 0,
              liquidityScore: 0,
              distanceKm: null,
              distanceLabel: 'Distance matrix pending'
            });
          }

          const route = routeBuckets.get(routeKey);
          route.items.push({
            ticker: ticker,
            name: material.name,
            qty: qty,
            buyExchange: originCode,
            sellExchange: destCode,
            buyPrice: buyPrice,
            sellPrice: sellPrice,
            unitProfit: unitProfit,
            totalProfit: totalProfit,
            roi: roi,
            supply: originData.supply || 0,
            demand: destData.demand || 0,
            traded: ((originData.traded || 0) + (destData.traded || 0)) / 2,
            volume: originData.volume || destData.volume || 0,
            liquidity: liquidity
          });
          route.totalUnits += qty;
          route.totalCost += totalCost;
          route.totalRevenue += totalRevenue;
          route.totalProfit += totalProfit;
          route.liquidityScore += liquidity;
        });
      });
    });

    const routes = Array.from(routeBuckets.values()).map(route => {
      route.items.sort((a, b) => b.totalProfit - a.totalProfit);
      route.avgROI = route.totalCost > 0 ? (route.totalProfit / route.totalCost) * 100 : 0;
      route.routeScore = mode === 'point_to_point'
        ? route.totalProfit
        : route.totalProfit + (route.liquidityScore * 5);
      route.itemCount = route.items.length;
      route.originLabel = getExchangeName(route.originExchange);
      route.destinationLabel = getExchangeName(route.destinationExchange);
      return route;
    }).sort((a, b) => {
      if (b.routeScore !== a.routeScore) return b.routeScore - a.routeScore;
      return b.totalProfit - a.totalProfit;
    });

    return {
      routeMode: mode,
      originExchange: originExchange || 'ALL',
      destinationExchange: destinationExchange || 'ALL',
      routeCount: routes.length,
      bestRoute: routes[0] || null,
      routes: routes.slice(0, 10),
      missingMaterials: missingMaterials,
      note: 'Profit ranking is active; distance weighting will plug into this engine once the map data is available.'
    };
  } catch (error) {
    return { error: error.toString() };
  }
}

// ==================== PRICE ANALYSER FUNCTIONS ====================
// (Keep all your existing Price Analyser functions below this line)
// Don't delete any of your existing functions!
