// PrUn Arbitrage Calculator
// Enhanced arbitrage functionality for the dedicated arbitrage app

class PrUnArbitrageCalculator {
    constructor() {
        this.allData = [];
        this.arbitrageData = [];
        this.ordersData = [];
        this.isLoading = false;
    }

    // Initialize the calculator
    async initialize() {
        this.isLoading = true;
        try {
            await this.loadData();
            this.arbitrageData = this.computeArbitrageOpportunities();
            this.arbitrageData = this.assignOpportunityLevels(this.arbitrageData);
        } catch (error) {
            console.error('Failed to initialize arbitrage calculator:', error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    // Load data from CSV files
    async loadData() {
        try {
            console.log('Loading data from CSV files...');

            // For debugging, let's try loading with a timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

            // Load orders data (asks/sell orders)
            const ordersResponse = await fetch('/pu-tracker/cache/orders.csv', {
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            console.log('Orders response status:', ordersResponse.status);
            if (!ordersResponse.ok) {
                throw new Error(`HTTP ${ordersResponse.status}: ${ordersResponse.statusText}`);
            }

            const ordersText = await ordersResponse.text();
            console.log('Orders CSV length:', ordersText.length);
            this.ordersData = this.parseCSV(ordersText, ['MaterialTicker', 'ExchangeCode', 'CompanyId', 'CompanyName', 'CompanyCode', 'ItemCount', 'ItemCost']);
            console.log('Parsed orders data:', this.ordersData.length, 'rows');

            // Load bids data (bids/buy orders)
            const bidsResponse = await fetch('/pu-tracker/cache/bids.csv');
            console.log('Bids response status:', bidsResponse.status);
            const bidsText = await bidsResponse.text();
            const bidsData = this.parseCSV(bidsText, ['MaterialTicker', 'ExchangeCode', 'CompanyId', 'CompanyName', 'CompanyCode', 'ItemCount', 'ItemCost']);
            console.log('Parsed bids data:', bidsData.length, 'rows');

            // Combine orders and bids into a unified orders data structure
            this.ordersData = [
                ...this.ordersData.map(order => ({ ...order, Side: 'ask', Price: parseFloat(order.ItemCost), Quantity: parseInt(order.ItemCount), Ticker: order.MaterialTicker, Exchange: order.ExchangeCode })),
                ...bidsData.map(bid => ({ ...bid, Side: 'bid', Price: parseFloat(bid.ItemCost), Quantity: parseInt(bid.ItemCount), Ticker: bid.MaterialTicker, Exchange: bid.ExchangeCode }))
            ];
            console.log('Combined orders data:', this.ordersData.length, 'total orders');

            // Load market data for material names and categories
            const marketResponse = await fetch('/pu-tracker/cache/market_data.csv');
            console.log('Market data response status:', marketResponse.status);
            const marketText = await marketResponse.text();
            this.allData = this.parseMarketDataCSV(marketText);
            console.log('Parsed market data:', this.allData.length, 'rows');

        } catch (error) {
            console.warn('Failed to load real data, using mock data:', error);
            // Generate mock data for development
            this.allData = this.generateMockMarketData();
            this.ordersData = this.generateMockOrdersData();
        }
    }

    // Compute arbitrage opportunities using the same logic as the Python script
    computeArbitrageOpportunities() {
        console.log('Computing arbitrage opportunities...');
        const arbitrageRows = [];
        const exchanges = [...new Set(this.ordersData.map(item => item.Exchange))];
        const tickers = [...new Set(this.ordersData.map(item => item.Ticker))];

        console.log('Found exchanges:', exchanges);
        console.log('Found tickers:', tickers);

        for (const ticker of tickers) {
            for (const buyEx of exchanges) {
                for (const sellEx of exchanges) {
                    if (buyEx === sellEx) continue;

                    const size = this.computeArbitrageOpportunitySize(ticker, buyEx, sellEx);
                    if (size.matchedQty > 0 && size.matches.length > 0) {
                        const totalBuy = size.matches.reduce((sum, match) => sum + (match.askPrice * match.qty), 0);
                        const totalSell = size.matches.reduce((sum, match) => sum + (match.bidPrice * match.qty), 0);
                        const avgBuy = totalBuy / size.matchedQty;
                        const avgSell = totalSell / size.matchedQty;
                        const profitPerUnit = size.totalProfit / size.matchedQty;
                        const roi = avgBuy > 0 ? (profitPerUnit / avgBuy) * 100 : 0;

                        // Get material name from market data
                        const matRows = this.allData.filter(item => item.Ticker === ticker);
                        const name = matRows.length > 0 ? (matRows[0]['Material Name'] || ticker) : ticker;
                        const product = ticker;

                        arbitrageRows.push({
                            ticker: ticker,
                            name: name,
                            product: product,
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

        console.log('Found', arbitrageRows.length, 'arbitrage opportunities');
        return arbitrageRows;
    }

    // Compute arbitrage opportunity size for specific ticker and exchanges
    computeArbitrageOpportunitySize(ticker, buyEx, sellEx) {
        // Get asks from buy exchange (where you buy) - sorted by price ascending
        const asks = this.ordersData
            .filter(order => order.Ticker === ticker && order.Exchange === buyEx && order.Side === 'ask')
            .sort((a, b) => a.Price - b.Price);

        // Get bids from sell exchange (where you sell) - sorted by price descending
        const bids = this.ordersData
            .filter(order => order.Ticker === ticker && order.Exchange === sellEx && order.Side === 'bid')
            .sort((a, b) => b.Price - a.Price);

        // Debug logging
        if (ticker === 'AAR' && buyEx === 'AI1' && sellEx === 'CI1') {
            console.log(`Checking ${ticker}: ${buyEx} -> ${sellEx}`);
            console.log('Asks:', asks.slice(0, 3));
            console.log('Bids:', bids.slice(0, 3));
        }

        let askIdx = 0;
        let bidIdx = 0;
        let matchedQty = 0;
        let totalProfit = 0;
        const matches = [];

        while (askIdx < asks.length && bidIdx < bids.length) {
            const askPrice = asks[askIdx].Price;
            const askQty = asks[askIdx].Quantity;
            const bidPrice = bids[bidIdx].Price;
            const bidQty = bids[bidIdx].Quantity;

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
                asks[askIdx].Quantity -= qty;
                bids[bidIdx].Quantity -= qty;

                if (asks[askIdx].Quantity <= 0) askIdx++;
                if (bids[bidIdx].Quantity <= 0) bidIdx++;
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

    // Assign opportunity levels based on ROI and size
    assignOpportunityLevels(arbitrageData) {
        return arbitrageData.map(item => {
            const roi = item.roi;
            const size = item.size;

            let level = 'Very Low';
            if (roi > 100 && size >= 1000) {
                level = 'Very High';
            } else if (roi > 50 && size >= 500) {
                level = 'High';
            } else if (roi > 20 && size >= 100) {
                level = 'Medium';
            } else if (roi > 5 && size >= 10) {
                level = 'Low';
            }

            // Debug: Show all opportunities regardless of level
            // console.log(`Opportunity: ${item.ticker} ${item.buy_exchange}->${item.sell_exchange}: ROI=${roi.toFixed(2)}%, Size=${size}, Level=${level}`);

            return { ...item, level: level };
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

    // Parse market data CSV with complex structure
    parseMarketDataCSV(csvText) {
        const lines = csvText.trim().split('\n');
        const headers = lines[0].split(',');
        const data = [];

        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',');
            const ticker = values[0];

            // Parse data for each exchange
            const exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1'];
            exchanges.forEach(exchange => {
                const baseIndex = headers.findIndex(h => h.startsWith(`${exchange}-`));
                if (baseIndex !== -1 && values[baseIndex + 5] && values[baseIndex + 5] !== '0') { // Check if bid available
                    data.push({
                        Ticker: ticker,
                        'Material Name': ticker, // Will be updated if we have materials.csv
                        Product: ticker,
                        Exchange: exchange,
                        Ask_Price: parseFloat(values[baseIndex + 2]) || 0,
                        Bid_Price: parseFloat(values[baseIndex + 4]) || 0,
                        Ask_Amount: parseInt(values[baseIndex + 1]) || 0,
                        Bid_Amount: parseInt(values[baseIndex + 3]) || 0
                    });
                }
            });
        }

        return data;
    }

    // Generate mock orders data for development
    generateMockOrdersData() {
        const exchanges = ['NC1', 'IC1', 'CI1', 'AI1'];
        const materials = ['AL', 'CU', 'FE', 'LI', 'TI', 'AU', 'AG', 'PT', 'H2O', 'O2'];
        const orders = [];

        materials.forEach(material => {
            exchanges.forEach(exchange => {
                // Add some ask orders (sell orders) - base price varies by material
                const basePrice = 50 + (materials.indexOf(material) * 20); // Different base prices
                const askPrice = basePrice + Math.random() * 50; // Random price around base
                const askQuantity = Math.floor(Math.random() * 1000) + 100;
                orders.push({
                    Ticker: material,
                    Exchange: exchange,
                    Side: 'ask',
                    Price: askPrice,
                    Quantity: askQuantity,
                    CompanyId: 'COMP' + Math.floor(Math.random() * 100),
                    CompanyName: 'Company ' + Math.floor(Math.random() * 100),
                    CompanyCode: 'C' + Math.floor(Math.random() * 100)
                });

                // Add bid orders (buy orders) - some higher than asks on other exchanges to create arbitrage
                let bidPrice;
                if (exchange === 'AI1') {
                    // Make AI1 bids higher to create arbitrage opportunities
                    bidPrice = basePrice + 30 + Math.random() * 50; // Higher bids
                } else {
                    bidPrice = basePrice + Math.random() * 30; // Lower bids on other exchanges
                }
                const bidQuantity = Math.floor(Math.random() * 1000) + 100;
                orders.push({
                    Ticker: material,
                    Exchange: exchange,
                    Side: 'bid',
                    Price: bidPrice,
                    Quantity: bidQuantity,
                    CompanyId: 'COMP' + Math.floor(Math.random() * 100),
                    CompanyName: 'Company ' + Math.floor(Math.random() * 100),
                    CompanyCode: 'C' + Math.floor(Math.random() * 100)
                });
            });
        });

        console.log('Generated mock orders with arbitrage opportunities');
        return orders;
    }

    // Generate mock market data for testing
    generateMockMarketData() {
        return [
            { Ticker: 'AL', 'Material Name': 'Aluminum', CategoryName: 'Minerals', Price: 100.0, Supply: 1000, Demand: 800 },
            { Ticker: 'CU', 'Material Name': 'Copper', CategoryName: 'Minerals', Price: 150.0, Supply: 800, Demand: 900 },
            { Ticker: 'FE', 'Material Name': 'Iron', CategoryName: 'Minerals', Price: 80.0, Supply: 1200, Demand: 1100 },
            { Ticker: 'LI', 'Material Name': 'Lithium', CategoryName: 'Minerals', Price: 200.0, Supply: 500, Demand: 600 },
            { Ticker: 'TI', 'Material Name': 'Titanium', CategoryName: 'Minerals', Price: 300.0, Supply: 300, Demand: 400 },
            { Ticker: 'AU', 'Material Name': 'Gold', CategoryName: 'Minerals', Price: 500.0, Supply: 100, Demand: 150 },
            { Ticker: 'AG', 'Material Name': 'Silver', CategoryName: 'Minerals', Price: 250.0, Supply: 200, Demand: 180 },
            { Ticker: 'PT', 'Material Name': 'Platinum', CategoryName: 'Minerals', Price: 600.0, Supply: 50, Demand: 80 },
            { Ticker: 'H2O', 'Material Name': 'Water', CategoryName: 'Resources', Price: 10.0, Supply: 5000, Demand: 4500 },
            { Ticker: 'O2', 'Material Name': 'Oxygen', CategoryName: 'Resources', Price: 5.0, Supply: 8000, Demand: 7500 },
            { Ticker: 'CO2', 'Material Name': 'Carbon Dioxide', CategoryName: 'Resources', Price: 2.0, Supply: 10000, Demand: 9000 },
            { Ticker: 'CH4', 'Material Name': 'Methane', CategoryName: 'Resources', Price: 15.0, Supply: 2000, Demand: 1800 },
            { Ticker: 'NH3', 'Material Name': 'Ammonia', CategoryName: 'Resources', Price: 25.0, Supply: 1500, Demand: 1600 },
            { Ticker: 'H2', 'Material Name': 'Hydrogen', CategoryName: 'Resources', Price: 8.0, Supply: 3000, Demand: 2800 },
            { Ticker: 'N2', 'Material Name': 'Nitrogen', CategoryName: 'Resources', Price: 3.0, Supply: 12000, Demand: 11000 },
            { Ticker: 'HE', 'Material Name': 'Helium', CategoryName: 'Resources', Price: 1000.0, Supply: 20, Demand: 30 },
            { Ticker: 'AR', 'Material Name': 'Argon', CategoryName: 'Resources', Price: 50.0, Supply: 800, Demand: 700 },
            { Ticker: 'NE', 'Material Name': 'Neon', CategoryName: 'Resources', Price: 200.0, Supply: 100, Demand: 120 },
            { Ticker: 'XE', 'Material Name': 'Xenon', CategoryName: 'Resources', Price: 1500.0, Supply: 10, Demand: 15 },
            { Ticker: 'KR', 'Material Name': 'Krypton', CategoryName: 'Resources', Price: 800.0, Supply: 25, Demand: 35 }
        ];
    }
}

// Export for use in the main app
window.PrUnArbitrageCalculator = PrUnArbitrageCalculator;