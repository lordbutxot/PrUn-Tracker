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
            'Ask Price', 'Bid Price',  # <-- Add these
            'Input Cost per Unit', 'Input Cost per Stack', 
            'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %',
            'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap',
            'Liquidity Ratio', 'Investment Score', 'Risk Level', 'Volatility',
            'Exchange'  # <-- Add this
        ]
        
        self._materials_cache = None
        self._materials_mtime = None
        
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
        
    def calculate_investment_score(self, roi_ask, liquidity_ratio, saturation):
        """Calculate investment score (0-100)"""
        score = 0

        # Safely handle None or non-numeric ROI
        try:
            roi = float(roi_ask)
        except (TypeError, ValueError):
            roi = None

        # ROI component (40%)
        if roi is not None:
            if roi > 20:
                score += 40
            elif roi > 10:
                score += 30
            elif roi > 0:
                score += 20

        # Liquidity component (30%)
        if liquidity_ratio > 10:
            score += 30
        elif liquidity_ratio > 5:
            score += 20
        elif liquidity_ratio > 1:
            score += 10

        # Saturation component (30%) - INVERSE
        if saturation < 20:
            score += 30
        elif saturation < 40:
            score += 20
        elif saturation < 60:
            score += 10

        return min(score, 100)
        
    def calculate_risk_level(self, saturation, liquidity_ratio, profit_per_unit, traded_volume):
        """Calculate risk level, now considering traded volume"""
        if saturation > 70 or liquidity_ratio < 1 or profit_per_unit < 0 or traded_volume < 10:
            return "High"
        elif saturation > 40 or liquidity_ratio < 5 or traded_volume < 100:
            return "Medium"
        else:
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

    def calculate_input_cost(self, ticker, market_prices):
        """
        For a given product ticker, find all recipes that produce it.
        For each recipe, sum the cost of all inputs (from recipe_inputs.csv) using market prices.
        Return the minimum input cost found (best recipe).
        """
        # Find all recipes that produce this ticker
        recipes = self.recipe_outputs[self.recipe_outputs['Material'] == ticker]
        if recipes.empty:
            return 0  # No recipe found

        min_cost = None
        for _, recipe_row in recipes.iterrows():
            recipe_key = recipe_row['Key']
            # Find all inputs for this recipe
            inputs = self.recipe_inputs[self.recipe_inputs['Key'] == recipe_key]
            total_cost = 0
            for _, inp in inputs.iterrows():
                input_ticker = inp['Material']
                amount = inp['Amount']
                price = market_prices.get(input_ticker, 0)
                total_cost += amount * price
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
        
        # If you have price_history loaded:
        # price_history = pd.read_csv(self.cache_dir / 'prices_all.csv')  # Example

        for _, row in base_df.iterrows():
            # Get ticker/material identification
            ticker = self.get_ticker_from_row(row)
            if not ticker:
                continue
                
            # Basic material info
            info = self.get_material_info(ticker)
            material_name = info['Material Name']
            category = info['Category']
            tier = info['Tier']
            weight = info['Weight']
            volume = info['Volume']
            
            # Recipe info
            recipe = self.get_recipe(ticker)
            amount_per_recipe = self.parse_output_amount_from_recipe(recipe, ticker)
            input_cost = self.calculate_input_cost(ticker, market_prices)
            input_cost_per_unit = input_cost / amount_per_recipe if amount_per_recipe else 0
            input_cost_per_stack = input_cost_per_unit * amount_per_recipe
            
            # Market data
            current_price = self.get_price_data(row, 'current')
            ask_price = self.get_price_data(row, 'ask') or current_price
            bid_price = self.get_price_data(row, 'bid') or current_price
            supply = self.get_market_data(row, 'supply')
            demand = self.get_market_data(row, 'demand')
            traded_volume = self.get_market_data(row, 'traded') or (supply + demand if supply and demand else 0)
            
            # Calculate profits
            profit_per_unit = current_price - input_cost_per_unit if current_price and input_cost_per_unit else 0
            profit_per_stack = profit_per_unit * 100
            
            # Calculate ROI
            roi_ask, roi_bid = self.calculate_roi_ask_bid(ask_price, bid_price, input_cost_per_unit)
            
            # Calculate market metrics
            market_cap = current_price * supply if current_price and supply else 0
            liquidity_ratio = (traded_volume / supply * 100) if supply > 0 else 0
            saturation = self.calculate_saturation(supply, demand, traded_volume)
            
            # Calculate scores
            investment_score = self.calculate_investment_score(roi_ask, liquidity_ratio, saturation)
            risk_level = self.calculate_risk_level(saturation, liquidity_ratio, profit_per_unit, traded_volume)
            
            # Compute volatility if price_history is available
            price_volatility = None
            vw_volatility = None
            # Uncomment and use if you have price_history loaded
            # if 'price_history' in locals():
            #     price_volatility, vw_volatility = self.compute_volatility(price_history, material_name)
            
            # Build row
            analysis_row = {
                'Material Name': material_name,
                'Ticker': ticker,
                'Category': category,
                'Tier': tier,
                'Recipe': recipe,
                'Amount per Recipe': amount_per_recipe,
                'Weight': weight,
                'Volume': volume,
                'Ask Price': ask_price,
                'Bid Price': bid_price,
                'Input Cost per Unit': input_cost_per_unit,
                'Input Cost per Stack': input_cost_per_stack,
                'Profit per Unit': profit_per_unit,
                'Profit per Stack': profit_per_stack,
                'ROI Ask %': roi_ask,
                'ROI Bid %': roi_bid,
                'Supply': supply,
                'Demand': demand,
                'Traded Volume': traded_volume,
                'Saturation': saturation,
                'Market Cap': market_cap,
                'Liquidity Ratio': liquidity_ratio,
                'Investment Score': investment_score,
                'Risk Level': risk_level,
                'Volatility': price_volatility if price_volatility is not None else abs(roi_ask - roi_bid) if roi_ask and roi_bid else 0
            }
            # Add Exchange if present in base_df
            if 'Exchange' in row:
                analysis_row['Exchange'] = row['Exchange']
            else:
                analysis_row['Exchange'] = ''  # or set to None

            analysis_data.append(analysis_row)
            
        # Create final DataFrame
        result_df = pd.DataFrame(analysis_data)
        
        # Ensure all target columns exist
        for col in self.target_columns:
            if col not in result_df.columns:
                result_df[col] = None
                
        # Reorder columns
        result_df = result_df[self.target_columns]
        
        # Fill NA values for ROI columns with 0 for normalization
        result_df[['ROI Ask %', 'ROI Bid %']] = result_df[['ROI Ask %', 'ROI Bid %']].fillna(0)

        # Normalize columns (0-1 scale)
        scaler = MinMaxScaler()
        result_df[['ROI_Norm', 'Liquidity_Norm', 'Saturation_Norm']] = scaler.fit_transform(
            result_df[['ROI Ask %', 'Liquidity Ratio', 'Saturation']]
        )

        # Invert saturation (lower is better)
        result_df['Saturation_Norm'] = 1 - result_df['Saturation_Norm']

        # Add volatility and market cap normalization if available
        if 'Volatility' in result_df.columns:
            result_df['Volatility_Norm'] = 1 - scaler.fit_transform(result_df[['Volatility']])
        else:
            result_df['Volatility_Norm'] = 1

        if 'Market Cap' in result_df.columns:
            result_df['MarketCap_Norm'] = scaler.fit_transform(result_df[['Market Cap']])
        else:
            result_df['MarketCap_Norm'] = 1

        # Normalize Traded Volume (0-1 scale)
        if 'Traded Volume' in result_df.columns:
            result_df['TradedVolume_Norm'] = scaler.fit_transform(result_df[['Traded Volume']])
        else:
            result_df['TradedVolume_Norm'] = 0

        # Weighted sum (adjust weights as needed)
        result_df['Investment Score'] = (
            0.35 * result_df['ROI_Norm'] +
            0.25 * result_df['Liquidity_Norm'] +
            0.15 * result_df['Saturation_Norm'] +
            0.05 * result_df['Volatility_Norm'] +
            0.05 * result_df['MarketCap_Norm'] +
            0.15 * result_df['TradedVolume_Norm']
        ) * 100
        
        # Save result
        output_path = self.cache_dir / 'daily_analysis_enhanced.csv'
        result_df.to_csv(output_path, index=False)
        
        print(f"\n Generated analysis: {len(result_df)} rows, 24 columns")
        print(f" Saved to: {output_path}")
        
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
            print(result.head(3)[['Material Name', 'Ticker', 'Ask Price', 'Bid Price', 'Investment Score']].to_string())
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