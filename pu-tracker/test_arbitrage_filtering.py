"""
Test script to verify arbitrage filtering logic for exchange-specific reports.
"""

import pandas as pd
import sys
import os

def test_arbitrage_filtering():
    """Test the arbitrage filtering logic."""
    print("Testing arbitrage filtering logic...")
    
    # Create sample data with various arbitrage opportunities
    sample_data = {
        'Material Name': ['DW', 'E', 'LSE', 'FEO', 'C'],
        'ticker': ['DW', 'E', 'LSE', 'FEO', 'C'],
        'category': ['Agricultural', 'Energy', 'Electronics', 'Minerals', 'Energy'],
        'tier': [1, 1, 2, 1, 1],
        'Current Price': [1000, 500, 2000, 300, 400],
        'Best Buy Exchange': ['AI1', 'CI1', 'AI1', 'NC1', 'CI2'],
        'Best Sell Exchange': ['CI1', 'AI1', 'CI2', 'AI1', 'NC1'],
        'Max Arbitrage Profit': [100, 50, 200, 75, 25],
        'Arbitrage ROI %': [10, 10, 10, 25, 6.25],
        'Investment Score': [80, 70, 90, 85, 60],
        'Risk Level': ['Medium', 'Low', 'High', 'Medium', 'Low']
    }
    
    # Create DataFrame
    exchange_data = pd.DataFrame(sample_data)
    print("\nSample data:")
    print(exchange_data[['Material Name', 'Best Buy Exchange', 'Best Sell Exchange', 'Max Arbitrage Profit']])
    
    # Test filtering for AI1 exchange
    test_exchanges = ['AI1', 'CI1', 'CI2', 'NC1']
    
    for current_exchange in test_exchanges:
        print(f"\n=== Testing for {current_exchange} ===")
        
        # Apply the same filtering logic as in upload_data.py
        arbitrage_data = exchange_data[exchange_data['Max Arbitrage Profit'] > 0].copy()
        
        if not arbitrage_data.empty:
            exchange_mask = (
                (arbitrage_data['Best Buy Exchange'] == current_exchange) |
                (arbitrage_data['Best Sell Exchange'] == current_exchange)
            )
            arbitrage_data = arbitrage_data[exchange_mask].copy()
        
        print(f"Arbitrage opportunities involving {current_exchange}: {len(arbitrage_data)}")
        if not arbitrage_data.empty:
            for _, row in arbitrage_data.iterrows():
                direction = ""
                if row['Best Buy Exchange'] == current_exchange and row['Best Sell Exchange'] != current_exchange:
                    direction = f"BUY from {current_exchange}, SELL to {row['Best Sell Exchange']}"
                elif row['Best Sell Exchange'] == current_exchange and row['Best Buy Exchange'] != current_exchange:
                    direction = f"BUY from {row['Best Buy Exchange']}, SELL to {current_exchange}"
                elif row['Best Buy Exchange'] == current_exchange and row['Best Sell Exchange'] == current_exchange:
                    direction = f"Same exchange trade (should not happen)"
                else:
                    direction = f"Both exchanges: {row['Best Buy Exchange']} -> {row['Best Sell Exchange']}"
                
                print(f"  {row['Material Name']}: {direction} (Profit: {row['Max Arbitrage Profit']})")
        else:
            print(f"  No arbitrage opportunities involving {current_exchange}")

if __name__ == "__main__":
    test_arbitrage_filtering()
