#!/usr/bin/env python3
"""
Test the new daily analysis generator
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

try:
    print("Testing new daily analysis generator...")
    
    # Import the builder
    from historical_data.report_builder import UnifiedReportBuilder
    print("✅ Import successful")
    
    # Create builder instance
    cache_dir = os.path.join(os.getcwd(), 'cache')
    builder = UnifiedReportBuilder(cache_dir)
    print("✅ Builder created")
    
    # Generate analysis
    print("🔄 Generating daily analysis...")
    analysis = builder.build_daily_analysis()
    print(f"✅ Generated analysis with {len(analysis)} rows")
    
    if not analysis.empty:
        print(f"📊 Columns: {list(analysis.columns)}")
        
        # Save new analysis
        output_path = os.path.join(cache_dir, 'daily_analysis_improved.csv')
        analysis.to_csv(output_path, index=False)
        print(f"💾 Saved improved analysis to: {output_path}")
        
        # Show sample data
        print("\n📋 Sample data:")
        print(analysis[['Material Name', 'ticker', 'Best Buy Exchange', 'Best Sell Exchange', 
                      'Max Arbitrage Profit', 'Bottleneck Type', 'Investment Score']].head(3))
    else:
        print("❌ No data generated")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
