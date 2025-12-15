// ====================================================================
// GOOGLE APPS SCRIPT - ARBITRAGE CALCULATOR (STANDALONE)
// ====================================================================
// 
// This is a minimal standalone deployment for the Arbitrage Calculator.
// Use this when you want a separate Apps Script project just for arbitrage.
//
// DEPLOYMENT INSTRUCTIONS:
// 1. Open your Google Sheet
// 2. Go to: Extensions → Apps Script
// 3. Click the project dropdown (top left) → New Project
// 4. Name it: "PrUn Arbitrage Calculator"
// 5. Replace Code.gs with this file's content
// 6. Add HTML file named "ArbitrageCalculator" with content from ArbitrageCalculator_Index.html
// 7. Click "Deploy" → "New deployment"
// 8. Select type: "Web app"
// 9. Settings:
//    - Description: "Arbitrage Calculator"
//    - Execute as: "Me"
//    - Who has access: "Anyone"
// 10. Click "Deploy"
// 11. Copy the Web App URL (ends with /exec)
// 12. Update index.html arbitrage modal iframe src with this URL
//
// ====================================================================

function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('ArbitrageCalculator')
    .setTitle('PrUn Arbitrage Calculator')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

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

    const tickerIdx = headers.indexOf('Ticker');
    const nameIdx = headers.indexOf('Name');
    const exchangeIdx = headers.indexOf('Exchange');
    const askIdx = headers.indexOf('Ask Price');
    const bidIdx = headers.indexOf('Bid Price');
    const supplyIdx = headers.indexOf('Supply');
    const demandIdx = headers.indexOf('Demand');
    const tradedIdx = headers.indexOf('Traded Volume');

    if (tickerIdx === -1 || exchangeIdx === -1) {
      return { error: 'Required columns not found' };
    }

    const minProfitValue = parseFloat(minProfit) || 0;
    const minROIValue = parseFloat(minROI) || 0;
    const transportCost = parseFloat(transportCostPerUnit) || 0;

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

      if (!ticker || !exchange) continue;

      if (!priceMap[ticker]) {
        priceMap[ticker] = { name: name, exchanges: {} };
      }

      priceMap[ticker].exchanges[exchange] = {
        askPrice: askPrice,
        bidPrice: bidPrice,
        supply: supply,
        demand: demand,
        traded: traded
      };
    }

    const opportunities = [];

    for (const ticker in priceMap) {
      const material = priceMap[ticker];
      const originData = material.exchanges[originExchange];
      const destData = material.exchanges[destExchange];

      if (!originData || !destData) continue;

      const buyPrice = originData.askPrice;
      const sellPrice = destData.bidPrice;

      if (buyPrice <= 0 || sellPrice <= 0) continue;

      const profit = sellPrice - buyPrice - transportCost;

      if (profit <= minProfitValue) continue;

      const roi = (profit / (buyPrice + transportCost)) * 100;

      if (roi < minROIValue) continue;

      const maxVolume = Math.min(originData.supply, destData.demand);
      const totalProfit = profit * maxVolume;

      let opportunityLevel = 'Low';
      if (totalProfit >= 100000) opportunityLevel = 'Very High';
      else if (totalProfit >= 50000) opportunityLevel = 'High';
      else if (totalProfit >= 10000) opportunityLevel = 'Medium';

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

    let sheet = ss.getSheetByName(sheetName);
    if (sheet) {
      ss.deleteSheet(sheet);
    }

    sheet = ss.insertSheet(sheetName);

    const headers = [
      'Ticker', 'Name', 'Buy Price', 'Sell Price', 'Profit/Unit', 
      'ROI %', 'Supply', 'Demand', 'Max Volume', 'Total Profit',
      'Opportunity Level', 'Liquidity', 'Origin Traded', 'Dest Traded'
    ];

    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.getRange(1, 1, 1, headers.length).setBackground('#1e40af');
    sheet.getRange(1, 1, 1, headers.length).setFontColor('#ffffff');

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
      sheet.getRange(2, 3, rows.length, 2).setNumberFormat('#,##0.00');
      sheet.getRange(2, 5, rows.length, 1).setNumberFormat('#,##0.00');
      sheet.getRange(2, 6, rows.length, 1).setNumberFormat('#,##0.00"%"');
      sheet.getRange(2, 7, rows.length, 4).setNumberFormat('#,##0');
      sheet.getRange(2, 10, rows.length, 1).setNumberFormat('#,##0.00');
      sheet.getRange(2, 13, rows.length, 2).setNumberFormat('#,##0');
    }

    sheet.autoResizeColumns(1, headers.length);
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
