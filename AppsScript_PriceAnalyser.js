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

// Get recipes for a specific material
function getRecipesForMaterial(material) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return [];
    }
    
    const data = sheet.getDataRange().getValues();
    const recipes = [];
    const seen = new Set();
    
    // Find all unique recipes for this material (column B is Ticker, column C is Recipe)
    for (let i = 1; i < data.length; i++) {
      if (data[i][1] === material && data[i][2]) { // Check Ticker and Recipe column exists
        const recipeKey = data[i][2];
        
        if (!seen.has(recipeKey)) {
          seen.add(recipeKey);
          
          // Extract building prefix from recipe (e.g., "BMP:1xC-2xH=>200xPE" -> "BMP")
          const building = recipeKey.split(':')[0];
          
          // Create a shortened display label
          let label = recipeKey;
          if (label.length > 50) {
            label = label.substring(0, 47) + '...';
          }
          
          recipes.push({
            key: recipeKey,
            label: label,
            building: building
          });
        }
      }
    }
    
    // Sort by building name
    recipes.sort((a, b) => a.building.localeCompare(b.building));
    
    return recipes;
  } catch (error) {
    Logger.log('Error getting recipes: ' + error.toString());
    return [];
  }
}

// Get recommended recipe based on profitability comparison
function getRecommendedRecipe(material, exchange) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return { error: 'Price Analyser Data sheet not found' };
    }
    
    const data = sheet.getDataRange().getValues();
    const recipeComparisons = [];
    
    // Find all recipes for this material+exchange combination
    // Column structure: A=LookupKey, B=Ticker, C=Recipe, D=Material Name, E=Exchange,
    // F=Ask_Price, G=Bid_Price, H=Input Cost Ask, I=Input Cost Bid,
    // J=Workforce Cost Ask, K=Workforce Cost Bid, L=Amount per Recipe, M=Supply, N=Demand
    for (let i = 1; i < data.length; i++) {
      if (data[i][1] === material && data[i][4] === exchange && data[i][2]) {
        const recipeString = data[i][2];
        const askPrice = parseFloat(data[i][5]) || 0;        // Column F
        const inputCostAsk = parseFloat(data[i][7]) || 0;    // Column H
        const workforceCostAsk = parseFloat(data[i][9]) || 0; // Column J
        const totalCostAsk = inputCostAsk + workforceCostAsk;
        const profitAskAsk = askPrice - totalCostAsk;
        const roiAskAsk = totalCostAsk > 0 ? (profitAskAsk / totalCostAsk) * 100 : 0;
        
        // Parse recipe for display
        let recipeInputs = '';
        let recipeOutputs = '';
        let building = '';
        
        if (recipeString.includes('=>')) {
          building = recipeString.split(':')[0];
          const parts = recipeString.split('=>');
          const inputPart = parts[0].split(':')[1] || parts[0];
          const outputPart = parts[1];
          
          recipeInputs = inputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[1] + ' ' + match[2] : item;
          }).join(', ');
          
          recipeOutputs = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[1] + ' ' + match[2] : item;
          }).join(', ');
        }
        
        recipeComparisons.push({
          recipe: recipeString,
          building: building,
          inputs: recipeInputs,
          outputs: recipeOutputs,
          inputCost: inputCostAsk,
          workforceCost: workforceCostAsk,
          totalCost: totalCostAsk,
          profit: profitAskAsk,
          roi: roiAskAsk
        });
      }
    }
    
    if (recipeComparisons.length === 0) {
      return { count: 0, message: 'No recipes found' };
    }
    
    if (recipeComparisons.length === 1) {
      return {
        count: 1,
        message: 'Only one recipe available',
        recommended: recipeComparisons[0],
        alternatives: []
      };
    }
    
    // Sort by profit (descending) - most profitable first
    recipeComparisons.sort((a, b) => b.profit - a.profit);
    
    return {
      count: recipeComparisons.length,
      recommended: recipeComparisons[0],
      alternatives: recipeComparisons.slice(1)
    };
    
  } catch (error) {
    Logger.log('Error getting recommended recipe: ' + error.toString());
    return { error: 'Error analyzing recipes: ' + error.toString() };
  }
}

// Get calculation data for selected material, exchange, and optionally specific recipe
function getCalculationData(material, exchange, recipe) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Price Analyser Data');
  
  if (!sheet) {
    return { error: 'Price Analyser Data sheet not found' };
  }
  
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  
  let bestRow = null;
  let lowestCost = Infinity;
  
  // Find matching rows (Ticker in column B, Exchange in column E, Recipe in column C)
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === material && data[i][4] === exchange) {
      // If specific recipe requested, match it exactly
      if (recipe && data[i][2] === recipe) {
        bestRow = i;
        break;
      }
      
      // If no recipe specified, find the one with lowest total cost (Ask basis)
      if (!recipe) {
        const inputCostAsk = parseFloat(data[i][6]) || 0;
        const workforceCostAsk = parseFloat(data[i][8]) || 0;
        const totalCost = inputCostAsk + workforceCostAsk;
        
        if (totalCost < lowestCost) {
          lowestCost = totalCost;
          bestRow = i;
        }
      }
    }
  }
  
  if (bestRow === null) {
    return { error: 'No data found for ' + material + ' on ' + exchange + (recipe ? ' with recipe ' + recipe : '') };
  }
  
  // Use the best matching row
  const i = bestRow;
  
  // Extract data from the found row
  if (data[i][0] && data[i][1] === material) {
      // Actual column structure:
      // A: LookupKey, B: Ticker, C: Recipe, D: Material Name, E: Exchange,
      // F: Ask_Price, G: Bid_Price, H: Input Cost Ask, I: Input Cost Bid,
      // J: Workforce Cost Ask, K: Workforce Cost Bid,
      // L: Amount per Recipe, M: Supply, N: Demand
      
      const askPrice = parseFloat(data[i][5]) || 0;           // Column F: Ask_Price
      const bidPrice = parseFloat(data[i][6]) || 0;           // Column G: Bid_Price
      const inputCostAsk = parseFloat(data[i][7]) || 0;       // Column H: Input Cost Ask
      const inputCostBid = parseFloat(data[i][8]) || 0;       // Column I: Input Cost Bid
      const workforceCostAsk = parseFloat(data[i][9]) || 0;   // Column J: Workforce Cost Ask
      const workforceCostBid = parseFloat(data[i][10]) || 0;  // Column K: Workforce Cost Bid
      const amountPerRecipe = parseFloat(data[i][11]) || 1;   // Column L: Amount per Recipe
      const supply = data[i][12] || 0;                         // Column M: Supply
      const demand = data[i][13] || 0;                         // Column N: Demand
      
      // Parse recipe to extract inputs and outputs
      const recipeString = data[i][2] || 'N/A';
      let recipeInputs = '';
      let recipeOutputs = '';
      
      if (recipeString !== 'N/A' && recipeString.includes('=>')) {
        try {
          // Format: "FP:1xALG-1xGRN-1xNUT=>10xRAT"
          const parts = recipeString.split('=>');
          const inputPart = parts[0].split(':')[1] || parts[0]; // Remove building prefix
          const outputPart = parts[1];
          
          // Parse inputs: "1xALG-1xGRN-1xNUT" -> "1 ALG, 1 GRN, 1 NUT"
          recipeInputs = inputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[1] + ' ' + match[2] : item;
          }).join(', ');
          
          // Parse outputs: "10xRAT" -> "10 RAT"
          recipeOutputs = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[1] + ' ' + match[2] : item;
          }).join(', ');
        } catch (e) {
          recipeInputs = 'Parse error';
          recipeOutputs = 'Parse error';
        }
      }
      
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
        recipe: recipeString,
        recipeInputs: recipeInputs,
        recipeOutputs: recipeOutputs,
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
        demand: demand
        };
    }
}
