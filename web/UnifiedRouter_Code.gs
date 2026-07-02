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

function getVolumeColumnIndex(headers) {
  const candidates = [
    'Volume per Unit',
    'Volume_per_Unit',
    'Volume',
    'volume',
    'Volume (m3)',
    'Volume m3'
  ];
  for (const candidate of candidates) {
    const idx = headers.indexOf(candidate);
    if (idx !== -1) return idx;
  }
  return -1;
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
    const volumeIdx = getVolumeColumnIndex(headers);
    
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
            volume: volume,
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

function getTradeRouteShipProfiles() {
  return [
    { key: 'freighter', label: 'Freighter', speedFactor: 1.0, engineBurn: 1.0, cargoCapacity: 900, loadPenalty: 0.9, mixPenalty: 0.14, handlingPenalty: 0.04 },
    { key: 'runner', label: 'Runner', speedFactor: 0.78, engineBurn: 0.85, cargoCapacity: 420, loadPenalty: 0.65, mixPenalty: 0.10, handlingPenalty: 0.03 },
    { key: 'hauler', label: 'Heavy Hauler', speedFactor: 1.18, engineBurn: 1.15, cargoCapacity: 1500, loadPenalty: 1.20, mixPenalty: 0.18, handlingPenalty: 0.06 }
  ];
}

function getTradeRouteShipProfile(profileKey) {
  const profiles = getTradeRouteShipProfiles();
  return profiles.find(profile => profile.key === profileKey) || profiles[0];
}

function getTradeRouteExchangeIndex(code) {
  const order = ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2'];
  const idx = order.indexOf(code);
  return idx === -1 ? order.length : idx;
}

function calculateTradeRoute(originExchange, destinationExchange, materialsJson, routeMode, shipProfileKey) {
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
    const volumeIdx = getVolumeColumnIndex(headers);

    if (tickerIdx === -1 || exchangeIdx === -1 || askIdx === -1 || bidIdx === -1) {
      return { error: 'Required columns not found in Price Analyser Data' };
    }

    const profile = getTradeRouteShipProfile(String(shipProfileKey || 'freighter'));
    const priceMap = {};
    const exchangeSet = new Set();

    for (let i = 1; i < data.length; i++) {
      const ticker = String(data[i][tickerIdx] || '').trim();
      const exchange = String(data[i][exchangeIdx] || '').trim();
      if (!ticker || !exchange) continue;

      exchangeSet.add(exchange);

      if (!priceMap[ticker]) {
        priceMap[ticker] = {
          ticker: ticker,
          name: nameIdx !== -1 ? String(data[i][nameIdx] || ticker).trim() : ticker,
          exchanges: {}
        };
      }

      priceMap[ticker].exchanges[exchange] = {
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
    const routeModeKey = String(routeMode || 'efficiency');
    const routeBuckets = new Map();
    const missingMaterials = [];

    cargo.forEach(item => {
      const ticker = String(item.ticker || '').trim();
      const qty = Math.max(1, parseFloat(item.qty) || 1);
      if (!ticker) return;

      const material = priceMap[ticker];
      if (!material) {
        missingMaterials.push({ ticker: ticker, qty: qty, reason: 'No market data found' });
        return;
      }

      const availableOrigins = originList.filter(code => material.exchanges[code]);
      const availableDestinations = destinationList.filter(code => material.exchanges[code]);
      if (!availableOrigins.length || !availableDestinations.length) {
        missingMaterials.push({ ticker: ticker, qty: qty, reason: 'No matching origin or destination exchange' });
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
          const baseProfit = unitProfit * qty;
          const volumePerUnit = originData.volume || destData.volume || 0;
          const cargoVolume = volumePerUnit * qty;
          const routeKey = `${originCode}__${destCode}`;

          if (!routeBuckets.has(routeKey)) {
            routeBuckets.set(routeKey, {
              originExchange: originCode,
              destinationExchange: destCode,
              originLabel: getExchangeName(originCode),
              destinationLabel: getExchangeName(destCode),
              items: [],
              totalProfit: 0,
              totalVolume: 0,
              totalUnits: 0,
              itemCount: 0,
              transitIndex: 0,
              adjustedProfit: 0,
              routeScore: 0,
              routeMode: routeModeKey,
              shipProfile: profile
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
            adjustedProfit: baseProfit,
            transitCost: 0,
            supply: originData.supply || 0,
            demand: destData.demand || 0,
            traded: ((originData.traded || 0) + (destData.traded || 0)) / 2,
            volume: volumePerUnit,
            cargoVolume: cargoVolume
          });
          route.totalProfit += baseProfit;
          route.totalVolume += cargoVolume;
          route.totalUnits += qty;
          route.itemCount += 1;
        });
      });
    });

    const routes = Array.from(routeBuckets.values()).map(route => {
      const hubSpan = Math.abs(getTradeRouteExchangeIndex(route.originExchange) - getTradeRouteExchangeIndex(route.destinationExchange)) + 1;
      const loadRatio = profile.cargoCapacity > 0 ? (route.totalVolume / profile.cargoCapacity) : 0;
      const mixPenalty = Math.max(0, route.itemCount - 1) * profile.mixPenalty;
      const handlingPenalty = route.totalUnits * profile.handlingPenalty;
      const loadPenalty = loadRatio > 1 ? (loadRatio - 1) * profile.loadPenalty : loadRatio * (profile.loadPenalty * 0.25);
      const transitIndex = (hubSpan * profile.speedFactor) + profile.engineBurn + loadPenalty + mixPenalty + handlingPenalty;
      const adjustedProfit = route.totalProfit - (transitIndex * 1000);
      const efficiencyScore = route.totalProfit / (1 + transitIndex);

      route.transitIndex = transitIndex;
      route.adjustedProfit = adjustedProfit;
      route.routeScore = routeModeKey === 'point_to_point' ? adjustedProfit : efficiencyScore;
      route.items = route.items.map(item => ({
        ticker: item.ticker,
        name: item.name,
        qty: item.qty,
        buyExchange: item.buyExchange,
        sellExchange: item.sellExchange,
        buyPrice: item.buyPrice,
        sellPrice: item.sellPrice,
        unitProfit: item.unitProfit,
        adjustedProfit: item.adjustedProfit,
        transitCost: transitIndex,
        supply: item.supply,
        demand: item.demand,
        traded: item.traded,
        volume: item.volume,
        cargoVolume: item.cargoVolume
      }));
      return route;
    }).sort((a, b) => b.routeScore - a.routeScore);

    return {
      routeMode: routeModeKey,
      shipProfile: profile,
      originExchange: originExchange || 'ALL',
      destinationExchange: destinationExchange || 'ALL',
      routeCount: routes.length,
      bestRoute: routes[0] || null,
      routes: routes.slice(0, 10),
      missingMaterials: missingMaterials,
      note: 'Abstract transit uses ship profile, cargo load, route complexity, and hub separation. Real distance data can plug in later.'
    };
  } catch (error) {
    return { error: error.toString() };
  }
}

// ==================== PRICE ANALYSER FUNCTIONS ====================
// (Keep all your existing Price Analyser functions below this line)
// Don't delete any of your existing functions!
