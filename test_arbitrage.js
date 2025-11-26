// Test script to verify arbitrage calculator
const { PrUnArbitrageCalculator } = require('./arbitrage_calculator.js');

async function testCalculator() {
    console.log('Testing arbitrage calculator...');

    const calculator = new PrUnArbitrageCalculator();

    try {
        await calculator.initialize();

        console.log('Orders data length:', calculator.ordersData.length);
        console.log('All data length:', calculator.allData.length);
        console.log('Arbitrage opportunities found:', calculator.arbitrageData.length);

        // Show first few opportunities
        calculator.arbitrageData.slice(0, 5).forEach((opp, i) => {
            console.log(`${i+1}. ${opp.ticker}: ${opp.buy_exchange} -> ${opp.sell_exchange}, Profit: ${opp.profit}, ROI: ${opp.roi}%, Size: ${opp.size}`);
        });

    } catch (error) {
        console.error('Test failed:', error);
    }
}

testCalculator();