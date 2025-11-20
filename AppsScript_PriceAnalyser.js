// ====================================================================
// GOOGLE APPS SCRIPT - INTERACTIVE PRICE ANALYSER WEB APP
// ====================================================================
// 
// DEPLOYMENT INSTRUCTIONS:
// 1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI/edit
// 2. Go to: Extensions → Apps Script
// 3. Delete any existing code
// 4. Paste ALL this code
// 5. Click "Deploy" → "New deployment"
// 6. Select type: "Web app"
// 7. Settings:
//    - Description: "Price Analyser Interactive"
//    - Execute as: "Me"
//    - Who has access: "Anyone"
// 8. Click "Deploy"
// 9. Copy the Web App URL (ends with /exec)
// 10. Replace the iframe src in index.html with this URL
//
// ====================================================================

// Main function to serve the HTML page
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('PrUn Price Analyser')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL); // Allow embedding
}

// Fetch all material names (unique) from Price Analyser Data sheet
function getMaterials() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Price Analyser Data');
  
  if (!sheet) {
    return ['Error: Price Analyser Data sheet not found'];
  }
  
  const data = sheet.getDataRange().getValues();
  const materialsSet = new Set();
  
  // Skip header row, column B contains materials like "AAR", "DW", etc.
  for (let i = 1; i < data.length; i++) {
    const material = data[i][1]; // Column B = Material ticker
    if (material && typeof material === 'string') {
      materialsSet.add(material);
    }
  }
  
  return Array.from(materialsSet).sort();
}

// Fetch all exchange names (unique) from Price Analyser Data sheet
function getExchanges() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Price Analyser Data');
  
  if (!sheet) {
    return ['Error: Price Analyser Data sheet not found'];
  }
  
  const data = sheet.getDataRange().getValues();
  const exchangesSet = new Set();
  const knownExchanges = ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2'];
  
  // Skip header row, extract exchanges from column A by removing material prefix
  for (let i = 1; i < data.length; i++) {
    const fullCode = data[i][0]; // Column A contains codes like "AARCI1"
    if (fullCode && typeof fullCode === 'string') {
      // Check if it ends with a known exchange code
      for (const exchange of knownExchanges) {
        if (fullCode.endsWith(exchange)) {
          exchangesSet.add(exchange);
          break;
        }
      }
    }
  }
  
  return Array.from(exchangesSet).sort();
}

// Get calculation data for selected material and exchange
function getCalculationData(material, exchange) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Price Analyser Data');
  
  if (!sheet) {
    return { error: 'Price Analyser Data sheet not found' };
  }
  
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  
  // Build the full material code from material + exchange
  const fullMaterialCode = material + exchange; // e.g., "AAR" + "CI1" = "AARCI1"
  
  // Find the row matching the full code in column A
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === fullMaterialCode) {
      // Get base data from sheet
      const askPrice = parseFloat(data[i][1]) || 0;
      const bidPrice = parseFloat(data[i][2]) || 0;
      const inputCostAsk = parseFloat(data[i][3]) || 0;
      const inputCostBid = parseFloat(data[i][4]) || 0;
      const workforceCostAsk = parseFloat(data[i][5]) || 0;
      const workforceCostBid = parseFloat(data[i][6]) || 0;
      const supply = data[i][14] || 0;
      const demand = data[i][15] || 0;
      const distance = data[i][16] || 0;
      
      // Calculate total costs
      const totalCostAsk = inputCostAsk + workforceCostAsk;
      const totalCostBid = inputCostBid + workforceCostBid;
      
      // Calculate profitability for all 4 scenarios
      // Scenario 1: Sell at Ask, Buy inputs at Ask
      const profitAskAsk = askPrice - totalCostAsk;
      const roiAskAsk = totalCostAsk > 0 ? (profitAskAsk / totalCostAsk) * 100 : 0;
      const breakevenAskAsk = askPrice > 0 ? ((totalCostAsk - askPrice) / askPrice) * 100 : 0;
      
      // Scenario 2: Sell at Ask, Buy inputs at Bid
      const profitAskBid = askPrice - totalCostBid;
      const roiAskBid = totalCostBid > 0 ? (profitAskBid / totalCostBid) * 100 : 0;
      const breakevenAskBid = askPrice > 0 ? ((totalCostBid - askPrice) / askPrice) * 100 : 0;
      
      // Scenario 3: Sell at Bid, Buy inputs at Ask
      const profitBidAsk = bidPrice - totalCostAsk;
      const roiBidAsk = totalCostAsk > 0 ? (profitBidAsk / totalCostAsk) * 100 : 0;
      const breakevenBidAsk = bidPrice > 0 ? ((totalCostAsk - bidPrice) / bidPrice) * 100 : 0;
      
      // Scenario 4: Sell at Bid, Buy inputs at Bid
      const profitBidBid = bidPrice - totalCostBid;
      const roiBidBid = totalCostBid > 0 ? (profitBidBid / totalCostBid) * 100 : 0;
      const breakevenBidBid = bidPrice > 0 ? ((totalCostBid - bidPrice) / bidPrice) * 100 : 0;
      
      // Return comprehensive data object
      return {
        materialCode: data[i][0],
        material: material,
        exchange: exchange,
        askPrice: askPrice,
        bidPrice: bidPrice,
        inputCostAsk: inputCostAsk,
        inputCostBid: inputCostBid,
        workforceCostAsk: workforceCostAsk,
        workforceCostBid: workforceCostBid,
        totalCostAsk: totalCostAsk,
        totalCostBid: totalCostBid,
        // All 4 profit scenarios
        profitAskAsk: profitAskAsk,
        profitAskBid: profitAskBid,
        profitBidAsk: profitBidAsk,
        profitBidBid: profitBidBid,
        // All 4 ROI scenarios
        roiAskAsk: roiAskAsk,
        roiAskBid: roiAskBid,
        roiBidAsk: roiBidAsk,
        roiBidBid: roiBidBid,
        // All 4 breakeven scenarios
        breakevenAskAsk: breakevenAskAsk,
        breakevenAskBid: breakevenAskBid,
        breakevenBidAsk: breakevenBidAsk,
        breakevenBidBid: breakevenBidBid,
        // Market indicators
        supply: supply,
        demand: demand,
        distance: distance
      };
    }
  }
  
  return { error: 'No data found for ' + material + ' on ' + exchange };
}
