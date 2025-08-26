import pandas as pd

# Load test data
df = pd.read_csv('cache/daily_analysis.csv')
print('=== DAILY ANALYSIS STRUCTURE TEST ===')
print(f'Data shape: {df.shape}')
print(f'First 5 columns: {list(df.columns[:5])}')
print(f'Last 5 columns: {list(df.columns[-5:])}')

# Check key columns for sections
key_columns = ['Max Arbitrage Profit', 'Bottleneck Severity', 'Break-even Quantity', 'Investment Score']
for col in key_columns:
    if col in df.columns:
        count = len(df[df[col] > 0])
        print(f'- {col}: {count} items > 0')
    else:
        print(f'- {col}: Column not found')

print(f'\nTotal materials: {len(df)}')
print('\n✅ Structure test complete')
