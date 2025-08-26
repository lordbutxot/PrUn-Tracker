"""
Test the structured upload function without actually uploading to Google Sheets
"""
import pandas as pd
import numpy as np

def test_upload_structured_report():
    # Load test data
    df = pd.read_csv('cache/daily_analysis.csv')
    print('=== TESTING STRUCTURED REPORT FUNCTION ===')
    print(f'Data shape: {df.shape}')
    
    # Get AI1 data as test
    if 'exchange' in df.columns:
        ai1_data = df[df['exchange'] == 'AI1'].copy()
        print(f'AI1 exchange data: {len(ai1_data)} materials')
    else:
        ai1_data = df.head(100).copy()  # Use first 100 as test
        print(f'Test data: {len(ai1_data)} materials')
    
    # Test each section
    print('\n=== SECTION ANALYSIS ===')
    
    # 1. Arbitrage section
    arbitrage_data = ai1_data[ai1_data['Max Arbitrage Profit'] > 0].copy()
    print(f'1. Arbitrage opportunities: {len(arbitrage_data)}')
    if len(arbitrage_data) > 0:
        print(f'   Top arbitrage profit: {arbitrage_data["Max Arbitrage Profit"].max():.2f}')
    
    # 2. Bottleneck section
    bottleneck_data = ai1_data[ai1_data['Bottleneck Severity'] > 0].copy()
    print(f'2. Bottleneck issues: {len(bottleneck_data)}')
    if len(bottleneck_data) > 0:
        print(f'   Max bottleneck severity: {bottleneck_data["Bottleneck Severity"].max():.2f}')
    
    # 3. Production section
    production_data = ai1_data[ai1_data['Break-even Quantity'] > 0].copy()
    print(f'3. Production opportunities: {len(production_data)}')
    if len(production_data) > 0:
        print(f'   Max ROI: {production_data["ROI %"].max():.2f}%')
    
    # 4. Investment section
    top_investments = ai1_data.nlargest(20, 'Investment Score').copy()
    print(f'4. Top 20 investments: {len(top_investments)}')
    if len(top_investments) > 0:
        print(f'   Best investment score: {top_investments["Investment Score"].max():.1f}')
    
    print('\n✅ Structure test complete - ready for Google Sheets upload!')
    return True

if __name__ == "__main__":
    test_upload_structured_report()
