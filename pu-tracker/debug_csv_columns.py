import pandas as pd
import os
from historical_data.config import CACHE_DIR

# Load the cached CSV file to see what columns it actually has
cache_file = os.path.join(CACHE_DIR, 'prices_all.csv')

if os.path.exists(cache_file):
    df = pd.read_csv(cache_file)
    print("Actual CSV columns:")
    print(list(df.columns))
    print("\nFirst few rows:")
    print(df.head())
    print(f"\nDataFrame shape: {df.shape}")
else:
    print(f"Cache file not found: {cache_file}")
