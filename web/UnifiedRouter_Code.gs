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
    const volumeIdx = headers.indexOf('Volume');
    
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
    
    for (const ticker in priceMap) {
      const material = priceMap[ticker];
      const originData = material.exchanges[originExchange];
      const destData = material.exchanges[destExchange];
      
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
    
    // Sort by total profit (descending)
    opportunities.sort((a, b) => b.totalProfit - a.totalProfit);
    
    return {
      opportunities: opportunities,
      count: opportunities.length,
      originExchange: originExchange,
      destExchange: destExchange,
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
      'Ticker', 'Name', 'Buy Price', 'Sell Price', 'Profit/Unit', 
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
      sheet.getRange(2, 3, rows.length, 2).setNumberFormat('#,##0.00'); // Prices
      sheet.getRange(2, 5, rows.length, 1).setNumberFormat('#,##0.00'); // Profit
      sheet.getRange(2, 6, rows.length, 1).setNumberFormat('#,##0.00"%"'); // ROI
      sheet.getRange(2, 7, rows.length, 4).setNumberFormat('#,##0'); // Volumes
      sheet.getRange(2, 10, rows.length, 1).setNumberFormat('#,##0.00'); // Total profit
      sheet.getRange(2, 13, rows.length, 2).setNumberFormat('#,##0'); // Traded volumes
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

// ==================== PRICE ANALYSER FUNCTIONS ====================
// (Keep all your existing Price Analyser functions below this line)
// Don't delete any of your existing functions!
