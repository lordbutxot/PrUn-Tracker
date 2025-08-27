"""
Enhanced Analysis Uploader - Using UnifiedSheetsManager pattern
Based on your working ultra_all_exchanges_upload.py
"""

import sys
import os
import pandas as pd
import logging
import traceback
from pathlib import Path
from typing import Optional
from sheets_manager import UnifiedSheetsManager

# The exact 24 column headers
REQUIRED_HEADERS = [
    'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe', 'Amount per Recipe',
    'Weight', 'Volume', 'Current Price', 'Input Cost per Unit', 'Input Cost per Stack',
    'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %',
    'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap',
    'Liquidity Ratio', 'Investment Score', 'Risk Level', 'Volatility'
]

EXCHANGE_TABS = ['DATA AI1', 'DATA CI1', 'DATA CI2', 'DATA IC1', 'DATA NC1', 'DATA NC2']

def main():
    """Main upload function using UnifiedSheetsManager"""
    try:
        print("🚀 Enhanced Analysis Uploader v2 - Using UnifiedSheetsManager")
        print("=" * 60)
        
        # Initialize UnifiedSheetsManager (like ultra_all_exchanges_upload.py)
        sheets_manager = UnifiedSheetsManager()
        print("✅ Initialized UnifiedSheetsManager")
        
        # Load enhanced data
        cache_dir = Path(__file__).parent.parent / 'cache'
        enhanced_file = cache_dir / 'daily_analysis_enhanced.csv'
        
        if not enhanced_file.exists():
            print("❌ daily_analysis_enhanced.csv not found")
            print("   📝 Run unified_analysis.py first")
            return False
        
        df = pd.read_csv(enhanced_file)
        print(f"✅ Loaded enhanced data: {len(df)} rows, {len(df.columns)} columns")
        
        # Ensure correct column order
        df = df[REQUIRED_HEADERS]
        
        # Upload to all DATA tabs
        success_count = 0
        
        for sheet_name in EXCHANGE_TABS:
            try:
                print(f"\n📤 Uploading to {sheet_name}...")
                
                # Use the same method as ultra_all_exchanges_upload.py
                success = sheets_manager.upload_dataframe_to_sheet(sheet_name, df)
                
                if success:
                    success_count += 1
                    print(f"✅ {sheet_name}: {len(df)} rows uploaded")
                else:
                    print(f"❌ {sheet_name}: Upload failed")
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                print(f"❌ {sheet_name}: Error - {e}")
                continue
        
        print(f"\n📊 Upload Summary: {success_count}/{len(EXCHANGE_TABS)} tabs updated")
        
        if success_count == len(EXCHANGE_TABS):
            print("🎉 ALL uploads successful!")
            return True
        else:
            print("⚠️  Some uploads failed")
            return False
        
    except Exception as e:
        print(f"❌ Upload process failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
