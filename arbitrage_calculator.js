// PrUn Arbitrage Calculator
// Enhanced arbitrage functionality for the dedicated arbitrage app

class PrUnArbitrageCalculator {
    constructor(options = {}) {
        this.allData = [];
        this.arbitrageData = [];
        this.ordersData = [];
        this.isLoading = false;

        // Configuration
        this.googleAppsScriptUrl = options.googleAppsScriptUrl ||
            'https://script.google.com/macros/s/1-msZsudVPRW4aJcuPbFQAC8XhSj6Fc0FH52nefiHqn3e0r1TvklxMUq2/exec';
    }

    // Initialize the calculator
    async initialize() {
        this.isLoading = true;
        try {
            await this.loadFromGoogleAppsScript();
            // Arbitrage data is computed locally now
        } catch (error) {
            console.error('Failed to initialize arbitrage calculator:', error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    // Load data from Google Apps Script
    async loadFromGoogleAppsScript() {
        console.log('Loading data from Google Apps Script...');

        try {
            // Load data from Google Apps Script
            const response = await fetch(this.googleAppsScriptUrl + '?action=getArbitrageData');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Process the data
            this.ordersData = data.orders || [];
            this.arbitrageData = this.computeArbitrageOpportunities(this.ordersData, [], []);

            // Create mock allData for compatibility
            this.allData = this.createMockMarketDataFromArbitrageData(this.arbitrageData);

            console.log('Data loaded successfully from Google Apps Script!');
            console.log('Arbitrage opportunities:', this.arbitrageData.length);

        } catch (error) {
            console.error('Failed to load data from Google Apps Script:', error);
            throw new Error(`Data loading failed: ${error.message}`);
        }
    }

    // Compute arbitrage opportunities using order book crossing
    computeArbitrageOpportunities(ordersData, bidsData, materialsData) {
        const arbitrageRows = [];
        const exchanges = ['AI1', 'CI1', 'CI2', 'IC1', 'NC1', 'NC2'];
        const tickers = new Set();

        // Collect all unique tickers
        ordersData.forEach(row => {
            if (row.MaterialTicker) tickers.add(row.MaterialTicker);
        });
        bidsData.forEach(row => {
            if (row.MaterialTicker) tickers.add(row.MaterialTicker);
        });

        // Create material name lookup
        const materialNames = {};
        materialsData.forEach(row => {
            if (row.Ticker && row.Name) {
                materialNames[row.Ticker] = row.Name;
            }
        });

        for (const ticker of tickers) {
            for (const buyEx of exchanges) {
                for (const sellEx of exchanges) {
                    if (buyEx === sellEx) continue;

                    const size = this.computeArbitrageOpportunitySizeLocal(ticker, buyEx, sellEx, ordersData, bidsData);
                    if (size.matchedQty > 0 && size.matches.length > 0) {
                        const totalBuy = size.matches.reduce((sum, match) => sum + (match.askPrice * match.qty), 0);
                        const totalSell = size.matches.reduce((sum, match) => sum + (match.bidPrice * match.qty), 0);
                        const avgBuy = totalBuy / size.matchedQty;
                        const avgSell = totalSell / size.matchedQty;
                        const profitPerUnit = size.totalProfit / size.matchedQty;
                        const roi = avgBuy > 0 ? (profitPerUnit / avgBuy) * 100 : 0;

                        const name = materialNames[ticker] || ticker;

                        arbitrageRows.push({
                            ticker: ticker,
                            name: name,
                            product: ticker,
                            buy_exchange: buyEx,
                            sell_exchange: sellEx,
                            buy_price: Number(avgBuy.toFixed(2)),
                            sell_price: Number(avgSell.toFixed(2)),
                            profit: Number(profitPerUnit.toFixed(2)),
                            roi: Number(roi.toFixed(4)),
                            size: Math.floor(size.matchedQty),
                            level: null // Will be assigned later
                        });
                    }
                }
            }
        }

        // Assign opportunity levels
        const opportunitiesWithLevels = this.assignOpportunityLevels(arbitrageRows);

        // Sort by profit descending
        return opportunitiesWithLevels.sort((a, b) => b.profit - a.profit);
    }

    // Compute arbitrage opportunity size for specific ticker and exchanges (local version)
    computeArbitrageOpportunitySizeLocal(ticker, buyEx, sellEx, ordersData, bidsData) {
        // Get asks from buy exchange (where you buy) - sorted by price ascending
        const asks = ordersData
            .filter(row => row.MaterialTicker === ticker && row.ExchangeCode === buyEx)
            .map(row => ({
                price: parseFloat(row.ItemCost),
                quantity: parseInt(row.ItemCount)
            }))
            .sort((a, b) => a.price - b.price);

        // Get bids from sell exchange (where you sell) - sorted by price descending
        const bids = bidsData
            .filter(row => row.MaterialTicker === ticker && row.ExchangeCode === sellEx)
            .map(row => ({
                price: parseFloat(row.ItemCost),
                quantity: parseInt(row.ItemCount)
            }))
            .sort((a, b) => b.price - a.price);

        let askIdx = 0;
        let bidIdx = 0;
        let matchedQty = 0;
        let totalProfit = 0;
        const matches = [];

        while (askIdx < asks.length && bidIdx < bids.length) {
            const askPrice = asks[askIdx].price;
            const askQty = asks[askIdx].quantity;
            const bidPrice = bids[bidIdx].price;
            const bidQty = bids[bidIdx].quantity;

            if (bidPrice >= askPrice) {
                const qty = Math.min(askQty, bidQty);
                const profit = (bidPrice - askPrice) * qty;

                matches.push({
                    askPrice: askPrice,
                    bidPrice: bidPrice,
                    qty: qty
                });

                matchedQty += qty;
                totalProfit += profit;

                // Update quantities
                asks[askIdx].quantity -= qty;
                bids[bidIdx].quantity -= qty;

                if (asks[askIdx].quantity <= 0) askIdx++;
                if (bids[bidIdx].quantity <= 0) bidIdx++;
            } else {
                break;
            }
        }

        return {
            matchedQty: matchedQty,
            totalProfit: totalProfit,
            matches: matches
        };
    }

    // Assign opportunity levels based on ROI thresholds
    assignOpportunityLevels(opportunities) {
        return opportunities.map(opp => {
            let level = 'Low';
            if (opp.roi >= 10) {
                level = 'High';
            } else if (opp.roi >= 5) {
                level = 'Medium';
            }
            return { ...opp, level: level };
        });
    }

    // Filter arbitrage data
    filterData(filters) {
        return this.arbitrageData.filter(item => {
            if (filters.material && item.ticker !== filters.material) return false;
            if (filters.buyExchange && item.buy_exchange !== filters.buyExchange) return false;
            if (filters.sellExchange && item.sell_exchange !== filters.sellExchange) return false;
            if (filters.minProfit && item.profit < filters.minProfit) return false;
            if (filters.minRoi && item.roi < filters.minRoi) return false;
            return true;
        });
    }

    // Sort data
    sortData(data, sortBy, sortDirection) {
        return [...data].sort((a, b) => {
            let aVal = a[sortBy];
            let bVal = b[sortBy];

            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }

            if (sortDirection === 'asc') {
                return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
            } else {
                return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
            }
        });
    }

    // Get statistics
    getStatistics(data) {
        if (data.length === 0) {
            return {
                totalOpportunities: 0,
                avgProfit: 0,
                avgRoi: 0,
                totalVolume: 0
            };
        }

        const totalOpportunities = data.length;
        const avgProfit = data.reduce((sum, item) => sum + item.profit, 0) / data.length;
        const avgRoi = data.reduce((sum, item) => sum + item.roi, 0) / data.length;
        const totalVolume = data.reduce((sum, item) => sum + item.size, 0);

        return {
            totalOpportunities,
            avgProfit: Number(avgProfit.toFixed(2)),
            avgRoi: Number(avgRoi.toFixed(2)),
            totalVolume
        };
    }

    // Parse CSV text into array of objects
    parseCSV(csvText, headers) {
        const lines = csvText.trim().split('\n');
        const data = [];

        for (let i = 1; i < lines.length; i++) { // Skip header row
            const line = lines[i].trim();
            if (!line) continue; // Skip empty lines

            // Simple CSV parsing - split on commas
            // Note: This is basic parsing and may not handle quoted fields with commas
            const values = line.split(',');

            if (values.length >= headers.length) {
                const obj = {};
                headers.forEach((header, index) => {
                    obj[header] = values[index] || '';
                });
                data.push(obj);
            }
        }

        return data;
    }

    // Create mock orders data from arbitrage opportunities for compatibility
    createMockOrdersFromArbitrageData(arbitrageData) {
        const orders = [];

        // Create minimal order data for each unique ticker/exchange combination
        arbitrageData.forEach(opp => {
            // Add buy order (ask) for buy exchange
            orders.push({
                Ticker: opp.ticker,
                Exchange: opp.buy_exchange,
                Side: 'ask',
                Price: opp.buy_price,
                Quantity: opp.size,
                CompanyId: 'MOCK_BUY',
                CompanyName: 'Mock Buyer',
                CompanyCode: 'MB'
            });

            // Add sell order (bid) for sell exchange
            orders.push({
                Ticker: opp.ticker,
                Exchange: opp.sell_exchange,
                Side: 'bid',
                Price: opp.sell_price,
                Quantity: opp.size,
                CompanyId: 'MOCK_SELL',
                CompanyName: 'Mock Seller',
                CompanyCode: 'MS'
            });
        });

        return orders;
    }

    // Create mock market data from arbitrage opportunities for compatibility
    createMockMarketDataFromArbitrageData(arbitrageData) {
        const marketData = [];
        const uniqueTickers = [...new Set(arbitrageData.map(opp => opp.ticker))];

        uniqueTickers.forEach(ticker => {
            const opp = arbitrageData.find(o => o.ticker === ticker);
            if (opp) {
                marketData.push({
                    Ticker: ticker,
                    'Material Name': opp.name || ticker,
                    CategoryName: 'Unknown',
                    Price: opp.buy_price,
                    Supply: 1000,
                    Demand: 1000
                });
            }
        });

        return marketData;
    }
}

// Export for use in the main app (only if window is available)
if (typeof window !== 'undefined') {
    window.PrUnArbitrageCalculator = PrUnArbitrageCalculator;
}

// Also export as a module if in a module context
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PrUnArbitrageCalculator;
}