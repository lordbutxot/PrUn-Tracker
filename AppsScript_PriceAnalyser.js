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
  const materials = [];
  
  // Skip header row, get unique materials from column A
  for (let i = 1; i < data.length; i++) {
    const material = data[i][0];
    if (material && !materials.includes(material)) {
      materials.push(material);
    }
  }
  
  return materials.sort();
}

// Fetch all exchange names (unique) from Price Analyser Data sheet
function getExchanges() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Price Analyser Data');
  
  if (!sheet) {
    return ['Error: Price Analyser Data sheet not found'];
  }
  
  const data = sheet.getDataRange().getValues();
  const exchanges = [];
  
  // Skip header row, get unique exchanges from column B
  for (let i = 1; i < data.length; i++) {
    const exchange = data[i][1];
    if (exchange && !exchanges.includes(exchange)) {
      exchanges.push(exchange);
    }
  }
  
  return exchanges.sort();
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
  
  // Find the row matching material and exchange
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === material && data[i][1] === exchange) {
      // Return data as object with column names
      return {
        material: data[i][0],
        exchange: data[i][1],
        askPrice: data[i][2],
        bidPrice: data[i][3],
        inputCost: data[i][4],
        workforceCost: data[i][5],
        totalCost: data[i][6],
        profitAsk: data[i][7],
        profitBid: data[i][8],
        roiAsk: data[i][9],
        roiBid: data[i][10],
        breakevenAsk: data[i][11],
        breakevenBid: data[i][12],
        supply: data[i][13],
        demand: data[i][14],
        distance: data[i][15]
      };
    }
  }
  
  return { error: 'No data found for this combination' };
}
