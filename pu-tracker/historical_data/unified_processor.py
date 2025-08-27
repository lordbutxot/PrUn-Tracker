"""
Unified Data Processor
Fixed materials loading and processing issues
"""

import pandas as pd
import json
import os
import sys  # FIXED: Added missing import
from pathlib import Path
from datetime import datetime
import logging

# Import config
from unified_config import REQUIRED_DATA_COLUMNS, VALID_EXCHANGES

class UnifiedDataProcessor:
    def __init__(self):
        self.cache_dir = Path(__file__).parent.parent / 'cache'
        self.cache_dir.mkdir(exist_ok=True)
        
    def load_basic_data(self):
        print("\n\033[1;36m[STEP]\033[0m Loading basic materials/buildings data...")
        """Load basic materials/buildings data"""
        try:
            print("[INFO] Loading basic data from cache...")
            
            # First try to load from existing CSV files
            basic_data = []
            
            # Try materials.csv first
            materials_csv = self.cache_dir / 'materials.csv'
            if materials_csv.exists():
                print(f"[INFO] Loading from {materials_csv}")
                df = pd.read_csv(materials_csv)
                return df
            
            # Try materials.json
            materials_file = self.cache_dir / 'materials.json'
            if materials_file.exists():
                print(f"[INFO] Loading from {materials_file}")
                with open(materials_file, 'r') as f:
                    materials = json.load(f)
                    
                for ticker, data in materials.items():
                    basic_data.append({
                        'Ticker': ticker,
                        'Product': data.get('Name', ticker),
                        'Category': data.get('CategoryName', 'Unknown'),
                        'Tier': data.get('Tier', 0)
                    })
            
            # Try buildings.json as fallback
            buildings_file = self.cache_dir / 'buildings.json'
            if buildings_file.exists() and not basic_data:
                print(f"[INFO] Loading buildings from {buildings_file}")
                with open(buildings_file, 'r') as f:
                    buildings = json.load(f)
                    
                for ticker, data in buildings.items():
                    basic_data.append({
                        'Ticker': ticker,
                        'Product': data.get('Name', ticker),
                        'Category': 'Building',
                        'Tier': 0
                    })
            
            if basic_data:
                df = pd.DataFrame(basic_data)
                print(f"[SUCCESS] Loaded {len(df)} items from basic data")
                return df
            else:
                print("[WARNING] No basic data found, creating empty DataFrame")
                return pd.DataFrame(columns=['Ticker', 'Product', 'Category', 'Tier'])
                
        except Exception as e:
            print(f"[ERROR] Loading basic data: {e}")
            return pd.DataFrame(columns=['Ticker', 'Product', 'Category', 'Tier'])
    
    def load_market_data(self):
        print("\n\033[1;36m[STEP]\033[0m Loading market data for all exchanges...")
        """Load market data by exchange"""
        market_data = {}
        
        # Try to load general market data first
        general_market = self.cache_dir / 'market_data.csv'
        if general_market.exists():
            try:
                df = pd.read_csv(general_market)
                print(f"[INFO] Loaded general market data: {len(df)} records")
                
                # If Exchange column exists, split by exchange
                if 'Exchange' in df.columns:
                    for exchange in VALID_EXCHANGES:
                        exchange_data = df[df['Exchange'] == exchange]
                        if not exchange_data.empty:
                            market_data[exchange] = exchange_data
                else:
                    # If no Exchange column, assume it's for all exchanges
                    for exchange in VALID_EXCHANGES:
                        market_data[exchange] = df.copy()
                        
            except Exception as e:
                print(f"[ERROR] Loading general market data: {e}")
        
        # Try exchange-specific files
        for exchange in VALID_EXCHANGES:
            if exchange in market_data:
                continue
                
            try:
                market_file = self.cache_dir / f'market_data_{exchange.lower()}.csv'
                if market_file.exists():
                    df = pd.read_csv(market_file)
                    market_data[exchange] = df
                    print(f"[INFO] Loaded market data for {exchange}: {len(df)} records")
                else:
                    print(f"[WARNING] No specific market data for {exchange}")
                    
            except Exception as e:
                print(f"[ERROR] Loading market data for {exchange}: {e}")
                
        # Check for wide format data and transform if necessary
        if 'AI1-AskPrice' in df.columns:
            print("[INFO] Detected wide market data format, transforming...")
            long_df = self.transform_market_data_wide_to_long(df)
            for exchange in VALID_EXCHANGES:
                market_data[exchange] = long_df[long_df['Exchange'] == exchange].copy()
        
        return market_data
    
    def create_complete_dataset(self, basic_data, market_data):
        print("\n\033[1;36m[STEP]\033[0m Creating complete dataset for all exchanges...")
        """Create complete dataset with all required columns"""
        complete_df = []

        if basic_data.empty:
            print("[ERROR] No basic data to process")
            return pd.DataFrame()

        all_tickers = basic_data['Ticker'].unique()
        all_exchanges = VALID_EXCHANGES

        # Cross join all tickers and all exchanges
        cross = pd.MultiIndex.from_product([all_tickers, all_exchanges], names=['Ticker', 'Exchange']).to_frame(index=False)
        merged = cross.merge(basic_data, on='Ticker', how='left')

        # For each exchange, merge with market data and collect results
        results = []
        for exchange in all_exchanges:
            subset = merged[merged['Exchange'] == exchange].copy()
            if exchange in market_data and not market_data[exchange].empty:
                market_df = market_data[exchange]
                # Merge on Ticker, keeping all tickers for this exchange
                subset = subset.merge(market_df, on='Ticker', how='left', suffixes=('', '_market'))
            results.append(subset)

        # Concatenate all exchanges back together
        merged = pd.concat(results, ignore_index=True)

        # Fill missing columns with appropriate defaults
        for col in REQUIRED_DATA_COLUMNS:
            if col not in merged.columns:
                if col in ['Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded']:
                    merged[col] = 0.0
                elif col in ['Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid']:
                    merged[col] = 0.0
                elif col in ['ROI_Ask', 'ROI_Bid', 'Investment_Score']:
                    merged[col] = 0.0
                elif col in ['Risk', 'Viability', 'Recommendation']:
                    merged[col] = 'Unknown'
                elif col == 'Price_Spread':
                    merged[col] = 0.0
                else:
                    merged[col] = ''

        # Add timestamp
        merged['Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Calculate derived fields
        merged = self.calculate_derived_fields(merged)

        # Select only required columns in correct order
        available_cols = [col for col in REQUIRED_DATA_COLUMNS if col in merged.columns]
        merged = merged[available_cols]

        # Add missing columns that might have been lost
        for col in REQUIRED_DATA_COLUMNS:
            if col not in merged.columns:
                merged[col] = ''

        # Reorder to match required columns
        merged = merged[REQUIRED_DATA_COLUMNS]

        print(f"[SUCCESS] Created complete dataset: {len(merged)} total records")
        return merged
    
    def calculate_derived_fields(self, df):
        print("\n\033[1;36m[STEP]\033[0m Calculating derived fields (profit, ROI, risk, etc.)...")
        """Calculate derived fields like profit, ROI, etc."""
        try:
            # Ensure numeric columns are numeric
            numeric_cols = ['Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Input_Cost', 'Traded']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Price spread
            df['Price_Spread'] = df['Ask_Price'] - df['Bid_Price']
            
            # Basic profit calculations
            df['Profit_Ask'] = df['Ask_Price'] - df['Input_Cost']
            df['Profit_Bid'] = df['Bid_Price'] - df['Input_Cost']
            
            # ROI calculations
            df['ROI_Ask'] = df.apply(lambda row: 
                (row['Profit_Ask'] / row['Input_Cost'] * 100) if row['Input_Cost'] > 0 else 0, axis=1)
            df['ROI_Bid'] = df.apply(lambda row: 
                (row['Profit_Bid'] / row['Input_Cost'] * 100) if row['Input_Cost'] > 0 else 0, axis=1)
            
            # Investment score (simplified)
            df['Investment_Score'] = df.apply(lambda row:
                min(100, max(0, row['ROI_Ask'] * 0.5 + (row['Supply'] * 0.1 if row['Supply'] > 0 else 0))), axis=1)
            
            # Risk assessment
            df['Risk'] = df.apply(lambda row: 
                'High' if row['Ask_Price'] > 0 and row['Price_Spread'] > row['Ask_Price'] * 0.2 else
                'Medium' if row['Ask_Price'] > 0 and row['Price_Spread'] > row['Ask_Price'] * 0.1 else 'Low', axis=1)
            
            # Viability
            df['Viability'] = df.apply(lambda row:
                'Excellent' if row['ROI_Ask'] > 50 else
                'Good' if row['ROI_Ask'] > 20 else
                'Fair' if row['ROI_Ask'] > 0 else 'Poor', axis=1)
            
            # Recommendations
            df['Recommendation'] = df.apply(lambda row:
                'Buy' if row['Viability'] in ['Excellent', 'Good'] and row['Risk'] != 'High' else
                'Hold' if row['Viability'] == 'Fair' else 'Avoid', axis=1)
                
        except Exception as e:
            print(f"[WARNING] Error calculating derived fields: {e}")
            
        return df
    
    def save_processed_data(self, complete_df):
        print("\n\033[1;36m[STEP]\033[0m Saving processed data to cache files...")
        """Save processed data to cache files"""
        try:
            if complete_df.empty:
                print("[ERROR] No data to save")
                return False
                
            # Save main dataset to multiple files for compatibility
            files_saved = []
            
            for filename in ['daily_report.csv', 'daily_analysis.csv', 'processed_data.csv']:
                file_path = self.cache_dir / filename
                complete_df.to_csv(file_path, index=False)
                files_saved.append(filename)
            
            print(f"[SUCCESS] Saved {len(complete_df)} records to {len(files_saved)} files")
            return True
            
        except Exception as e:
            print(f"[ERROR] Saving processed data: {e}")
            return False

    def transform_market_data_wide_to_long(self, wide_df):
        print("\n\033[1;36m[STEP]\033[0m Transforming wide market data to long format...")
        """Convert wide market_data.csv to long format for all exchanges."""
        records = []
        exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
        for _, row in wide_df.iterrows():
            ticker = row['Ticker']
            for exch in exchanges:
                ask_price = row.get(f"{exch}-AskPrice", None)
                bid_price = row.get(f"{exch}-BidPrice", None)
                supply = row.get(f"{exch}-AskAvail", None)
                demand = row.get(f"{exch}-BidAvail", None)
                traded = row.get(f"{exch}-AskAmt", None)
                # Only add if at least one price exists
                if pd.notnull(ask_price) or pd.notnull(bid_price):
                    records.append({
                        'Ticker': ticker,
                        'Exchange': exch,
                        'Ask_Price': pd.to_numeric(ask_price, errors='coerce') if pd.notnull(ask_price) else 0,
                        'Bid_Price': pd.to_numeric(bid_price, errors='coerce') if pd.notnull(bid_price) else 0,
                        'Supply': pd.to_numeric(supply, errors='coerce') if pd.notnull(supply) else 0,
                        'Demand': pd.to_numeric(demand, errors='coerce') if pd.notnull(demand) else 0,
                        'Traded': pd.to_numeric(traded, errors='coerce') if pd.notnull(traded) else 0,
                    })
        return pd.DataFrame(records)

def main():
    print("\n\033[1;35m[UNIFIED PROCESSOR]\033[0m")
    """Main processing function"""
    try:
        processor = UnifiedDataProcessor()
        
        print("[INFO] Loading basic data...")
        basic_data = processor.load_basic_data()
        if basic_data.empty:
            print("[ERROR] No basic data loaded")
            return False
            
        print("[INFO] Loading market data...")
        market_data = processor.load_market_data()
        
        print("[INFO] Creating complete dataset...")
        complete_df = processor.create_complete_dataset(basic_data, market_data)
        
        if complete_df.empty:
            print("[ERROR] No complete dataset created")
            return False
            
        print("[INFO] Saving processed data...")
        return processor.save_processed_data(complete_df)
        
    except Exception as e:
        print(f"[ERROR] Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)