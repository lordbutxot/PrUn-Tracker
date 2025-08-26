#!/usr/bin/env python3
"""
Test the improved report builder formulas
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from historical_data.report_builder import UnifiedReportBuilder
import pandas as pd

def test_improvements():
    print("🧪 Testing improved report builder formulas...")
    print("=" * 60)
    
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    
    # Test if we can create the report builder
    try:
        report_builder = UnifiedReportBuilder(cache_dir)
        print("✅ Report builder created successfully")
    except Exception as e:
        print(f"❌ Error creating report builder: {e}")
        return
    
    # Test arbitrage calculation
    print("\n🔄 Testing arbitrage calculation...")
    try:
        # Load market data for testing
        market_data_path = os.path.join(cache_dir, "market_data.csv")
        if os.path.exists(market_data_path):
            market_df = pd.read_csv(market_data_path)
            
            # Test with a sample ticker
            sample_ticker = market_df['Ticker'].iloc[0] if not market_df.empty else 'AAR'
            arbitrage_result = report_builder.calculate_arbitrage_opportunities(sample_ticker, market_df)
            print(f"   Sample arbitrage for {sample_ticker}: {arbitrage_result}")
        else:
            print("   ⚠️  No market data found for testing")
    except Exception as e:
        print(f"   ❌ Error testing arbitrage: {e}")
    
    # Test bottleneck analysis
    print("\n🔄 Testing bottleneck analysis...")
    try:
        bottleneck_result = report_builder.analyze_bottlenecks('AAR', 100, 50, 3, 'electronic devices', pd.DataFrame())
        print(f"   Sample bottleneck analysis: {bottleneck_result}")
    except Exception as e:
        print(f"   ❌ Error testing bottleneck: {e}")
    
    # Test produce vs buy
    print("\n🔄 Testing produce vs buy analysis...")
    try:
        produce_result = report_builder.enhanced_produce_vs_buy('AAR', 1000, 1500, 1600, 1400, 100, 50, 3, {})
        print(f"   Sample produce vs buy: {produce_result}")
    except Exception as e:
        print(f"   ❌ Error testing produce vs buy: {e}")
    
    # Test investment score
    print("\n🔄 Testing investment score...")
    try:
        investment_score = report_builder.calculate_investment_score(500, 25.0, 1.2, 0.1, 100, 60, 3)
        print(f"   Sample investment score: {investment_score}")
    except Exception as e:
        print(f"   ❌ Error testing investment score: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")

if __name__ == "__main__":
    test_improvements()
