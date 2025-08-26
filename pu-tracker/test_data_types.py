#!/usr/bin/env python3

import pandas as pd
import os

def test_data_types():
    """Test the data types in our daily report to verify numeric columns."""
    
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    report_path = os.path.join(cache_dir, "daily_report.csv")
    
    if not os.path.exists(report_path):
        print("❌ Daily report not found")
        return
    
    # Load the data
    report_df = pd.read_csv(report_path)
    print(f"✅ Loaded daily report with {len(report_df)} rows")
    
    # Check data types for numeric columns
    numeric_columns = [
        'Tier', 'Amount per Recipe', 'Weight', 'Volume', 'Current Price',
        'Input Cost per Unit', 'Input Cost per Stack', 'Profit per Unit',
        'Profit per Stack', 'ROI %', 'Supply', 'Demand', 'Traded Volume',
        'Market Cap', 'Liquidity Ratio', 'Investment Score', 'Volatility'
    ]
    
    print("\n📊 Data type analysis:")
    for col in numeric_columns:
        if col in report_df.columns:
            dtype = report_df[col].dtype
            sample_value = report_df[col].iloc[0] if len(report_df) > 0 else None
            print(f"  {col:20s}: {dtype} (sample: {sample_value})")
    
    # Test a specific row to show data handling
    print("\n🔍 Sample AAR data for type testing:")
    aar_data = report_df[(report_df['Ticker'] == 'AAR') & (report_df['exchange'] == 'AI1')]
    if not aar_data.empty:
        row = aar_data.iloc[0]
        print(f"  Current Price: {row['Current Price']} (type: {type(row['Current Price'])})")
        print(f"  Input Cost per Unit: {row['Input Cost per Unit']} (type: {type(row['Input Cost per Unit'])})")
        print(f"  Profit per Unit: {row['Profit per Unit']} (type: {type(row['Profit per Unit'])})")
        print(f"  ROI %: {row['ROI %']} (type: {type(row['ROI %'])})")
        
        # Test how the values would be handled in upload
        values_for_upload = []
        test_cols = ['Current Price', 'Input Cost per Unit', 'Profit per Unit', 'ROI %']
        for col in test_cols:
            value = row[col]
            if pd.isna(value):
                values_for_upload.append('')
            elif isinstance(value, (int, float)):
                values_for_upload.append(value)  # Keep as number
            else:
                values_for_upload.append(str(value))  # Convert to string
        
        print(f"\n📤 Values that would be uploaded:")
        for i, col in enumerate(test_cols):
            val = values_for_upload[i]
            print(f"  {col}: {val} (upload type: {type(val)})")

if __name__ == "__main__":
    test_data_types()
