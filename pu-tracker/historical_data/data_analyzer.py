"""
SINGLE UNIFIED ANALYSIS FILE
Generates the exact 24-column structure for Google Sheets upload
Uses existing cache data and outputs to daily_analysis_enhanced.csv
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

class UnifiedAnalysisProcessor:
    def __init__(self):
        print("\n\033[1;36m[STEP]\033[0m Initializing UnifiedAnalysisProcessor...")
        # Ensure we're using the correct cache directory
        self.cache_dir = Path(__file__).parent.parent / 'cache'
        print(f" Cache directory: {self.cache_dir}")
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load material and recipe data
        self.materials = pd.read_csv(self.cache_dir / 'materials.csv')
        self.recipe_outputs = pd.read_csv(self.cache_dir / 'recipe_outputs.csv')
        self.recipe_inputs = pd.read_csv(self.cache_dir / 'recipe_inputs.csv')
        
        self.target_columns = [
            'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe', 
            'Amount per Recipe', 'Weight', 'Volume', 
            'Ask_Price', 'Bid_Price',
            'Input Cost per Unit', 'Input Cost per Stack', 'Input Cost per Hour',
            'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %',
            'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap',
            'Liquidity Ratio', 'Investment Score', 'Risk Level', 'Volatility',
            'Exchange'
        ]
        
        self._materials_cache = None
        self._materials_mtime = None
        self.buildingrecipes_df = self.load_buildingrecipes()
        self.workforceneeds = self.load_workforceneeds()
        
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
                    data[file] = pd.read_csv(path)
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

    def load_buildingrecipes(self):
        path = self.cache_dir / "buildingrecipes.csv"
        if not path.exists():
            print("[WARN] buildingrecipes.csv not found, workforce costs will be skipped.")
            return None
        df = pd.read_csv(path)
        # Use 'Key' as the recipe identifier
        if "Key" not in df.columns:
            print("[WARN] buildingrecipes.csv missing 'Key' column.")
            return None
        return df.set_index("Key")

    def load_workforceneeds(self):
        path = self.cache_dir / "workforceneeds.json"
        if not path.exists():
            print("[WARN] workforceneeds.json not found, using static mapping.")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Convert to: { "Pioneers": {"RAT": 0.5, ...}, ... }
        needs = {}
        for wf in data:
            name = wf.get("name")
            needs[name] = {}
            for need in wf.get("needs", []):
                ticker = need.get("ticker")
                per_hour = need.get("amountPerWorkerPerHour")
                needs[name][ticker] = per_hour
        return needs

    def calculate_input_cost(self, ticker, market_prices):
        """
        For a given product ticker, find all recipes that produce it.
        For each recipe, sum the cost of all inputs (from recipe_inputs.csv) using market prices,
        plus workforce consumables for the recipe time (from workforceneeds.json).
        Return the minimum input cost found (best recipe).
        """
        recipes = self.recipe_outputs[self.recipe_outputs['Material'] == ticker]
        if recipes.empty:
            return 0  # No recipe found

        min_cost = None
        for _, recipe_row in recipes.iterrows():
            recipe_key = recipe_row['Key']
            # 1. Material input cost
            inputs = self.recipe_inputs[self.recipe_inputs['Key'] == recipe_key]
            material_input_cost = 0
            for _, inp in inputs.iterrows():
                input_ticker = inp['Material']
                try:
                    amount = float(inp['Amount'])
                except Exception:
                    amount = 0
                price = float(market_prices.get(input_ticker, 0))
                material_input_cost += amount * price

            # 2. Workforce consumable cost
            workforce_cost = 0
            if self.buildingrecipes_df is not None and recipe_key in self.buildingrecipes_df.index:
                recipe_info = self.buildingrecipes_df.loc[recipe_key]
                try:
                    time_minutes = float(recipe_info.get("Time", 0))
                    time_hours = time_minutes / 60
                    workforce_type = recipe_info.get("Workforce", None)
                    workforce_amount = float(recipe_info.get("WorkforceAmount", 0))
                    if workforce_type and workforce_type in self.workforceneeds:
                        consumables = self.workforceneeds[workforce_type]
                        for item, per_hour in consumables.items():
                            try:
                                total_needed = float(per_hour) * workforce_amount * time_hours
                            except Exception:
                                total_needed = 0
                            price = float(market_prices.get(item, 0))
                            workforce_cost += total_needed * price
                    else:
                        if workforce_type:
                            print(f"[WARN] Workforce type '{workforce_type}' not found in workforceneeds.json")
                except Exception as e:
                    print(f"[WARN] Error calculating workforce cost for {recipe_key}: {e}")

            total_cost = material_input_cost + workforce_cost
            if min_cost is None or total_cost < min_cost:
                min_cost = total_cost
        return min_cost if min_cost is not None else 0

    def load_materials(self):
        path = self.cache_dir / 'materials.csv'
        mtime = os.path.getmtime(path)
        if self._materials_cache is not None and self._materials_mtime == mtime:
            return self._materials_cache
        self._materials_cache = pd.read_csv(path)
        self._materials_mtime = mtime
        return self._materials_cache

    def generate_unified_analysis(self):
        print("\n\033[1;36m[STEP]\033[0m Generating unified analysis for Google Sheets...")
        """Generate the complete 24-column analysis"""
        # Load all data
        data = self.load_cache_data()
        
        # Show data structure
        self.inspect_data_structure(data)
        
        # Determine best data source
        base_df = None
        
        # Priority: processed_data.csv > market_data.csv > materials.csv
        if 'processed_data.csv' in data and not data['processed_data.csv'].empty:
            base_df = data['processed_data.csv'].copy()
            print(f"\n Using processed_data.csv as base ({len(base_df)} rows)")
        elif 'market_data.csv' in data and not data['market_data.csv'].empty:
            base_df = data['market_data.csv'].copy()
            print(f"\n Using market_data.csv as base ({len(base_df)} rows)")
        elif 'materials.csv' in data and not data['materials.csv'].empty:
            base_df = data['materials.csv'].copy()
            print(f"\n Using materials.csv as base ({len(base_df)} rows)")
        else:
            print("\n No suitable base data found")
            return None
            
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
        
        # Show available columns for mapping
        print(f"\n Available columns in base data:")
        for i, col in enumerate(base_df.columns, 1):
            print(f"   {i:2d}. {col}")
            
        # Build a market_prices dictionary for all tickers in materials.csv
        market_prices = {}
        for _, mat_row in self.materials.iterrows():
            ticker = mat_row['Ticker']
            # Try to find this ticker in base_df
            base_row = base_df[base_df['Ticker'] == ticker]
            if not base_row.empty:
                price = self.get_price_data(base_row.iloc[0], 'ask')
                if price:
                    market_prices[ticker] = price
        
        # Generate analysis data
        analysis_data = []

        for _, row in base_df.iterrows():
            ticker = row['Ticker']
            material_info = self.get_material_info(ticker)
            analysis_row = {
                'Material Name': material_info.get('Material Name', ''),
                'Ticker': ticker,
                'Category': material_info.get('Category', ''),
                'Tier': material_info.get('Tier', ''),
                'Recipe': self.get_recipe(ticker),
                'Amount per Recipe': self.get_amount_per_recipe(ticker),
                'Weight': material_info.get('Weight', ''),
                'Volume': material_info.get('Volume', ''),
                'Ask_Price': row.get('Ask_Price', ''),
                'Bid_Price': row.get('Bid_Price', ''),
                'Input Cost per Unit': row.get('Input Cost per Unit', ''),
                'Input Cost per Stack': row.get('Input Cost per Stack', ''),
                'Input Cost per Hour': row.get('Input Cost per Hour', ''),
                'Profit per Unit': row.get('Profit_Ask', ''),
                'Profit per Stack': '',  # You can compute this if needed
                'ROI Ask %': row.get('ROI_Ask', ''),
                'ROI Bid %': row.get('ROI_Bid', ''),
                'Supply': row.get('Supply', ''),
                'Demand': row.get('Demand', ''),
                'Traded Volume': row.get('Traded', row.get('Traded Volume', 0)),  # Ensure this is filled
                'Saturation': row.get('Saturation', ''),
                'Market Cap': '',  # Compute if you have the data
                'Liquidity Ratio': '',  # Compute if you have the data
                'Investment Score': row.get('Investment_Score', ''),
                'Risk Level': row.get('Risk', ''),
                'Volatility': '',  # Compute if you have the data
                'Exchange': row.get('Exchange', ''),
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

        # Add/correct formulas for missing columns
        result_df['Profit per Unit'] = pd.to_numeric(result_df['Ask_Price'], errors='coerce').fillna(0) - pd.to_numeric(result_df['Input Cost per Unit'], errors='coerce').fillna(0)
        # FIX: Use Amount per Recipe for stack calculation
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