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
from collections import defaultdict

# Import config
from unified_config import REQUIRED_DATA_COLUMNS, VALID_EXCHANGES
from workforce_costs import (
    load_market_prices,
    load_workforce_needs,
    calculate_input_costs_for_recipe,
    get_market_price,  # <-- Add this line
)

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

                # Always transform to long format if needed
                if 'Exchange' not in df.columns and 'AI1-AskPrice' in df.columns:
                    print("[INFO] Detected wide market data format, transforming...")
                    df = self.transform_market_data_wide_to_long(df)
                    # Optionally, save the transformed file for future use
                    df.to_csv(self.cache_dir / 'market_data_long.csv', index=False)

                # Now split by exchange
                if 'Exchange' in df.columns:
                    for exchange in VALID_EXCHANGES:
                        market_data[exchange] = df[df['Exchange'] == exchange].copy()
                else:
                    print("[ERROR] Could not find 'Exchange' column after transformation.")
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

        # --- ENSURE CORRECT COLUMN NAMES FOR DOWNSTREAM ---
        rename_map = {
            'Profit_Ask': 'Profit per Unit',
            'ROI_Ask': 'ROI Ask %',
            'ROI_Bid': 'ROI Bid %',
            # REMOVE or COMMENT OUT this line:
            # 'Traded': 'Traded Volume',
        }
        merged = merged.rename(columns=rename_map)

        # Add timestamp
        merged['Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Ensure input cost columns exist before calculating derived fields
        for col in ['Input Cost per Unit', 'Input Cost per Stack', 'Input Cost per Hour']:
            if col not in merged.columns:
                merged[col] = 0.0

        # Calculate derived fields
        merged = self.calculate_derived_fields(merged)

        # Select only required columns in correct order
        available_cols = [col for col in REQUIRED_DATA_COLUMNS if col in merged.columns]
        merged = merged[available_cols]
        # Drop any columns not in REQUIRED_DATA_COLUMNS
        merged = merged.loc[:, merged.columns.isin(REQUIRED_DATA_COLUMNS)]

        # Add missing columns that might have been lost
        for col in REQUIRED_DATA_COLUMNS:
            if col not in merged.columns:
                merged[col] = ''

        # Reorder to match required columns
        merged = merged[REQUIRED_DATA_COLUMNS]

        # --- BEGIN: Input cost calculation integration ---
        market_prices = load_market_prices()

        # Ensure market_prices is in long format
        if market_prices is not None and 'Exchange' not in market_prices.columns:
            print("[INFO] Transforming market_prices to long format for input cost calculations...")
            exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
            records = []
            for _, row in market_prices.iterrows():
                ticker = row['Ticker']
                for exch in exchanges:
                    ask_price = row.get(f"{exch}-AskPrice", None)
                    bid_price = row.get(f"{exch}-BidPrice", None)
                    if pd.notnull(ask_price) or pd.notnull(bid_price):
                        records.append({
                            'Ticker': ticker,
                            'Exchange': exch,
                            'Ask_Price': pd.to_numeric(ask_price, errors='coerce') if pd.notnull(ask_price) else 0,
                            'Bid_Price': pd.to_numeric(bid_price, errors='coerce') if pd.notnull(bid_price) else 0,
                        })
            market_prices = pd.DataFrame(records)

        wf_consumables = load_workforce_needs()
        inputs_by_recipe = build_input_materials_dict()

        # You may need to join recipe/building/workforce info to get these columns:
        # 'Recipe', 'WorkforceType', 'HoursPerRecipe', 'UnitsPerRecipe'
        # For demonstration, let's assume you have them or fill with defaults

        # Preload all recipe/building/workforce info
        recipe_outputs = pd.read_csv(self.cache_dir / "recipe_outputs.csv")
        recipe_inputs = pd.read_csv(self.cache_dir / "recipe_inputs.csv")
        buildingrecipes = pd.read_csv(self.cache_dir / "buildingrecipes.csv")
        workforces = pd.read_csv(self.cache_dir / "workforces.csv")
        wf_consumables = load_workforce_needs()
        market_prices = load_market_prices()

        # Build lookup dicts
        building_to_workforce = defaultdict(list)
        for _, row in workforces.iterrows():
            building_to_workforce[row['Building']].append(row['Level'])

        buildingrecipes_dict = buildingrecipes.set_index('Key').to_dict('index')

        # NEW APPROACH: Create separate rows for each recipe
        expanded_rows = []
        for idx, row in merged.iterrows():
            ticker = row['Ticker']
            exchange = row['Exchange']
            recipes = recipe_outputs[recipe_outputs['Material'] == ticker]
            
            if recipes.empty:
                # No recipes, keep original row with zero cost
                row_copy = row.copy()
                row_copy['Input Cost per Unit'] = 0
                row_copy['Input Cost per Stack'] = 0
                row_copy['Input Cost per Hour'] = 0
                row_copy['Recipe'] = 'N/A'
                row_copy['Building'] = 'N/A'
                expanded_rows.append(row_copy)
                continue
                
            for _, recipe_row in recipes.iterrows():
                recipe_id = recipe_row['Key']
                # Get input materials
                inputs = recipe_inputs[recipe_inputs['Key'] == recipe_id]
                input_materials = {r['Material']: float(r['Amount']) for _, r in inputs.iterrows()}
                # Get building and duration
                if recipe_id in buildingrecipes_dict:
                    b_row = buildingrecipes_dict[recipe_id]
                    building = b_row['Building']
                    duration_sec = float(b_row['Duration'])
                    hours_per_recipe = duration_sec / 3600
                    units_per_recipe = float(recipe_row['Amount'])
                    # Get workforce type(s)
                    workforce_types = building_to_workforce.get(building, ['PIONEER'])
                    # Calculate cost for first workforce type (most common)
                    workforce_type = workforce_types[0] if workforce_types else 'PIONEER'
                    # Workforce needs per hour
                    consumables = wf_consumables.get(workforce_type, {})
                    wf_cost = 0
                    for ticker_c, amt_per_day in consumables.items():
                        amt_per_hour = amt_per_day  # Already divided by 24 in loader
                        qty = amt_per_hour * hours_per_recipe * 1  # workforce_amount=1 unless you have more info
                        price = get_market_price(ticker_c, market_prices, exchange)
                        wf_cost += qty * price
                    # Material input cost
                    direct_input_cost = sum(
                        qty * get_market_price(t, market_prices, exchange)
                        for t, qty in input_materials.items()
                    )
                    total_input_cost = direct_input_cost + wf_cost
                    input_cost_per_unit = total_input_cost / units_per_recipe if units_per_recipe else 0
                    input_cost_per_stack = input_cost_per_unit * units_per_recipe
                    input_cost_per_hour = total_input_cost / hours_per_recipe if hours_per_recipe else 0
                    
                    # Create a new row for this recipe
                    row_copy = row.copy()
                    row_copy['Input Cost per Unit'] = input_cost_per_unit
                    row_copy['Input Cost per Stack'] = input_cost_per_stack
                    row_copy['Input Cost per Hour'] = input_cost_per_hour
                    row_copy['Recipe'] = recipe_id
                    row_copy['Building'] = building
                    expanded_rows.append(row_copy)
        
        # Replace merged with expanded dataset
        merged = pd.DataFrame(expanded_rows)
        # --- END: Input cost calculation integration ---

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

            # Profit per Unit
            df['Profit_Ask'] = df['Ask_Price'] - df['Input Cost per Unit']
            df['Profit_Bid'] = df['Bid_Price'] - df['Input Cost per Unit']

            # Profit per Stack (assuming stack size 100, adjust if needed)
            df['Profit_per_Stack'] = df['Profit_Ask'] * 100

            # ROI Ask % and ROI Bid %
            df['ROI_Ask'] = df.apply(
                lambda row: (row['Profit_Ask'] / row['Input_Cost'] * 100) if row['Input_Cost'] > 0 else 0,
                axis=1
            )
            df['ROI_Bid'] = df.apply(
                lambda row: (row['Profit_Bid'] / row['Input_Cost'] * 100) if row['Input_Cost'] > 0 else 0,
                axis=1
            )

            # Saturation
            def calc_saturation(row):
                supply = row.get('Supply', 0)
                demand = row.get('Demand', 0)
                if pd.isna(supply) or pd.isna(demand) or demand == 0:
                    return 100.0
                return min(200.0, round((supply / demand) * 100, 2))
            df['Saturation'] = df.apply(calc_saturation, axis=1)

            # Market Cap
            df['Market_Cap'] = df['Supply'] * df['Ask_Price']

            # Liquidity Ratio
            df['Liquidity_Ratio'] = df.apply(
                lambda row: row['Traded'] / (row['Supply'] + row['Demand']) if (row['Supply'] + row['Demand']) > 0 else 0,
                axis=1
            )

            # Risk Level
            df['Risk'] = df.apply(
                lambda row: 'High' if row['Ask_Price'] > 0 and (row['Ask_Price'] - row['Bid_Price']) > row['Ask_Price'] * 0.2
                else ('Medium' if row['Ask_Price'] > 0 and (row['Ask_Price'] - row['Bid_Price']) > row['Ask_Price'] * 0.1
                else 'Low'),
                axis=1
            )

            # Input Cost per Stack (assuming stack size 100)
            df['Input_Cost_per_Stack'] = df['Input_Cost'] * 100

            # Input Cost per Hour (if you have recipe duration in seconds)
            if 'Recipe_Duration' in df.columns:
                df['Input_Cost_per_Hour'] = df.apply(
                    lambda row: (row['Input_Cost'] * (3600 / row['Recipe_Duration'])) if row['Recipe_Duration'] > 0 else 0,
                    axis=1
                )
            else:
                df['Input_Cost_per_Hour'] = 0

            # Traded Volume
            if 'Traded' not in df.columns:
                df['Traded'] = 0.0
            df['Traded'] = pd.to_numeric(df['Traded'], errors='coerce').fillna(0)
            df['Traded_Volume'] = df['Traded']

            # Ensure all required columns exist for downstream
            required_cols = [
                'Profit_Ask', 'Profit_Bid', 'Profit_per_Stack', 'ROI_Ask', 'ROI_Bid',
                'Saturation', 'Market_Cap', 'Liquidity_Ratio', 'Investment_Score', 'Risk',
                'Input_Cost_per_Stack', 'Input_Cost_per_Hour', 'Traded_Volume'
            ]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 0

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

def build_input_materials_dict():
    """
    Builds a dictionary mapping recipe Key to a dict of {ticker: qty} using recipe_inputs.csv.
    """
    recipe_inputs_path = Path(__file__).parent.parent / "cache" / "recipe_inputs.csv"
    recipe_inputs_df = pd.read_csv(recipe_inputs_path)
    inputs_by_recipe = {}
    recipe_id_col = "Key"
    for _, r in recipe_inputs_df.iterrows():
        rid = r[recipe_id_col]
        ticker = r['Material']
        qty = r['Amount']
        inputs_by_recipe.setdefault(rid, {})[ticker] = qty
    return inputs_by_recipe

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