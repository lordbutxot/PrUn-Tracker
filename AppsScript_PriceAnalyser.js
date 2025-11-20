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
  
  // Skip header row, column C contains exchanges like "CI1", "IC1", etc.
  for (let i = 1; i < data.length; i++) {
    const exchange = data[i][2]; // Column C = Exchange
    if (exchange && typeof exchange === 'string') {
      exchangesSet.add(exchange);
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
  
  // Find the row matching material (column B) and exchange (column C)
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === material && data[i][2] === exchange) {
      // Return data as object - adjust indices based on actual column structure
      return {
        materialCode: data[i][0],  // Column A - Full code (e.g., "AARCI1")
        material: data[i][1],       // Column B - Material ticker
        exchange: data[i][2],       // Column C - Exchange
        askPrice: data[i][3],       // Column D
        bidPrice: data[i][4],       // Column E
        inputCost: data[i][5],      // Column F
        workforceCost: data[i][6],  // Column G
        totalCost: data[i][7],      // Column H
        profitAsk: data[i][8],      // Column I
        profitBid: data[i][9],      // Column J
        roiAsk: data[i][10],        // Column K
        roiBid: data[i][11],        // Column L
        breakevenAsk: data[i][12],  // Column M
        breakevenBid: data[i][13],  // Column N
        supply: data[i][14],        // Column O
        demand: data[i][15],        // Column P
        distance: data[i][16]       // Column Q
      };
    }
  }
  
  return { error: 'No data found for ' + material + ' on ' + exchange };
}
