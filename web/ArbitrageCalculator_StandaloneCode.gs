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
    const ss = SpreadsheetApp.openById('1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI');

    const minProfitValue = parseFloat(minProfit) || 0;
    const minROIValue = parseFloat(minROI) || 0;
    const transportCost = parseFloat(transportCostPerUnit) || 0;

    const opportunities = [];

    // Attempt 1: Per-exchange report tabs like "Report AI1", "Report CI1", etc.
    const originSheetName = `Report ${originExchange}`;
    const destSheetName = `Report ${destExchange}`;
    let originSheet = null;
    let destSheet = null;
    try { originSheet = ss.getSheetByName(originSheetName); } catch (e) {}
    try { destSheet = ss.getSheetByName(destSheetName); } catch (e) {}

    const allSheets = ss.getSheets().map(s => s.getName());

    // Helper to build a map from a per-exchange sheet with underscore headers
    function buildExchangeMap(sheet) {
      const map = {};
      const range = sheet.getDataRange();
      const values = range.getValues();

      // Find the actual header row (some reports have multi-row numeric headers)
      let headerRowIndex = 0;
      for (let r = 0; r < Math.min(values.length, 10); r++) {
        const rowStrings = values[r].map(v => String(v));
        const hasTicker = rowStrings.includes('Ticker') || rowStrings.includes('LookupKey');
        const hasMaterial = rowStrings.includes('Material Name') || rowStrings.includes('Name');
        const hasAsk = rowStrings.includes('Ask_Price') || rowStrings.includes('Ask Price');
        const hasBid = rowStrings.includes('Bid_Price') || rowStrings.includes('Bid Price');
        if ((hasTicker && hasMaterial) || (hasAsk && hasBid)) {
          headerRowIndex = r;
          break;
        }
      }

      const headers = values[headerRowIndex].map(String);

      // Support both underscore and space headers
      const idx = {
        ticker: headers.indexOf('Ticker') !== -1 ? headers.indexOf('Ticker') : headers.indexOf('LookupKey'),
        name: headers.indexOf('Material Name') !== -1 ? headers.indexOf('Material Name') : headers.indexOf('Name'),
        ask: headers.indexOf('Ask_Price') !== -1 ? headers.indexOf('Ask_Price') : headers.indexOf('Ask Price'),
        bid: headers.indexOf('Bid_Price') !== -1 ? headers.indexOf('Bid_Price') : headers.indexOf('Bid Price'),
        supply: headers.indexOf('Supply'),
        demand: headers.indexOf('Demand'),
        traded: headers.indexOf('Traded Volume'),
        volume: headers.indexOf('Volume')
      };

      // If critical indices are missing, return empty map with headers for debugging
      const valid = !(idx.ticker === -1 || idx.ask === -1 || idx.bid === -1);
      if (!valid) {
        return { map, headers, valid };
      }

      for (let r = headerRowIndex + 1; r < values.length; r++) {
        const row = values[r];
        const ticker = String(row[idx.ticker] || '').trim();
        if (!ticker) continue;
        const name = row[idx.name] || ticker;
        const ask = parseFloat(row[idx.ask]) || 0;
        const bid = parseFloat(row[idx.bid]) || 0;
        const supply = idx.supply !== -1 ? (parseFloat(row[idx.supply]) || 0) : 0;
        const demand = idx.demand !== -1 ? (parseFloat(row[idx.demand]) || 0) : 0;
        const traded = idx.traded !== -1 ? (parseFloat(row[idx.traded]) || 0) : 0;
        const volume = idx.volume !== -1 ? (parseFloat(row[idx.volume]) || 0) : 0;

        map[ticker] = { name, ask, bid, supply, demand, traded, volume };
      }

      return { map, headers, valid: true };
    }

    // Helper: safe parse that supports comma decimals and strips non-numeric
    function parseNum(v) {
      if (v === null || v === undefined) return 0;
      const s = String(v).replace(/[^0-9,\.\-]/g, '').replace(',', '.');
      const n = parseFloat(s);
      return isNaN(n) ? 0 : n;
    }

    // Helper: read 'ARBITRAGE OPPORTUNITIES' section inside a report sheet
    function readArbSectionFromReport(sheet) {
      const data = sheet.getDataRange().getValues();
      let titleRow = -1;
      // Find any cell in the first 100 rows that matches 'ARBITRAGE OPPORTUNITIES'
      for (let r = 0; r < Math.min(data.length, 100); r++) {
        for (let c = 0; c < data[r].length; c++) {
          if (String(data[r][c]).trim().toUpperCase() === 'ARBITRAGE OPPORTUNITIES') {
            titleRow = r;
            break;
          }
        }
        if (titleRow !== -1) break;
      }
      if (titleRow === -1) return { rows: [], headers: [], found: false };

      // Search for the header row after the title row: row that contains Ticker and (Buy Exchange or Sell Exchange)
      let headerRow = -1;
      for (let r = titleRow + 1; r < Math.min(data.length, titleRow + 15); r++) {
        const rowStrings = data[r].map(v => String(v).trim());
        const hasTicker = rowStrings.includes('Ticker');
        const hasBuyEx = rowStrings.some(v => v === 'Buy Exchange');
        const hasSellEx = rowStrings.some(v => v === 'Sell Exchange');
        if (hasTicker && (hasBuyEx || hasSellEx)) {
          headerRow = r;
          break;
        }
      }
      if (headerRow === -1) return { rows: [], headers: [], found: false };

      const headers = data[headerRow].map(h => String(h).trim());

      const idx = {
        ticker: headers.indexOf('Ticker'),
        name: headers.indexOf('Name') !== -1 ? headers.indexOf('Name') : headers.indexOf('Product'),
        buyPrice: headers.indexOf('Buy Price'),
        sellPrice: headers.indexOf('Sell Price'),
        profit: headers.indexOf('Profit'),
        buyEx: headers.indexOf('Buy Exchange'),
        sellEx: headers.indexOf('Sell Exchange'),
        roi: headers.indexOf('ROI'),
        size: headers.indexOf('Opportunity Size'),
        oppLevel: headers.indexOf('Opportunity Level')
      };

      const rows = [];
      for (let r = headerRow + 1; r < data.length; r++) {
        const row = data[r];
        const ticker = String(idx.ticker !== -1 ? row[idx.ticker] : '').trim();
        const buyEx = idx.buyEx !== -1 ? String(row[idx.buyEx] || '').trim().toUpperCase() : '';
        const sellEx = idx.sellEx !== -1 ? String(row[idx.sellEx] || '').trim().toUpperCase() : '';
        // Stop if section ends (blank ticker and buy/sell)
        if (!ticker && !buyEx && !sellEx) break;
        if (!ticker) continue;

        rows.push({
          ticker,
          name: idx.name !== -1 ? (row[idx.name] || ticker) : ticker,
          buyEx,
          sellEx,
          buyPrice: parseNum(idx.buyPrice !== -1 ? row[idx.buyPrice] : 0),
          sellPrice: parseNum(idx.sellPrice !== -1 ? row[idx.sellPrice] : 0),
          profit: parseNum(idx.profit !== -1 ? row[idx.profit] : 0),
          roi: parseNum(idx.roi !== -1 ? row[idx.roi] : 0),
          size: parseNum(idx.size !== -1 ? row[idx.size] : 0),
          oppLevel: idx.oppLevel !== -1 ? row[idx.oppLevel] : ''
        });
      }

      return { rows, headers, found: true };
    }

    let debugInfo = {
      mode: '',
      sheetName: '',
      dataRows: 0,
      columns: 0,
      headerNames: [],
      availableSheets: allSheets,
      originSheetTried: originSheetName,
      destSheetTried: destSheetName
    };

    if (originSheet && destSheet) {
      debugInfo.sheetName = `${originSheet.getName()} & ${destSheet.getName()}`;
      debugInfo.dataRows = (originSheet.getLastRow() - 1) + (destSheet.getLastRow() - 1);
      debugInfo.columns = Math.max(originSheet.getLastColumn(), destSheet.getLastColumn());
      debugInfo.arbSectionFound = false;

      // First, try the in-sheet ARBITRAGE OPPORTUNITIES section (more reliable for these reports)
      const section = readArbSectionFromReport(originSheet);
      if (section.found && section.rows.length > 0) {
        debugInfo.mode = 'per-exchange-tabs:arb-section';
        debugInfo.arbSectionFound = true;
        debugInfo.headerNames = section.headers;
        for (const row of section.rows) {
          if (row.buyEx !== originExchange || row.sellEx !== destExchange) continue;
          const buyPrice = row.buyPrice;
          const sellPrice = row.sellPrice;
          let profit = sellPrice - buyPrice - transportCost;
          let roi = buyPrice > 0 ? (profit / buyPrice) * 100 : 0;

          if (minProfitValue === 0 && minROIValue === 0) {
            if (profit <= 0) continue;
          } else {
            if (minProfitValue > 0 && profit < minProfitValue) continue;
            if (minROIValue > 0 && roi < minROIValue) continue;
          }

          const opportunitySize = row.size || 0;
          const totalProfit = profit * opportunitySize;
          let opportunityLevel = row.oppLevel || 'Low';
          if (!row.oppLevel) {
            if (totalProfit >= 100000) opportunityLevel = 'Very High';
            else if (totalProfit >= 50000) opportunityLevel = 'High';
            else if (totalProfit >= 10000) opportunityLevel = 'Medium';
            else opportunityLevel = 'Low';
          }

          opportunities.push({
            ticker: row.ticker,
            name: row.name,
            buyPrice,
            sellPrice,
            profit,
            profitPerM3: 0,
            roi,
            supply: opportunitySize,
            demand: opportunitySize,
            maxVolume: opportunitySize,
            totalProfit,
            opportunityLevel,
            liquidityLevel: 'Medium'
          });
        }
      }

      // If nothing found in section, fall back to bid/ask maps (if usable)
      if (opportunities.length === 0) {
        const originData = buildExchangeMap(originSheet);
        const destData = buildExchangeMap(destSheet);

        debugInfo.mode = 'per-exchange-tabs';
        debugInfo.headerNames = originData.headers;

        const originMap = originData.map;
        const destMap = destData.map;

        for (const ticker in originMap) {
          if (!destMap[ticker]) continue;
          const o = originMap[ticker];
          const d = destMap[ticker];

          const buyPrice = o.bid || o.ask;
          const sellPrice = d.ask || d.bid;
          if (buyPrice <= 0 && sellPrice <= 0) continue;

      const profit = sellPrice - buyPrice - transportCost;
      const volume = o.volume || d.volume || 0;
      const profitPerM3 = volume > 0 ? profit / volume : 0;
          const roi = buyPrice > 0 ? (profit / (buyPrice + transportCost)) * 100 : 0;

          if (minProfitValue === 0 && minROIValue === 0) {
            if (profit <= 0) continue;
          } else {
            if (minProfitValue > 0 && profit < minProfitValue) continue;
            if (minROIValue > 0 && roi < minROIValue) continue;
          }

          const maxVolume = Math.min(o.supply, d.demand);
          const totalProfit = profit * maxVolume;

          let opportunityLevel = 'Low';
          if (totalProfit >= 100000) opportunityLevel = 'Very High';
          else if (totalProfit >= 50000) opportunityLevel = 'High';
          else if (totalProfit >= 10000) opportunityLevel = 'Medium';

          const avgTraded = (o.traded + d.traded) / 2;
          let liquidityLevel = 'Low';
          if (avgTraded >= 1000) liquidityLevel = 'High';
          else if (avgTraded >= 100) liquidityLevel = 'Medium';

          opportunities.push({
            ticker: ticker,
            name: o.name,
            buyPrice: buyPrice,
            sellPrice: sellPrice,
        profit: profit,
        profitPerM3: profitPerM3,
        roi: roi,
            supply: o.supply,
            demand: d.demand,
            maxVolume: maxVolume,
            totalProfit: totalProfit,
            opportunityLevel: opportunityLevel,
            liquidityLevel: liquidityLevel,
            originTraded: o.traded,
            destTraded: d.traded,
            avgTraded: avgTraded
          });
        }

        // If the bid/ask map is invalid or headers look numeric, try the arb section as a final fallback
        const headersLookNumeric = debugInfo.headerNames.length > 0 && debugInfo.headerNames.every(h => /^\d+$/.test(String(h)));
        if (opportunities.length === 0 || headersLookNumeric || !originData.valid || !destData.valid) {
          const sectionFallback = readArbSectionFromReport(originSheet);
          if (sectionFallback.found) {
            debugInfo.mode = 'per-exchange-tabs:arb-section';
            debugInfo.arbSectionFound = true;
            debugInfo.headerNames = sectionFallback.headers;
            for (const row of sectionFallback.rows) {
              if (row.buyEx !== originExchange || row.sellEx !== destExchange) continue;
              const buyPrice = row.buyPrice;
              const sellPrice = row.sellPrice;
              let profit = sellPrice - buyPrice - transportCost;
              let roi = buyPrice > 0 ? (profit / buyPrice) * 100 : 0;

              if (minProfitValue === 0 && minROIValue === 0) {
                if (profit <= 0) continue;
              } else {
                if (minProfitValue > 0 && profit < minProfitValue) continue;
                if (minROIValue > 0 && roi < minROIValue) continue;
              }

              const opportunitySize = row.size || 0;
              const totalProfit = profit * opportunitySize;
              let opportunityLevel = row.oppLevel || 'Low';
              if (!row.oppLevel) {
                if (totalProfit >= 100000) opportunityLevel = 'Very High';
                else if (totalProfit >= 50000) opportunityLevel = 'High';
                else if (totalProfit >= 10000) opportunityLevel = 'Medium';
                else opportunityLevel = 'Low';
              }

              opportunities.push({
                ticker: row.ticker,
                name: row.name,
                buyPrice,
                sellPrice,
                profit,
                profitPerM3: 0,
                roi,
                supply: opportunitySize,
                demand: opportunitySize,
                maxVolume: opportunitySize,
                totalProfit,
                opportunityLevel,
                liquidityLevel: 'Medium'
              });
            }
          }
        }
      }
    } else {
      // Attempt 2: Dedicated precomputed arbitrage sheet
      const arbSheet = ss.getSheetByName('ARBITRAGE OPPORTUNITIES');

      if (arbSheet) {
        const data = arbSheet.getDataRange().getValues();
        // Find header row (may be preceded by title row)
        let headerRowIndex = 0;
        for (let r = 0; r < Math.min(data.length, 10); r++) {
          const row = data[r].map(String);
          if (row.includes('Ticker') && (row.includes('Buy Exchange') || row.includes('Buy Exchange'))) {
            headerRowIndex = r; break;
          }
        }
        const headers = data[headerRowIndex].map(String);

        debugInfo.mode = 'arbitrage-precomputed';
        debugInfo.sheetName = arbSheet.getName();
        debugInfo.dataRows = data.length - (headerRowIndex + 1);
        debugInfo.columns = headers.length;
        debugInfo.headerNames = headers;

        const idx = {
          ticker: headers.indexOf('Ticker'),
          name: headers.indexOf('Name') !== -1 ? headers.indexOf('Name') : headers.indexOf('Product'),
          buyPrice: headers.indexOf('Buy Price'),
          sellPrice: headers.indexOf('Sell Price'),
          profit: headers.indexOf('Profit'),
          buyEx: headers.indexOf('Buy Exchange'),
          sellEx: headers.indexOf('Sell Exchange'),
          roi: headers.indexOf('ROI'),
          size: headers.indexOf('Opportunity Size'),
          oppLevel: headers.indexOf('Opportunity Level')
        };

        for (let r = headerRowIndex + 1; r < data.length; r++) {
          const row = data[r];
          const ticker = String(row[idx.ticker] || '').trim();
          if (!ticker) continue;
          const name = row[idx.name] || ticker;
          const buyEx = String(row[idx.buyEx] || '').trim();
          const sellEx = String(row[idx.sellEx] || '').trim();
          if (buyEx !== originExchange || sellEx !== destExchange) continue;

          const buyPrice = parseNum(row[idx.buyPrice]);
          const sellPrice = parseNum(row[idx.sellPrice]);
          let profit = parseNum(row[idx.profit]);
          let roi = parseNum(row[idx.roi]);
          const opportunitySize = parseNum(row[idx.size]);

          // Recalculate profit/roi with provided transport cost to be consistent
          profit = (sellPrice - buyPrice - transportCost);
          roi = buyPrice > 0 ? (profit / buyPrice) * 100 : 0;

          if (minProfitValue === 0 && minROIValue === 0) {
            if (profit <= 0) continue;
          } else {
            if (minProfitValue > 0 && profit < minProfitValue) continue;
            if (minROIValue > 0 && roi < minROIValue) continue;
          }

          const totalProfit = profit * opportunitySize;
          let opportunityLevel = row[idx.oppLevel] || 'Low';
          if (!opportunityLevel) {
            if (totalProfit >= 100000) opportunityLevel = 'Very High';
            else if (totalProfit >= 50000) opportunityLevel = 'High';
            else if (totalProfit >= 10000) opportunityLevel = 'Medium';
            else opportunityLevel = 'Low';
          }

          opportunities.push({
            ticker,
            name,
            buyPrice,
            sellPrice,
            profit,
            profitPerM3: 0,
            roi,
            supply: opportunitySize,
            demand: opportunitySize,
            maxVolume: opportunitySize,
            totalProfit,
            opportunityLevel,
            liquidityLevel: 'Medium'
          });
        }
      } else {
        // Attempt 3: Single consolidated sheet, support underscore headers
        let sheet = null;
        const possibleNames = ['Price Analyser Data', 'Report', 'Arbitrage', 'Data', 'Sheet1'];
        for (const sheetName of possibleNames) {
          try {
            const s = ss.getSheetByName(sheetName);
            if (s) { sheet = s; break; }
          } catch (e) {}
        }

      if (!sheet) {
        return {
          error: 'No suitable data sheet found',
          availableSheets: allSheets,
          sheetsChecked: ['Report <EXCHANGE>', ...possibleNames]
        };
      }

      const data = sheet.getDataRange().getValues();
      // Detect header row for consolidated sheet too
      let headerRowIndex2 = 0;
      for (let r = 0; r < Math.min(data.length, 10); r++) {
        const rowStrings = data[r].map(v => String(v));
        const hasExchange = rowStrings.includes('Exchange');
        const hasAsk = rowStrings.includes('Ask_Price') || rowStrings.includes('Ask Price');
        const hasBid = rowStrings.includes('Bid_Price') || rowStrings.includes('Bid Price');
        if (hasExchange && hasAsk && hasBid) { headerRowIndex2 = r; break; }
      }
      const headers = data[headerRowIndex2].map(String);

      debugInfo.mode = 'single-sheet';
      debugInfo.sheetName = sheet.getName();
      debugInfo.dataRows = data.length - 1;
      debugInfo.columns = headers.length;
      debugInfo.headerNames = headers;

      const tickerIdx = headers.indexOf('Ticker') !== -1 ? headers.indexOf('Ticker') : headers.indexOf('LookupKey');
      const nameIdx = headers.indexOf('Material Name') !== -1 ? headers.indexOf('Material Name') : headers.indexOf('Name');
      const exchangeIdx = headers.indexOf('Exchange');
      const askIdx = headers.indexOf('Ask_Price') !== -1 ? headers.indexOf('Ask_Price') : headers.indexOf('Ask Price');
      const bidIdx = headers.indexOf('Bid_Price') !== -1 ? headers.indexOf('Bid_Price') : headers.indexOf('Bid Price');
      const supplyIdx = headers.indexOf('Supply');
      const demandIdx = headers.indexOf('Demand');
      const tradedIdx = headers.indexOf('Traded Volume');
      const volumeIdx = headers.indexOf('Volume');

      const priceMap = {};
      for (let i = headerRowIndex2 + 1; i < data.length; i++) {
        const row = data[i];
        const ticker = String(row[tickerIdx] || '').trim();
        const name = row[nameIdx] || ticker;
        const exchange = row[exchangeIdx];
        if (!ticker || !exchange) continue;

        const askPrice = parseFloat(row[askIdx]) || 0;
        const bidPrice = parseFloat(row[bidIdx]) || 0;
        const supply = supplyIdx !== -1 ? (parseFloat(row[supplyIdx]) || 0) : 0;
        const demand = demandIdx !== -1 ? (parseFloat(row[demandIdx]) || 0) : 0;
        const traded = tradedIdx !== -1 ? (parseFloat(row[tradedIdx]) || 0) : 0;
        const volume = volumeIdx !== -1 ? (parseFloat(row[volumeIdx]) || 0) : 0;

        if (!priceMap[ticker]) priceMap[ticker] = { name, exchanges: {} };
        priceMap[ticker].exchanges[exchange] = { askPrice, bidPrice, supply, demand, traded, volume };
      }

      for (const ticker in priceMap) {
        const material = priceMap[ticker];
        const o = material.exchanges[originExchange];
        const d = material.exchanges[destExchange];
        if (!o || !d) continue;

        const buyPrice = o.bidPrice || o.askPrice;
        const sellPrice = d.askPrice || d.bidPrice;
        if (buyPrice <= 0 && sellPrice <= 0) continue;

        const profit = sellPrice - buyPrice - transportCost;
        const volume = o.volume || d.volume || 0;
        const profitPerM3 = volume > 0 ? profit / volume : 0;
        const roi = buyPrice > 0 ? (profit / (buyPrice + transportCost)) * 100 : 0;

        if (minProfitValue === 0 && minROIValue === 0) {
          if (profit <= 0) continue;
        } else {
          if (minProfitValue > 0 && profit < minProfitValue) continue;
          if (minROIValue > 0 && roi < minROIValue) continue;
        }

        const maxVolume = Math.min(o.supply, d.demand);
        const totalProfit = profit * maxVolume;

        let opportunityLevel = 'Low';
        if (totalProfit >= 100000) opportunityLevel = 'Very High';
        else if (totalProfit >= 50000) opportunityLevel = 'High';
        else if (totalProfit >= 10000) opportunityLevel = 'Medium';

        const avgTraded = (o.traded + d.traded) / 2;
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
          supply: o.supply,
          demand: d.demand,
          maxVolume: maxVolume,
          totalProfit: totalProfit,
          opportunityLevel: opportunityLevel,
          liquidityLevel: liquidityLevel,
          originTraded: o.traded,
          destTraded: d.traded,
          avgTraded: avgTraded
        });
      }
    }

    // Close the outer else branch (single-sheet or arbitrage-precomputed)
    }
    
    opportunities.sort((a, b) => b.totalProfit - a.totalProfit);

    return {
      opportunities,
      count: opportunities.length,
      originExchange,
      destExchange,
      transportCost,
      debug: debugInfo,
      dataProcessed: true
    };

  } catch (error) {
    return { error: error.toString() };
  }
}

function getMetadata() {
  try {
    const ss = SpreadsheetApp.openById('1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI');
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
  // Export functionality removed - data is read-only from the spreadsheet
  return { 
    error: 'Export functionality is not available. This tool provides read-only access to market data.' 
  };
}
