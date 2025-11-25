"""
SINGLE UNIFIED ANALYSIS FILE
Generates the exact 24-column structure for Google Sheets upload
Uses existing cache data and outputs to daily_analysis_enhanced.csv

REFACTORED: Now uses loaders.py, calculators.py, and config.py modules
"""

import pandas as pd
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import from refactored modules
from config import CACHE_DIR, ENHANCED_ANALYSIS_COLUMNS
from loaders import (
    load_materials, load_market_data, load_recipe_inputs, load_recipe_outputs,
    load_buildingrecipes, load_workforceneeds, load_categories, load_tiers,
    load_recipes_json, load_processed_data, load_materials_json,
    get_market_price
)
from calculators import (
    calculate_detailed_costs, calculate_profit, calculate_roi,
    calculate_investment_score, calculate_viability, calculate_risk_level
)

class UnifiedAnalysisProcessor:
    def __init__(self):
        print("\n\033[1;36m[STEP]\033[0m Initializing UnifiedAnalysisProcessor...")
        # Use centralized cache directory
        self.cache_dir = CACHE_DIR
        print(f" Cache directory: {self.cache_dir}")
        
        # Load material and recipe data using loaders
        self.materials = load_materials()
        self.recipe_outputs = load_recipe_outputs()
        self.recipe_inputs = load_recipe_inputs()
        
        # Use centralized column definitions
        self.target_columns = ENHANCED_ANALYSIS_COLUMNS
        
        # Load building recipes and workforce needs
        self._materials_cache = None
        self._materials_mtime = None
        self.buildingrecipes_df = load_buildingrecipes()
        self.workforceneeds = load_workforceneeds()
        
    def load_cache_data(self):
        print("\n\033[1;36m[STEP]\033[0m Loading cache data...")
        """Load all available cache data"""
        print(f"   Cache directory exists: {self.cache_dir.exists()}")
        
        if not self.cache_dir.exists():
            print(" Cache directory doesn't exist - creating it...")
            self.cache_dir.mkdir(exist_ok=True)
        
        data = {}
        
        # List all files in cache directory
        if self.cache_dir.exists():
            cache_files = list(self.cache_dir.glob("*"))
            print(f"   Files in cache: {len(cache_files)}")
            for file in cache_files[:10]:  # Show first 10 files
                print(f"     - {file.name}")
        
        # Load CSV files
        csv_files = ['materials.csv', 'market_data.csv', 'processed_data.csv', 'daily_analysis.csv', 'daily_report.csv']
        for file in csv_files:
            path = self.cache_dir / file
            if path.exists():
                try:
                    data[file] = pd.read_csv(path, na_filter=False)
                    print(f"    {file}: {len(data[file])} rows")
                except Exception as e:
                    print(f"    {file}: Error loading - {e}")
            else:
                print(f"    {file}: Not found")
                
        # Load JSON files
        json_files = ['materials.json', 'categories.json', 'tiers.json', 'recipes.json']
        for file in json_files:
            path = self.cache_dir / file
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data[file] = json.load(f)
                    print(f"    {file}: {len(data[file])} items")
                except Exception as e:
                    print(f"    {file}: Error loading - {e}")
                    data[file] = {}
            else:
                print(f"    {file}: Not found")
                data[file] = {}
                
        return data
        
    def inspect_data_structure(self, data):
        print("\n\033[1;36m[STEP]\033[0m Inspecting data structure...")
        """Inspect and show available data structure"""
        print("\n Data Structure Analysis:")
        
        for filename, content in data.items():
            if isinstance(content, pd.DataFrame):
                print(f"\n {filename} columns:")
                for i, col in enumerate(content.columns, 1):
                    non_null = content[col].count()
                    print(f"   {i:2d}. {col} ({non_null}/{len(content)} non-null)")
            elif isinstance(content, dict) and content:
                print(f"\n {filename} sample keys:")
                sample_keys = list(content.keys())[:5]
                for key in sample_keys:
                    print(f"   - {key}")
                    
        return True
        
    def calculate_saturation(self, supply, demand, traded_volume):
        """
        Calculate market saturation as a percentage.
        High saturation = oversupplied (supply > demand).
        Low saturation = undersupplied (demand > supply).
        If demand is zero, returns 100 (fully saturated).
        If supply is zero, returns 0 (no saturation).
        """
        if pd.isna(supply) or pd.isna(demand):
            return 50  # Neutral if data missing

        if demand <= 0:
            # No demand: market is fully saturated (oversupplied)
            return 100.0
        if supply <= 0:
            # No supply: market is empty (undersupplied)
            return 0.0

        saturation = (supply / demand) * 100
        # Optionally cap at 200 for extreme oversupply, or leave uncapped
        return round(saturation, 2)
        
    def calculate_roi_ask_bid(self, ask_price, bid_price, input_cost):
        """Calculate separate ROI for Ask and Bid"""
        roi_ask = roi_bid = None
        ROI_CAP = 1000  # or whatever large value you prefer

        if pd.notna(input_cost) and input_cost > 0:
            if pd.notna(ask_price) and ask_price > 0:
                roi_ask = round(((ask_price - input_cost) / input_cost) * 100, 2)
            if pd.notna(bid_price) and bid_price > 0:
                roi_bid = round(((bid_price - input_cost) / input_cost) * 100, 2)
        elif input_cost == 0:
            # Free product: ROI is "infinite" if profit > 0, else 0
            if pd.notna(ask_price) and ask_price > 0:
                roi_ask = ROI_CAP
            else:
                roi_ask = 0
            if pd.notna(bid_price) and bid_price > 0:
                roi_bid = ROI_CAP
            else:
                roi_bid = 0

        return roi_ask, roi_bid
        
    def calculate_investment_score(self, roi_ask, liquidity_ratio, saturation, supply, demand, traded_volume, volatility):
        score = 0

        # Penalize no supply or no demand
        if supply == 0 or demand == 0 or traded_volume == 0:
            return 0

        # ROI component (30%)
        try:
            roi = float(roi_ask)
        except (TypeError, ValueError):
            roi = 0
        if roi > 20:
            score += 30
        elif roi > 10:
            score += 20
        elif roi > 0:
            score += 10

        # Liquidity (20%)
        if liquidity_ratio > 10:
            score += 20
        elif liquidity_ratio > 5:
            score += 10

        # Saturation (15%, lower is better)
        if saturation < 20:
            score += 15
        elif saturation < 40:
            score += 10

        # Traded volume (15%)
        if traded_volume > 1000:
            score += 15
        elif traded_volume > 100:
            score += 10

        # Volatility (10%, lower is better)
        if volatility is not None and volatility < 10:
            score += 10
        elif volatility is not None and volatility < 30:
            score += 5

        return min(score, 100)
        
    def calculate_risk_level(self, saturation, liquidity_ratio, profit_per_unit, traded_volume, supply, demand, volatility):
        if supply == 0 or demand == 0 or traded_volume < 10:
            return "High"
        if profit_per_unit < 0:
            return "High"
        if volatility is not None and volatility > 50:
            return "High"
        if liquidity_ratio < 1:
            return "High"
        if saturation > 80:
            return "High"
        if traded_volume < 100 or liquidity_ratio < 5 or saturation > 40 or (volatility is not None and volatility > 20):
            return "Medium"
        return "Low"
            
    def get_material_info(self, ticker):
        """Get material info from materials.csv"""
        row = self.materials[self.materials['Ticker'] == ticker]
        if not row.empty:
            return {
                'Category': row.iloc[0]['Category'],
                'Tier': row.iloc[0]['Tier'],
                'Weight': row.iloc[0]['Weight'],
                'Volume': row.iloc[0]['Volume'],
                'Material Name': row.iloc[0]['Name']
            }
        return {
            'Category': 'Unknown',
            'Tier': '',
            'Weight': '',
            'Volume': '',
            'Material Name': ticker
        }

    def get_recipe(self, ticker):
        """Get recipe for a given ticker from recipe_outputs.csv"""
        # Find all recipes that produce this ticker
        recipes = self.recipe_outputs[self.recipe_outputs['Material'] == ticker]
        if not recipes.empty:
            # Return the first recipe key, or join all if you want
            return '; '.join(recipes['Key'].unique())
        return 'None'
        
    def get_amount_per_recipe(self, ticker):
        # Find all recipes that produce this ticker
        recipes = self.recipe_outputs[self.recipe_outputs['Material'] == ticker]
        if not recipes.empty:
            # If multiple recipes, use the first (or sum, or max, as appropriate)
            return float(recipes.iloc[0]['Amount'])
        return 1.0  # Default to 1 if not found
        
    def parse_output_amount_from_recipe(self, recipe_str, ticker):
        """
        Extracts the output amount for the given ticker from the recipe string.
        E.g., for 'ELP:2xAU-1xKV-4xPCB-6xSWF=>3xAAR', ticker='AAR', returns 3
        """
        if not recipe_str or not ticker:
            return 1
        matches = re.findall(r'=>\s*([\d.]+)x([A-Z0-9]+)', recipe_str)
        for amount, out_ticker in matches:
            if out_ticker == ticker:
                try:
                    return float(amount)
                except Exception:
                    continue
        return 1

    # Removed: load_buildingrecipes() - now using loaders.load_buildingrecipes()
    # Removed: load_workforceneeds() - now using loaders.load_workforceneeds()

    def load_materials(self):
        path = self.cache_dir / 'materials.csv'
        mtime = os.path.getmtime(path)
        if self._materials_cache is not None and self._materials_mtime == mtime:
            return self._materials_cache
        self._materials_cache = pd.read_csv(path)
        self._materials_mtime = mtime
        return self._materials_cache

    def get_all_tickers_from_recipes(self, recipes_dict):
        """Extract all unique tickers from recipes.json"""
        tickers = set()
        for recipe_key, recipe_data in recipes_dict.items():
            # Parse inputs and outputs from recipe_key
            if ':' in recipe_key:
                parts = recipe_key.split(':')[1].split('=>')
                if len(parts) == 2:
                    inputs = parts[0]
                    outputs = parts[1]
                    # Parse inputs
                    for item in inputs.split('-'):
                        if 'x' in item:
                            ticker = item.split('x')[1].strip()
                            tickers.add(ticker)
                    # Parse outputs
                    for item in outputs.split('-'):
                        if 'x' in item:
                            ticker = item.split('x')[1].strip()
                            tickers.add(ticker)
        return sorted(list(tickers))

    def generate_unified_analysis(self):
        print("\n\033[1;36m[STEP]\033[0m Generating unified analysis for Google Sheets...")
        """Generate the complete 24-column analysis"""
        # Load all data
        data = self.load_cache_data()
        
        # Show data structure
        self.inspect_data_structure(data)
        
        # Get reference data
        materials_dict = data.get('materials.json', {})
        categories_dict = data.get('categories.json', {})
        tiers_dict = data.get('tiers.json', {})
        recipes_dict = data.get('recipes.json', {})
        
        print(f" Reference data loaded:")
        print(f"   Materials: {len(materials_dict)}")
        print(f"   Categories: {len(categories_dict)}")
        print(f"   Tiers: {len(tiers_dict)}")
        print(f"   Recipes: {len(recipes_dict)}")
        
        # Use processed_data.csv as base, which has recipe-specific rows
        if 'processed_data.csv' in data and not data['processed_data.csv'].empty:
            base_df = data['processed_data.csv'].copy()
            print(f"   Base df from processed data: {len(base_df)} rows")
        else:
            print("   No processed data found")
            return None
        
        # Merge market data if available
        if 'market_data.csv' in data and not data['market_data.csv'].empty:
            market_df = data['market_data.csv'].copy()
            print(f"   Merging market data: {len(market_df)} rows")
            # Transform market_data.csv to long format if needed
            if 'Exchange' not in market_df.columns:
                # Wide format - transform
                melted = market_df.melt(id_vars=['Ticker'], var_name='var', value_name='value')
                melted = melted[melted['var'].str.contains('-')]
                melted['Exchange'] = melted['var'].str.split('-').str[0]
                melted['Metric'] = melted['var'].str.split('-').str[1]
                # Pivot to wide
                pivoted = melted.pivot_table(index=['Ticker', 'Exchange'], columns='Metric', values='value', aggfunc='first').reset_index()
                pivoted.columns.name = None
                # Rename columns to match
                pivoted.rename(columns={
                    'AskPrice': 'Ask_Price',
                    'BidPrice': 'Bid_Price',
                    'AskAvail': 'Supply',
                    'BidAvail': 'Demand',
                    'Average': 'Traded'
                }, inplace=True)
            else:
                # Already long format
                pivoted = market_df.copy()
                pivoted.rename(columns={
                    'AskPrice': 'Ask_Price',
                    'BidPrice': 'Bid_Price',
                    'AskAvail': 'Supply',
                    'BidAvail': 'Demand',
                    'Average': 'Traded'
                }, inplace=True)
            # Merge with base_df on Ticker and Exchange
            # First, drop the columns to ensure they are updated
            base_df = base_df.drop(columns=['Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded Volume'], errors='ignore')
            base_df = base_df.merge(pivoted[['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded']], on=['Ticker', 'Exchange'], how='left')
            print(f"   After market merge: {len(base_df)} rows")
        else:
            print("   No market data to merge")
            base_df['Ask_Price'] = 0.0
            base_df['Bid_Price'] = 0.0
            base_df['Supply'] = 0
            base_df['Demand'] = 0
            base_df['Traded'] = 0.0
        
        # Apply byproduct cost allocation
        # base_df = self.allocate_byproduct_costs_in_df(base_df, data)
        
        # Load materials for info
        materials_df = self.load_materials()
        
        # Generate analysis data
        analysis_data = []

        for _, row in base_df.iterrows():
            ticker = row['Ticker']
            material_info = self.get_material_info(ticker)
            
            # Use recipe from merged data, fallback to get_recipe
            recipe = row.get('Recipe', '') or self.get_recipe(ticker)
            amount_per_recipe = self.get_amount_per_recipe(ticker)
            
            analysis_row = {
                'Material Name': material_info.get('Material Name', ''),
                'Ticker': ticker,
                'Category': material_info.get('Category', ''),
                'Tier': material_info.get('Tier', ''),
                'Recipe': recipe,
                'Amount per Recipe': amount_per_recipe,
                'Weight': material_info.get('Weight', ''),
                'Volume': material_info.get('Volume', ''),
                'Ask_Price': row.get('Ask_Price', 0),
                'Bid_Price': row.get('Bid_Price', 0),
                'Input Cost per Unit': row.get('Input Cost per Unit', 0),
                'Input Cost per Stack': row.get('Input Cost per Stack', 0),
                'Input Cost per Hour': row.get('Input Cost per Hour', 0),
                'Profit per Unit': row.get('Profit per Unit', 0),
                'Profit per Stack': 0,  # Will be calculated
                'ROI Ask %': row.get('ROI Ask %', 0),
                'ROI Bid %': row.get('ROI Bid %', 0),
                'Supply': pd.to_numeric(row.get('Supply', 0), errors='coerce') or 0,
                'Demand': pd.to_numeric(row.get('Demand', 0), errors='coerce') or 0,
                'Traded Volume': pd.to_numeric(row.get('Traded', row.get('Traded Volume', 0)), errors='coerce') or 0,
                'Saturation': row.get('Saturation', 0),
                'Market Cap': 0,  # Will be calculated
                'Liquidity Ratio': 0,  # Will be calculated
                'Investment Score': row.get('Investment_Score', 0),
                'Risk Level': row.get('Risk', 'Low'),
                'Volatility': 0,
                'Exchange': row['Exchange'],
            }
            analysis_data.append(analysis_row)

        result_df = pd.DataFrame(analysis_data)
        # Ensure all required columns are present and in the correct order
        for col in self.target_columns:
            if col not in result_df.columns:
                result_df[col] = ""
        result_df = result_df[self.target_columns]

        # --- ENSURE CORRECT COLUMN NAMES FOR DOWNSTREAM ---
        rename_map = {
            'Profit_Ask': 'Profit per Unit',
            'Profit per Unit': 'Profit per Unit',
            'ROI_Ask': 'ROI Ask %',
            'ROI Bid %': 'ROI Bid %',
            'Traded': 'Traded Volume',
            'Traded Volume': 'Traded Volume',
        }
        result_df = result_df.rename(columns=rename_map)

        # Add missing columns for upload compatibility
        for col in [
            'ROI Ask %', 'ROI Bid %', 'Traded Volume'
        ]:
            if col not in result_df.columns:
                result_df[col] = 0

        # Fill NaN with 0 for numeric columns
        numeric_cols = ['Ask_Price', 'Bid_Price', 'Input Cost per Unit', 'Input Cost per Stack', 'Input Cost per Hour', 'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %', 'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap', 'Liquidity Ratio', 'Investment Score', 'Amount per Recipe', 'Weight', 'Volume', 'Tier']
        result_df[numeric_cols] = result_df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

        # Recalculate formulas
        result_df['Profit per Unit'] = pd.to_numeric(result_df['Ask_Price'], errors='coerce').fillna(0) - pd.to_numeric(result_df['Input Cost per Unit'], errors='coerce').fillna(0)
        result_df['Input Cost per Stack'] = result_df['Input Cost per Unit'] * result_df['Amount per Recipe']
        result_df['Profit per Stack'] = result_df['Profit per Unit'] * result_df['Amount per Recipe']
        result_df['ROI Ask %'] = result_df.apply(
            lambda row: (row['Profit per Unit'] / row['Input Cost per Unit'] * 100) if row['Input Cost per Unit'] > 0 else 0,
            axis=1
        )
        result_df['ROI Bid %'] = result_df.apply(
            lambda row: ((row['Bid_Price'] - row['Input Cost per Unit']) / row['Input Cost per Unit'] * 100) if row['Input Cost per Unit'] > 0 else 0,
            axis=1
        )
        result_df['Saturation'] = result_df.apply(
            lambda row: min(200.0, round((row['Supply'] / row['Demand']) * 100, 2)) if row['Demand'] > 0 else 100.0,
            axis=1
        )
        result_df['Market Cap'] = result_df['Supply'] * result_df['Ask_Price']
        result_df['Liquidity Ratio'] = result_df.apply(
            lambda row: row['Traded Volume'] / (row['Supply'] + row['Demand']) if (row['Supply'] + row['Demand']) > 0 else 0,
            axis=1
        )
        result_df['Risk Level'] = result_df.apply(
            lambda row: 'High' if row['Ask_Price'] > 0 and (row['Ask_Price'] - row['Bid_Price']) > row['Ask_Price'] * 0.2
            else ('Medium' if row['Ask_Price'] > 0 and (row['Ask_Price'] - row['Bid_Price']) > row['Ask_Price'] * 0.1
            else 'Low'),
            axis=1
        )
        result_df['Input Cost per Stack'] = result_df['Input Cost per Unit'] * result_df['Amount per Recipe']

        # --- ADD THIS: Apply the new investment score ---
        result_df['Investment Score'] = result_df.apply(self.compute_investment_score, axis=1)

        result_df.to_csv(self.cache_dir / "daily_analysis_enhanced.csv", index=False)
        print(f"\n Generated analysis: {len(result_df)} rows, {len(result_df.columns)} columns")
        print(f" Saved to: {self.cache_dir / 'daily_analysis_enhanced.csv'}")
        return result_df
        
    def allocate_byproduct_costs_in_df(self, df, data):
        """Allocate costs for byproduct materials based on their recipes"""
        print("   Applying byproduct cost allocation...")
        
        # Load byproduct recipes
        byproduct_recipes = {}
        byproduct_file = self.cache_dir / 'byproduct_recipes.json'
        if byproduct_file.exists():
            try:
                with open(byproduct_file, 'r') as f:
                    byproduct_recipes = json.load(f)
                print(f"   Loaded {len(byproduct_recipes)} byproduct recipes")
            except Exception as e:
                print(f"   Error loading byproduct recipes: {e}")
                return df
        
        # Load market data for prices
        market_prices = None
        if 'market_data.csv' in data:
            market_df = data['market_data.csv']
            # Convert to long format if needed
            if 'Exchange' not in market_df.columns:
                # Wide format - convert
                records = []
                exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
                for _, row in market_df.iterrows():
                    ticker = str(row['Ticker']).strip()
                    for exch in exchanges:
                        ask_price = row.get(f"{exch}-AskPrice")
                        if pd.notnull(ask_price) and ask_price != '':
                            records.append({
                                'Ticker': ticker.upper(),
                                'Exchange': exch,
                                'Ask_Price': float(ask_price)
                            })
                market_prices = pd.DataFrame(records)
            else:
                market_prices = market_df.copy()
                market_prices['Ticker'] = market_prices['Ticker'].str.upper()
        
        # For each byproduct recipe, allocate costs
        for recipe_id, recipe_info in byproduct_recipes.items():
            outputs = recipe_info.get('outputs', [])
            if len(outputs) <= 1:
                continue
            
            # Find the main product row (first output) to get the total input cost
            main_product = str(outputs[0]).upper()
            
            # Get total input cost from processed_data for this recipe
            if 'processed_data.csv' in data:
                processed_df = data['processed_data.csv']
                recipe_rows = processed_df[processed_df['Recipe'] == recipe_id]
                if not recipe_rows.empty:
                    # Use the first row's input cost (they should be the same for the recipe)
                    total_input_cost = recipe_rows.iloc[0]['Input Cost per Unit']
                    units_produced = recipe_rows.iloc[0].get('Amount', 1)  # Assuming Amount column exists
                    
                    # Calculate total recipe cost
                    total_recipe_cost = total_input_cost * units_produced
                    
                    # Get market values for allocation
                    output_values = {}
                    total_value = 0.0
                    
                    for ticker in outputs:
                        ticker_upper = str(ticker).upper()
                        if market_prices is not None:
                            # Get average price across exchanges
                            ticker_prices = market_prices[market_prices['Ticker'] == ticker_upper]
                            if not ticker_prices.empty:
                                avg_price = ticker_prices['Ask_Price'].mean()
                                output_values[ticker_upper] = avg_price
                                total_value += avg_price
                    
                    # Allocate costs proportionally
                    if total_value > 0:
                        for ticker in outputs:
                            ticker_upper = str(ticker).upper()
                            if ticker_upper in output_values:
                                proportion = output_values[ticker_upper] / total_value
                                allocated_cost_per_unit = (total_recipe_cost * proportion) / units_produced
                                
                                # Update the cost in df for this byproduct
                                mask = (df['Ticker'] == ticker_upper)
                                df.loc[mask, 'Input Cost per Unit'] = allocated_cost_per_unit
                                # Note: Input Cost per Stack will be calculated later in the analysis
                    
                    print(f"   Allocated costs for recipe {recipe_id}: {outputs}")
        
        return df
        
    def get_ticker_from_row(self, row):
        """Extract ticker from row using various column names"""
        ticker_columns = ['Ticker', 'ticker', 'MaterialTicker', 'Symbol', 'Code']
        for col in ticker_columns:
            if col in row and pd.notna(row[col]):
                return str(row[col]).strip()
        return None
        
    def get_price_data(self, row, price_type):
        """Get price data (current, ask, bid)"""
        if price_type == 'current':
            price_columns = ['Current Price', 'Price', 'price', 'Ask_Price', 'Ask']
        elif price_type == 'ask':
            price_columns = ['Ask', 'Ask_Price', 'ask', 'AskPrice']
        elif price_type == 'bid':
            price_columns = ['Bid', 'Bid_Price', 'bid', 'BidPrice']
        else:
            return 0
            
        for col in price_columns:
            if col in row and pd.notna(row[col]):
                return pd.to_numeric(row[col], errors='coerce') or 0
                
        return 0
        
    def get_market_data(self, row, data_type):
        """Get market data (supply, demand, traded)"""
        if data_type == 'supply':
            columns = ['Supply', 'supply', 'Available', 'Stock']
        elif data_type == 'demand':
            columns = ['Demand', 'demand', 'Wanted', 'Orders']
        elif data_type == 'traded':
            columns = ['Traded Volume', 'Traded', 'traded', 'Volume']
        else:
            return 0
            
        for col in columns:
            if col in row and pd.notna(row[col]):
                return pd.to_numeric(row[col], errors='coerce') or 0
                
        return 0

    # If you have a DataFrame 'price_history' with columns: 'Material', 'Date', 'Price', 'Volume'
    def compute_volatility(self, price_history, material, window=7):
        mat_hist = price_history[price_history['Material'] == material].sort_values('Date')
        if mat_hist.empty:
            return 0, 0
        mat_hist['Price_Std'] = mat_hist['Price'].rolling(window=window, min_periods=1).std()
        mat_hist['VW_Volatility'] = (
            mat_hist['Price'].rolling(window=window, min_periods=1)
            .apply(lambda x: (x * mat_hist['Volume']).sum() / mat_hist['Volume'].sum() if mat_hist['Volume'].sum() > 0 else 0)
        )
        return mat_hist['Price_Std'].iloc[-1], mat_hist['VW_Volatility'].iloc[-1]

    @staticmethod
    def compute_investment_score(row):
        """
        Compute a robust investment score for PrUn-Tracker.
        Returns a value between 0 (avoid) and 100 (top investment).
        """
        def to_num(val, default=0):
            try:
                return float(val)
            except Exception:
                return default

        roi = max(to_num(row.get('ROI Ask %', 0)), to_num(row.get('ROI Bid %', 0)))
        profit = max(to_num(row.get('Profit per Unit', 0)), 0)
        liquidity_ratio = to_num(row.get('Liquidity Ratio', 0))
        traded = to_num(row.get('Traded Volume', 0))
        supply = to_num(row.get('Supply', 0))
        demand = to_num(row.get('Demand', 0))
        saturation = to_num(row.get('Saturation', 100))
        spread = abs(to_num(row.get('Ask_Price', 0)) - to_num(row.get('Bid_Price', 0)))
        ask_price = to_num(row.get('Ask_Price', 0))
        volatility = to_num(row.get('Volatility', 0))

        if demand < 1 or supply < 1 or traded < 1:
            return 0
        if roi <= 0 or profit <= 0:
            return 0
        if ask_price <= 0:
            return 0

        roi_score = min(roi / 50, 1)
        liquidity_score = min(liquidity_ratio / 0.2, 1)
        traded_score = min(traded / 1000, 1)
        saturation_score = 1 - abs(saturation - 100) / 100
        spread_score = 1 - min(spread / ask_price, 1) if ask_price else 0
        volatility_score = 1 - min(volatility / 50, 1)

        score = (
            0.35 * roi_score +
            0.20 * liquidity_score +
            0.15 * traded_score +
            0.10 * saturation_score +
            0.10 * spread_score +
            0.10 * volatility_score
        ) * 100

        if saturation > 180 or saturation < 20:
            score *= 0.7
        if ask_price and spread / ask_price > 0.5:
            score *= 0.7
        if volatility > 50:
            score *= 0.7

        return round(score, 2)

def main():
    print("\n\033[1;35m[DATA ANALYZER]\033[0m")
    """Main entry point"""
    print("Starting Unified Analysis Processor")
    print("=" * 50)
    
    try:
        processor = UnifiedAnalysisProcessor()
        result = processor.generate_unified_analysis()
        if result is not None:
            print(f"\n SUCCESS: Generated {len(result)} rows with 24 columns")
            # Show summary of generated data
            output_file = processor.cache_dir / 'daily_analysis_enhanced.csv'
            print(f" Output file: {output_file}")
            print(f" File size: {output_file.stat().st_size / 1024:.1f} KB")
            # Show sample data
            print(f"\n Sample data (first 3 rows):")
            print(result.head(3)[['Material Name', 'Ticker', 'Ask_Price', 'Bid_Price', 'Investment Score']].to_string())
            return True
        else:
            print(f"\n FAILED: Could not generate analysis")
            return False
    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)