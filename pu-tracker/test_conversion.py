#!/usr/bin/env python3

import pandas as pd
import numpy as np
import os

def test_value_conversion():
    """Test how our values are converted for upload."""
    
    # Load sample data
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    report_path = os.path.join(cache_dir, "daily_report.csv")
    
    report_df = pd.read_csv(report_path)
    sample_row = report_df.iloc[0]
    
    print("🧪 Testing value conversion logic:")
    
    test_columns = ['Current Price', 'Input Cost per Unit', 'ROI %', 'Supply', 'Ticker', 'Category']
    
    for col in test_columns:
        if col in sample_row:
            value = sample_row[col]
            original_type = type(value)
            
            # Apply our conversion logic
            if pd.isna(value):
                converted = ''
                converted_type = "empty string"
            elif isinstance(value, (int, float, np.integer, np.floating)):
                if isinstance(value, np.integer):
                    converted = int(value)
                else:
                    converted = float(value)
                converted_type = type(converted)
            else:
                converted = str(value)
                converted_type = type(converted)
            
            print(f"  {col:20s}: {value} ({original_type}) -> {converted} ({converted_type})")
    
    print("\n✅ Conversion test complete!")
    print("Numbers should be uploaded as int/float (not str) to avoid apostrophes.")

if __name__ == "__main__":
    test_value_conversion()
