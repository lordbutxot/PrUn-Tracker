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

// NEW: Load all data at once to avoid multiple API calls
function getAllData() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return { error: 'Price Analyser Data sheet not found' };
    }
    
    const data = sheet.getDataRange().getValues();
    const headers = data[0];
    
    // Convert to array of objects for easier client-side processing
    const rows = [];
    for (let i = 1; i < data.length; i++) {
      rows.push({
        lookupKey: data[i][0],      // Column A
        ticker: data[i][1],          // Column B
        recipe: data[i][2],          // Column C
        materialName: data[i][3],    // Column D
        exchange: data[i][4],        // Column E
        askPrice: parseFloat(data[i][5]) || 0,       // Column F
        bidPrice: parseFloat(data[i][6]) || 0,       // Column G
        inputCostAsk: parseFloat(data[i][7]) || 0,   // Column H
        inputCostBid: parseFloat(data[i][8]) || 0,   // Column I
        workforceCostAsk: parseFloat(data[i][9]) || 0,  // Column J
        workforceCostBid: parseFloat(data[i][10]) || 0, // Column K
        amountPerRecipe: parseFloat(data[i][11]) || 1,  // Column L
        supply: data[i][12] || 0,    // Column M
        demand: data[i][13] || 0     // Column N
      });
    }
    
    // Load bids data for breakeven calculation
    const bidsSheet = ss.getSheetByName('Bids');
    const bids = [];
    if (bidsSheet) {
      const bidsData = bidsSheet.getDataRange().getValues();
      for (let i = 1; i < bidsData.length; i++) {
        bids.push({
          ticker: bidsData[i][0],      // MaterialTicker
          exchange: bidsData[i][1],    // ExchangeCode
          quantity: parseInt(bidsData[i][5]) || 0,  // ItemCount
          price: parseFloat(bidsData[i][6]) || 0    // ItemCost
        });
      }
    }
    
    // Load planet resources for extraction recipes
    const planetSheet = ss.getSheetByName('Planet Resources');
    const planets = [];
    if (planetSheet) {
      const planetData = planetSheet.getDataRange().getValues();
      // Skip header row (Key, Planet, Ticker, Type, Factor)
      for (let i = 1; i < planetData.length; i++) {
        planets.push({
          planet: planetData[i][1],    // Planet name
          ticker: planetData[i][2],    // Material ticker
          factor: parseFloat(planetData[i][4]) || 0  // Concentration factor
        });
      }
    }
    
    // Load planet fertility for farming recipes
    const fertilitySheet = ss.getSheetByName('Planet Fertility');
    const fertility = [];
    if (fertilitySheet) {
      try {
        const fertilityData = fertilitySheet.getDataRange().getValues();
        // Skip header row (Planet, Fertility)
        for (let i = 1; i < fertilityData.length; i++) {
          fertility.push({
            planet: fertilityData[i][0],    // Planet name
            fertility: parseFloat(fertilityData[i][1]) || 1.0  // Fertility factor
          });
        }
        Logger.log('Loaded ' + fertility.length + ' planets with fertility data');
      } catch (e) {
        Logger.log('Could not load fertility data: ' + e);
      }
    }
    
    return {
      success: true,
      data: rows,
      bids: bids,
      planets: planets,
      fertility: fertility,
      rowCount: rows.length
    };
  } catch (error) {
    Logger.log('Error loading all data: ' + error.toString());
    return { error: 'Failed to load data: ' + error.toString() };
  }
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

// Get planet concentration factor for a specific material and planet
function getPlanetFactor(ticker, planetName) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const planetSheet = ss.getSheetByName('Planet Resources');
    
    if (!planetSheet) {
      return 0;
    }
    
    const data = planetSheet.getDataRange().getValues();
    
    // Skip header row (Key, Planet, Ticker, Type, Factor)
    for (let i = 1; i < data.length; i++) {
      if (data[i][2] === ticker && data[i][1] === planetName) {
        return parseFloat(data[i][4]) || 0;
      }
    }
    
    return 0;
  } catch (error) {
    Logger.log('Error in getPlanetFactor: ' + error);
    return 0;
  }
}

// Get planets for extraction material
function getPlanetsForMaterial(ticker) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const planetSheet = ss.getSheetByName('Planet Resources');
    
    if (!planetSheet) {
      return [];
    }
    
    const data = planetSheet.getDataRange().getValues();
    const planets = [];
    
    // Skip header row (Key, Planet, Ticker, Type, Factor)
    for (let i = 1; i < data.length; i++) {
      if (data[i][2] === ticker) {  // Column C is Ticker
        planets.push({
          planet: data[i][1],  // Column B is Planet
          factor: parseFloat(data[i][4]) || 0  // Column E is Factor
        });
      }
    }
    
    // Sort by factor descending (best planets first)
    planets.sort((a, b) => b.factor - a.factor);
    
    return planets;
  } catch (error) {
    Logger.log('Error in getPlanetsForMaterial: ' + error);
    return [];
  }
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
function getRecommendedRecipe(material, exchange, includeLuxury, selfProduced) {
  try {
    includeLuxury = includeLuxury !== false; // Default true
    selfProduced = selfProduced === true;     // Default false
    
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
        let inputCostAsk = parseFloat(data[i][7]) || 0;      // Column H
        let workforceCostAsk = parseFloat(data[i][9]) || 0;  // Column J
        
        // Apply efficiency penalty if no luxury (79% efficiency = 1/0.79 = ~1.266x cost)
        if (!includeLuxury) {
          workforceCostAsk *= (1 / 0.79);
        }
        
        // Apply self-production cost (use production cost instead of market price for inputs)
        if (selfProduced) {
          inputCostAsk = calculateSelfProductionCost(data[i][2], data, exchange);
        }
        
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

// Helper function to calculate self-production cost by recursively looking up input materials
function calculateSelfProductionCost(recipeString, allData, exchange, visited) {
  if (!recipeString || !recipeString.includes('=>')) return 0;
  
  // Initialize visited set on first call
  if (!visited) visited = {};
  
  try {
    const parts = recipeString.split('=>');
    const inputPart = parts[0].split(':')[1] || parts[0];
    const inputs = inputPart.split('-');
    
    let totalCost = 0;
    for (let inputStr of inputs) {
      const match = inputStr.match(/(\d+)x([A-Z]+)/);
      if (match) {
        const amount = parseFloat(match[1]);
        const inputTicker = match[2];
        
        // Prevent infinite recursion for circular dependencies
        const visitKey = inputTicker + '_' + exchange;
        if (visited[visitKey]) {
          // If circular, fall back to market price
          for (let i = 1; i < allData.length; i++) {
            if (allData[i][1] === inputTicker && allData[i][4] === exchange) {
              const askPrice = parseFloat(allData[i][5]) || 0;
              totalCost += amount * askPrice;
              break;
            }
          }
          continue;
        }
        
        // Find the best (cheapest) recipe for this input material
        let bestInputCost = Infinity;
        let foundRecipe = false;
        
        for (let i = 1; i < allData.length; i++) {
          if (allData[i][1] === inputTicker && allData[i][4] === exchange && allData[i][2]) {
            foundRecipe = true;
            
            // Create new visited object for this branch
            const newVisited = Object.assign({}, visited);
            newVisited[visitKey] = true;
            
            // Recursively calculate production cost for this input's recipe
            const recursiveCost = calculateSelfProductionCost(allData[i][2], allData, exchange, newVisited);
            const workforceCost = parseFloat(allData[i][9]) || 0;
            const inputProductionCost = recursiveCost + workforceCost;
            
            if (inputProductionCost < bestInputCost) {
              bestInputCost = inputProductionCost;
            }
          }
        }
        
        // If no recipe found (tier-0 material), use market price
        if (!foundRecipe || bestInputCost === Infinity) {
          for (let i = 1; i < allData.length; i++) {
            if (allData[i][1] === inputTicker && allData[i][4] === exchange) {
              const askPrice = parseFloat(allData[i][5]) || 0;
              totalCost += amount * askPrice;
              break;
            }
          }
        } else {
          totalCost += amount * bestInputCost;
        }
      }
    }
    return totalCost;
  } catch (e) {
    Logger.log('Error calculating self-production cost: ' + e.toString());
    return 0;
  }
}

// Get exchange comparison data (prices and profitability across all exchanges)
function getExchangeComparison(material, recipe, currentExchange) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return { error: 'Price Analyser Data sheet not found' };
    }
    
    const data = sheet.getDataRange().getValues();
    const exchanges = {};
    
    // Find data for this material across all exchanges
    for (let i = 1; i < data.length; i++) {
      if (data[i][1] === material && (!recipe || data[i][2] === recipe)) {
        const exch = data[i][4];  // Column E: Exchange
        const askPrice = parseFloat(data[i][5]) || 0;
        const bidPrice = parseFloat(data[i][6]) || 0;
        const inputCostAsk = parseFloat(data[i][7]) || 0;
        const workforceCostAsk = parseFloat(data[i][9]) || 0;
        const totalCost = inputCostAsk + workforceCostAsk;
        const profitAsk = askPrice - totalCost;
        const roiAsk = totalCost > 0 ? (profitAsk / totalCost) * 100 : 0;
        
        exchanges[exch] = {
          exchange: exch,
          askPrice: askPrice,
          bidPrice: bidPrice,
          totalCost: totalCost,
          profit: profitAsk,
          roi: roiAsk,
          isCurrent: exch === currentExchange
        };
      }
    }
    
    // Sort by ROI descending
    const sortedExchanges = Object.values(exchanges).sort((a, b) => b.roi - a.roi);
    
    return {
      success: true,
      exchanges: sortedExchanges,
      bestExchange: sortedExchanges[0]
    };
  } catch (error) {
    Logger.log('Error in getExchangeComparison: ' + error.toString());
    return { error: error.toString() };
  }
}

// Get arbitrage opportunities (buy low at one exchange, sell high at another)
function getArbitrageOpportunities(material) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return { error: 'Price Analyser Data sheet not found' };
    }
    
    const data = sheet.getDataRange().getValues();
    const exchangePrices = {};
    
    // Collect prices for this material at each exchange
    for (let i = 1; i < data.length; i++) {
      if (data[i][1] === material) {
        const exch = data[i][4];
        const askPrice = parseFloat(data[i][5]) || 0;  // Buy at Ask
        const bidPrice = parseFloat(data[i][6]) || 0;  // Sell at Bid
        
        if (!exchangePrices[exch]) {
          exchangePrices[exch] = { ask: askPrice, bid: bidPrice };
        }
      }
    }
    
    // Find arbitrage opportunities: Buy at Exchange A (ask), Sell at Exchange B (bid)
    const opportunities = [];
    const exchanges = Object.keys(exchangePrices);
    
    for (let i = 0; i < exchanges.length; i++) {
      for (let j = 0; j < exchanges.length; j++) {
        if (i !== j) {
          const buyExch = exchanges[i];
          const sellExch = exchanges[j];
          const buyPrice = exchangePrices[buyExch].ask;  // Cost to buy
          const sellPrice = exchangePrices[sellExch].bid;  // Revenue from selling
          
          const profit = sellPrice - buyPrice;
          const profitPercent = buyPrice > 0 ? (profit / buyPrice) * 100 : 0;
          
          // Only include profitable opportunities (accounting for ~5% transfer costs)
          if (profitPercent > 5) {
            opportunities.push({
              buyExchange: buyExch,
              sellExchange: sellExch,
              buyPrice: buyPrice,
              sellPrice: sellPrice,
              profit: profit,
              profitPercent: profitPercent
            });
          }
        }
      }
    }
    
    // Sort by profit percent descending
    opportunities.sort((a, b) => b.profitPercent - a.profitPercent);
    
    return {
      success: true,
      opportunities: opportunities,
      count: opportunities.length
    };
  } catch (error) {
    Logger.log('Error in getArbitrageOpportunities: ' + error.toString());
    return { error: error.toString() };
  }
}

// Get calculation data for selected material, exchange, and optionally specific recipe
function getCalculationData(material, exchange, recipe, includeLuxury, selfProduced, planetName) {
  includeLuxury = includeLuxury !== false; // Default true
  selfProduced = selfProduced === true;     // Default false
  planetName = planetName || null;          // Optional planet for extraction
  
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
        let inputCostAsk = parseFloat(data[i][7]) || 0;
        let workforceCostAsk = parseFloat(data[i][9]) || 0;
        
        // Apply efficiency penalty if no luxury (79% efficiency = 1/0.79 = ~1.266x cost)
        if (!includeLuxury) workforceCostAsk *= (1 / 0.79);
        if (selfProduced) inputCostAsk = calculateSelfProductionCost(data[i][2], data, exchange);
        
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
      let inputCostAsk = parseFloat(data[i][7]) || 0;         // Column H: Input Cost Ask
      let inputCostBid = parseFloat(data[i][8]) || 0;         // Column I: Input Cost Bid
      let workforceCostAsk = parseFloat(data[i][9]) || 0;     // Column J: Workforce Cost Ask
      let workforceCostBid = parseFloat(data[i][10]) || 0;    // Column K: Workforce Cost Bid
      
      // Check if this is an extraction recipe
      const recipeStr = data[i][2] || '';
      const isExtraction = recipeStr.startsWith('COL=>') || recipeStr.startsWith('EXT=>') || recipeStr.startsWith('RIG=>');
      
      // Apply planet-specific extraction time adjustment for extraction recipes
      if (isExtraction && planetName) {
        const planetFactor = getPlanetFactor(material, planetName);
        if (planetFactor > 0) {
          // Workforce costs in data are based on BASE extraction time (24h or 48h)
          // Now adjust for the specific planet's concentration factor
          const building = recipeStr.split('=>')[0];
          const baseHours = building === 'RIG' ? 48 : 24;
          
          // Calculate planet-specific extraction time
          const adjustedHours = Math.max(6, Math.min(240, baseHours / planetFactor));
          const timeFactor = adjustedHours / baseHours;
          
          // Adjust workforce costs based on planet-specific extraction time
          workforceCostAsk *= timeFactor;
          workforceCostBid *= timeFactor;
        }
      }
      // If no planet selected for extraction, use base costs (24h or 48h)
      
      // Apply efficiency penalty if no luxury (79% efficiency = 1/0.79 = ~1.266x cost)
      if (!includeLuxury) {
        workforceCostAsk *= (1 / 0.79);
        workforceCostBid *= (1 / 0.79);
      }
      
      // Apply self-production cost
      if (selfProduced) {
        inputCostAsk = calculateSelfProductionCost(data[i][2], data, exchange);
        inputCostBid = inputCostAsk; // Use same for both
      }
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
      const breakevenAskAsk = profitAskAsk !== 0 ? Math.abs(totalCostAsk / profitAskAsk) : 0;
      
      // Scenario 2: Sell at Ask, Buy inputs at Bid
      const profitAskBid = askPrice - totalCostBid;
      const roiAskBid = totalCostBid > 0 ? (profitAskBid / totalCostBid) * 100 : 0;
      const breakevenAskBid = profitAskBid !== 0 ? Math.abs(totalCostBid / profitAskBid) : 0;
      
      // Scenario 3: Sell at Bid, Buy inputs at Ask
      const profitBidAsk = bidPrice - totalCostAsk;
      const roiBidAsk = totalCostAsk > 0 ? (profitBidAsk / totalCostAsk) * 100 : 0;
      const breakevenBidAsk = profitBidAsk !== 0 ? Math.abs(totalCostAsk / profitBidAsk) : 0;
      
      // Scenario 4: Sell at Bid, Buy inputs at Bid
      const profitBidBid = bidPrice - totalCostBid;
      const roiBidBid = totalCostBid > 0 ? (profitBidBid / totalCostBid) * 100 : 0;
      const breakevenBidBid = profitBidBid !== 0 ? Math.abs(totalCostBid / profitBidBid) : 0;
      
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
