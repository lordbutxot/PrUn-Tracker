// ====================================================================
// GOOGLE APPS SCRIPT - INTERACTIVE PRICE ANALYSER WEB APP
// ====================================================================
// 
// FEATURES:
// - 💎 Best ROI badges with color-coded comparison (green/red/blue)
// - 📊 Real-time traded volume display across all sections
// - 🌍 Planet-based extraction building filtering
// - ⏱️ Last update timestamp with timezone support
// - 📱 Mobile responsive design with badge stacking
// - ✅ Corrected fertility calculations using PCT formula
// - 🔄 Unique material recommendations (deduplicated)
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
// DATA REQUIREMENTS:
// - Price Analyser Data sheet (15 columns including Traded Volume in column O)
// - Metadata sheet (Key-Value pairs with Last Data Update timestamp)
// - Planet Resources sheet (Planet, Ticker, Type, Factor, Fertility columns)
// - Bids sheet (for breakeven calculations)
//
// ====================================================================

// Main function to serve the HTML page
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('PrUn Price Analyser')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL); // Allow embedding
}

// TEST FUNCTION - Analyze byproduct recipes
function analyzeByproductRecipes() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return 'ERROR: Price Analyser Data sheet not found';
    }
    
    const data = sheet.getDataRange().getValues();
    const headers = data[0];
    
    // Step 1: Identify materials that have recipes (producers)
    const materialsWithRecipes = new Set();
    const allMaterials = new Set();
    const recipes = [];
    
    // Skip header row
    for (let i = 1; i < data.length; i++) {
      const ticker = data[i][1]; // Column B: ticker
      const recipe = data[i][2]; // Column C: recipe
      
      if (ticker) {
        allMaterials.add(ticker);
        
        if (recipe && recipe !== 'N/A' && recipe !== '') {
          materialsWithRecipes.add(ticker);
          recipes.push({
            ticker: ticker,
            recipe: recipe,
            row: i
          });
        }
      }
    }
    
    // Step 2: Identify byproducts (materials that appear but have no recipes)
    const byproducts = new Set();
    for (const material of allMaterials) {
      if (!materialsWithRecipes.has(material)) {
        byproducts.add(material);
      }
    }
    
    // Step 3: Find recipes where ALL outputs are byproducts
    const byproductRecipes = [];
    
    for (const recipeData of recipes) {
      const recipe = recipeData.recipe;
      
      if (recipe.includes('=>')) {
        const outputPart = recipe.split('=>')[1];
        if (outputPart) {
          const outputs = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[2] : item;
          });
          
          // Check if ALL outputs are byproducts
          const allOutputsAreByproducts = outputs.every(output => byproducts.has(output));
          
          if (allOutputsAreByproducts) {
            byproductRecipes.push({
              recipe: recipe,
              building: recipe.split(':')[0],
              outputs: outputs,
              producer: recipeData.ticker
            });
          }
        }
      }
    }
    
    // Step 4: Generate report
    let report = '=== BYPRODUCT RECIPE ANALYSIS ===\n\n';
    report += 'Total materials: ' + allMaterials.size + '\n';
    report += 'Materials with recipes: ' + materialsWithRecipes.size + '\n';
    report += 'Byproducts (no recipes): ' + byproducts.size + '\n\n';
    
    report += 'Byproducts: ' + Array.from(byproducts).sort().join(', ') + '\n\n';
    
    report += 'Recipes producing ONLY byproducts: ' + byproductRecipes.length + '\n\n';
    
    byproductRecipes.forEach((item, index) => {
      report += (index + 1) + '. ' + item.recipe + '\n';
      report += '   Building: ' + item.building + '\n';
      report += '   Outputs (byproducts): ' + item.outputs.join(', ') + '\n';
      report += '   Producer material: ' + item.producer + '\n\n';
    });
    
    // Look for specific example: CHP => NA + CL
    const chpRecipes = byproductRecipes.filter(item => item.building === 'CHP' && 
                                                      item.outputs.includes('NA') && 
                                                      item.outputs.includes('CL'));
    
    if (chpRecipes.length > 0) {
      report += '=== SPECIFIC EXAMPLE: CHP => NA + CL ===\n';
      report += 'Found ' + chpRecipes.length + ' CHP recipes producing NA and CL as byproducts\n';
      chpRecipes.forEach(item => {
        report += 'Recipe: ' + item.recipe + '\n';
      });
    } else {
      report += '=== SPECIFIC EXAMPLE: CHP => NA + CL ===\n';
      report += 'No CHP recipes found that produce NA and CL as byproducts\n';
    }
    
    Logger.log(report);
    return report;
    
  } catch (error) {
    Logger.log('Error in analyzeByproductRecipes: ' + error.toString());
    return 'Error: ' + error.toString();
  }
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
    
    // DEBUG: Log headers to verify column structure
    Logger.log('Price Analyser Data headers: ' + JSON.stringify(headers));
    Logger.log('Column O (index 14) header: ' + headers[14]);
    if (data.length > 1) {
      Logger.log('Sample row 1 column O value: ' + data[1][14]);
    }
    
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
        supply: parseFloat(data[i][12]) || 0,    // Column M
        demand: parseFloat(data[i][13]) || 0,    // Column N
        traded: parseFloat(data[i][14]) || 0     // Column O
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
    
    // Load planet resources for extraction recipes AND fertility for farming
    const planetSheet = ss.getSheetByName('Planet Resources');
    const planets = [];
    const fertility = [];
    const fertilityMap = {}; // Track unique planets with fertility
    
    if (planetSheet) {
      const planetData = planetSheet.getDataRange().getValues();
      const headers = planetData[0];
      Logger.log('Planet Resources headers: ' + JSON.stringify(headers));
      Logger.log('Total planet resource rows: ' + (planetData.length - 1));
      
      // Skip header row (Key, Planet, Ticker, Type, Factor, Fertility)
      for (let i = 1; i < planetData.length; i++) {
        planets.push({
          planet: planetData[i][1],    // Planet name
          ticker: planetData[i][2],    // Material ticker
          factor: parseFloat(planetData[i][4]) || 0  // Concentration factor
        });
        
        // Extract fertility data (column 5) if available
        const planetName = planetData[i][1];
        const fertilityValue = parseFloat(planetData[i][5]);
        
        // DEBUG: Log first few fertility values
        if (i <= 5) {
          Logger.log('Row ' + i + ': Planet=' + planetName + ', Column[5]=' + planetData[i][5] + ', Parsed=' + fertilityValue);
        }
        
        // Include ALL planets with valid fertility values (even highly negative ones)
        // With efficiency bonuses, farming is theoretically possible on any planet with fertility data
        // Negative fertility = slower farming, but user can decide viability based on their bonuses
        if (!isNaN(fertilityValue) && !fertilityMap[planetName]) {
          fertilityMap[planetName] = fertilityValue;
          fertility.push({
            planet: planetName,
            fertility: fertilityValue
          });
        }
      }
      Logger.log('Loaded ' + planets.length + ' planet resources and ' + fertility.length + ' planets with fertility data');
      if (fertility.length > 0) {
        Logger.log('Sample fertility data: ' + JSON.stringify(fertility.slice(0, 5)));
        Logger.log('Fertility range: Min=' + Math.min(...fertility.map(f => f.fertility)).toFixed(3) + 
                   ', Max=' + Math.max(...fertility.map(f => f.fertility)).toFixed(3));
        Logger.log('Planets with negative fertility: ' + fertility.filter(f => f.fertility < 0).length);
      } else {
        Logger.log('WARNING: No fertility data found! Check if Fertility column exists and has data.');
      }
    }
    
    // Try to get last update timestamp from a metadata cell
    // Look for "Last Updated" in the Price Analyser Data sheet or use file timestamp
    let lastUpdated = null;
    try {
      // Check if there's a "Metadata" sheet with timestamp
      const metadataSheet = ss.getSheetByName('Metadata');
      if (metadataSheet) {
        const metadataData = metadataSheet.getDataRange().getValues();
        for (let i = 0; i < metadataData.length; i++) {
          if (metadataData[i][0] === 'Last Data Update') {
            lastUpdated = metadataData[i][1];
            break;
          }
        }
      }
    } catch (e) {
      Logger.log('Could not read metadata timestamp: ' + e);
    }
    
    return {
      success: true,
      data: rows,
      bids: bids,
      planets: planets,
      fertility: fertility,
      rowCount: rows.length,
      lastUpdated: lastUpdated
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

  // Skip header row, get materials from column B (tickers) or parse from recipes
  for (let i = 1; i < data.length; i++) {
    let material = data[i][1]; // Column B = Material ticker or recipe

    if (material && typeof material === 'string') {
      // Check if it's a recipe format (contains =>)
      if (material.includes('=>')) {
        // Parse outputs from recipe: "CHP:1xH2O-3xHAL=>1xCL-2xNA" -> ["CL", "NA"]
        const outputPart = material.split('=>')[1];
        if (outputPart) {
          const outputs = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[2] : item;
          });
          // Add each output material
          outputs.forEach(output => materialsSet.add(output));
        }
      } else {
        // Regular ticker
        materialsSet.add(material);
      }
    }
  }

  return Array.from(materialsSet).sort();
}

// Get materials filtered by category
function getMaterialsByCategory(category) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Price Analyser Data');

  if (!sheet) {
    return ['Error: Price Analyser Data sheet not found'];
  }

  const data = sheet.getDataRange().getValues();
  const materialsSet = new Set();

  // Building to category mapping
  const buildingCategories = {
    // Manufacturing
    'AAF': 'manufacturing', 'APF': 'manufacturing', 'BMP': 'manufacturing', 'CLF': 'manufacturing', 'MCA': 'manufacturing', 'PPF': 'manufacturing', 'SCA': 'manufacturing', 'SKF': 'manufacturing', 'SPP': 'manufacturing', 'WPL': 'manufacturing', 'SPF': 'manufacturing',
    // Electronics
    'CLR': 'electronics', 'DRS': 'electronics', 'ECA': 'electronics', 'EDM': 'electronics', 'ELP': 'electronics', 'SD': 'electronics', 'SE': 'electronics', 'SL': 'electronics', 'PHF': 'electronics',
    // Chemistry
    'AML': 'chemistry', 'CHP': 'chemistry', 'EEP': 'chemistry', 'LAB': 'chemistry', 'POL': 'chemistry', 'TNP': 'chemistry',
    // Metallurgy
    'ASM': 'metallurgy', 'FS': 'metallurgy', 'GF': 'metallurgy', 'HWP': 'metallurgy', 'SME': 'metallurgy',
    // Construction
    'PP1': 'construction', 'PP2': 'construction', 'PP3': 'construction', 'PP4': 'construction', 'UPF': 'construction', 'WEL': 'construction', 'PAC': 'construction',
    // Food Industries
    'FER': 'food industries', 'FP': 'food industries', 'HYF': 'food industries', 'IVP': 'food industries', 'ORC': 'food industries',
    // Agriculture
    'FRM': 'agriculture',
    // Fuel Refining
    'REF': 'fuel',
    // Resource Extraction
    'COL': 'extraction', 'EXT': 'extraction', 'RIG': 'extraction',
    // Chemistry (INC produces carbon)
    'INC': 'chemistry'
  };

  // Skip header row, get materials from column B (tickers) or parse from recipes
  for (let i = 1; i < data.length; i++) {
    let material = data[i][1]; // Column B = Material ticker or recipe
    const recipe = data[i][2] || ''; // Column C = Recipe

    if (material && typeof material === 'string') {
      let materialTicker = material;
      let materialCategory = '';

      // Check if it's a recipe format (contains =>)
      if (material.includes('=>')) {
        // Parse outputs from recipe: "CHP:1xH2O-3xHAL=>1xCL-2xNA" -> ["CL", "NA"]
        const outputPart = material.split('=>')[1];
        if (outputPart) {
          const outputs = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[2] : item;
          });
          // For recipes, we add each output material
          outputs.forEach(output => {
            // Get category from building in recipe
            const building = recipe.split(':')[0];
            const cat = buildingCategories[building] || 'other';
            if (category === 'all' || cat === category) {
              materialsSet.add(output);
            }
          });
        }
      } else {
        // Regular ticker - get category from recipe building
        const building = recipe.split(':')[0];
        const cat = buildingCategories[building] || 'other';
        if (category === 'all' || cat === category) {
          materialsSet.add(material);
        }
      }
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
  
  // Skip header row, get exchanges from column E
  for (let i = 1; i < data.length; i++) {
    const exchange = data[i][4]; // Column E = Exchange
    if (exchange && typeof exchange === 'string') {
      exchangesSet.add(exchange);
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
    
    // Find all recipes for this material (column B is Ticker or recipe, column C is Recipe)
    for (let i = 1; i < data.length; i++) {
      const tickerOrRecipe = data[i][1]; // Column B
      const recipeKey = data[i][2]; // Column C
      
      let matchesMaterial = false;
      
      // Check if ticker matches
      if (tickerOrRecipe === material) {
        matchesMaterial = true;
      }
      // Check if recipe outputs contain the material
      else if (recipeKey && recipeKey.includes('=>')) {
        const outputPart = recipeKey.split('=>')[1];
        if (outputPart) {
          const outputs = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[2] : item;
          });
          if (outputs.includes(material)) {
            matchesMaterial = true;
          }
        }
      }
      
      if (matchesMaterial && recipeKey) {
        // Extract building prefix from recipe (e.g., "BMP:1xC-2xH=>200xPE" -> "BMP")
        const building = recipeKey.split(':')[0];
        
        // Create a visual display label showing only material tickers
        let visualLabel = recipeKey;
        if (recipeKey.includes('=>')) {
          const parts = recipeKey.split('=>');
          const inputPart = parts[0].split(':')[1] || parts[0];
          const outputPart = parts[1];
          
          // Parse inputs: extract tickers only
          const inputTickers = inputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[2] : item;
          });
          
          // Parse outputs: extract tickers only
          const outputTickers = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[2] : item;
          });
          
          // Create visual format: "INPUT1 + INPUT2 → OUTPUT1"
          const inputsStr = inputTickers.join(' + ');
          const outputsStr = outputTickers.join(' + ');
          visualLabel = inputsStr + ' → ' + outputsStr;
        }
        
        recipes.push({
          key: recipeKey,
          label: visualLabel,
          building: building
        });
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

// Get building comparison - compare all recipes for the same building
function getBuildingComparison(currentRecipe, exchange, includeLuxury) {
  try {
    includeLuxury = includeLuxury !== false; // Default true
    
    if (!currentRecipe || !currentRecipe.includes(':')) {
      return { error: 'Invalid recipe format' };
    }
    
    // Extract building from current recipe (e.g., "BMP:1xC-2xH=>200xPE" -> "BMP")
    const building = currentRecipe.split(':')[0];
    
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName('Price Analyser Data');
    
    if (!sheet) {
      return { error: 'Price Analyser Data sheet not found' };
    }
    
    const data = sheet.getDataRange().getValues();
    const buildingRecipes = [];
    const seenMaterials = new Set();
    
    // Find all recipes for this building at the specified exchange
    for (let i = 1; i < data.length; i++) {
      const recipeString = data[i][2] || ''; // Column C: Recipe
      const material = data[i][1]; // Column B: Ticker
      const exch = data[i][4]; // Column E: Exchange
      
      // Check if recipe is for the same building and exchange
      if (recipeString.startsWith(building + ':') && exch === exchange && !seenMaterials.has(material)) {
        seenMaterials.add(material);
        
        const askPrice = parseFloat(data[i][5]) || 0;
        const bidPrice = parseFloat(data[i][6]) || 0;
        let inputCostAsk = parseFloat(data[i][7]) || 0;
        let workforceCostAsk = parseFloat(data[i][9]) || 0;
        
        // Apply efficiency penalty if no luxury
        if (!includeLuxury) {
          workforceCostAsk *= (1 / 0.79);
        }
        
        const totalCostAsk = inputCostAsk + workforceCostAsk;
        const profitAsk = askPrice - totalCostAsk;
        const roiAsk = totalCostAsk > 0 ? (profitAsk / totalCostAsk) * 100 : 0;
        
        // Parse recipe outputs for display
        let outputDisplay = '';
        if (recipeString.includes('=>')) {
          const outputPart = recipeString.split('=>')[1];
          outputDisplay = outputPart.split('-').map(item => {
            const match = item.match(/(\d+)x([A-Z]+)/);
            return match ? match[1] + ' ' + match[2] : item;
          }).join(', ');
        }
        
        buildingRecipes.push({
          material: material,
          materialName: data[i][3] || material, // Column D: Material Name
          recipe: recipeString,
          output: outputDisplay,
          askPrice: askPrice,
          bidPrice: bidPrice,
          inputCost: inputCostAsk,
          workforceCost: workforceCostAsk,
          totalCost: totalCostAsk,
          profit: profitAsk,
          roi: roiAsk,
          isCurrent: recipeString === currentRecipe
        });
      }
    }
    
    if (buildingRecipes.length === 0) {
      return { error: 'No recipes found for building ' + building };
    }
    
    // Sort by profit descending
    buildingRecipes.sort((a, b) => b.profit - a.profit);
    
    return {
      success: true,
      building: building,
      recipes: buildingRecipes,
      count: buildingRecipes.length,
      bestRecipe: buildingRecipes[0]
    };
    
  } catch (error) {
    Logger.log('Error in getBuildingComparison: ' + error.toString());
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
      
      // Check if this is an extraction recipe
      const recipeStr = data[i][2] || '';
      const amountPerRecipe = parseFloat(data[i][11]) || 1;   // Column L: Amount per Recipe
      
      // If input cost is 0, try to calculate it from recipe inputs
      if (inputCostAsk === 0 && recipeStr && recipeStr.includes('=>')) {
        try {
          const parts = recipeStr.split('=>');
          const inputPart = parts[0].split(':')[1] || parts[0];
          const inputs = inputPart.split('-');
          let totalInputCostAsk = 0;
          let totalInputCostBid = 0;
          
          for (let inputStr of inputs) {
            const match = inputStr.match(/(\d+)x([A-Z]+)/);
            if (match) {
              const amount = parseFloat(match[1]);
              const inputTicker = match[2];
              
              // Find the ask/bid price for this input on the same exchange
              for (let j = 1; j < data.length; j++) {
                if (data[j][1] === inputTicker && data[j][4] === exchange) {
                  const inputAskPrice = parseFloat(data[j][5]) || 0;
                  const inputBidPrice = parseFloat(data[j][6]) || 0;
                  totalInputCostAsk += amount * inputAskPrice;
                  totalInputCostBid += amount * inputBidPrice;
                  break;
                }
              }
            }
          }
          
          // Divide by output amount per recipe
          inputCostAsk = totalInputCostAsk / amountPerRecipe;
          inputCostBid = totalInputCostBid / amountPerRecipe;
        } catch (e) {
          Logger.log('Error calculating input cost for ' + material + ': ' + e.toString());
        }
      }
      let workforceCostAsk = parseFloat(data[i][9]) || 0;     // Column J: Workforce Cost Ask
      let workforceCostBid = parseFloat(data[i][10]) || 0;    // Column K: Workforce Cost Bid
      
      const isExtraction = recipeStr.startsWith('COL=>') || recipeStr.startsWith('EXT=>') || recipeStr.startsWith('RIG=>');
      
      // Apply planet-specific extraction calculation for extraction recipes (Official PCT Formula)
      if (isExtraction && planetName) {
        const planetFactor = getPlanetFactor(material, planetName);
        if (planetFactor > 0) {
          const building = recipeStr.split('=>')[0];
          
          // Step 1: Calculate daily extraction
          const multiplier = (building === 'COL') ? 0.6 : 0.7;
          const dailyExtraction = (planetFactor * 100) * multiplier;
          
          // Step 2: Base cycle time (in hours)
          const baseCycleTime = (building === 'RIG') ? 4.8 : (building === 'COL') ? 6 : 12;
          
          // Step 3: Units per cycle
          const cyclesPerDay = 24 / baseCycleTime;
          const unitsPerCycle = dailyExtraction / cyclesPerDay;
          
          // Step 4: Round up and adjust time
          const roundedUnits = Math.ceil(unitsPerCycle);
          const remainder = roundedUnits - unitsPerCycle;
          const adjustedTime = baseCycleTime + (baseCycleTime * (remainder / unitsPerCycle));
          
          // Note: Efficiency will be applied separately below
          // The data has workforce costs for BASE cycle time, we need to adjust
          const dataBaseCycleTime = (building === 'RIG') ? 4.8 : (building === 'COL') ? 6 : 12;
          const timeFactor = adjustedTime / dataBaseCycleTime;
          
          // Adjust workforce costs based on actual extraction time
          workforceCostAsk *= timeFactor;
          workforceCostBid *= timeFactor;
        }
      }
      // If no planet selected for extraction, use base costs
      
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
      const supply = parseFloat(data[i][12]) || 0;            // Column M: Supply
      const demand = parseFloat(data[i][13]) || 0;            // Column N: Demand
      const traded = parseFloat(data[i][14]) || 0;            // Column O: Traded Volume
      
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
        demand: demand,
        traded: traded
        };
    }
}
