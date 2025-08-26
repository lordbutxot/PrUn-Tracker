import pandas as pd
import numpy as np
import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# Set up module-level logger
logger = logging.getLogger(__name__)

class UnifiedReportBuilder:
    """Unified report builder that generates comprehensive reports for all exchanges."""
    
    def __init__(self, cache_dir: str = None):
        # Initialize logger for this instance
        self.logger = logging.getLogger(__name__)
        
        # Set cache directory
        if cache_dir is None:
            from historical_data.config import CACHE_DIR
            self.cache_dir = CACHE_DIR
        else:
            self.cache_dir = cache_dir
        
        # Load support data
        self.load_support_data()
        self.logger.info("Support data loaded successfully")
    
    def load_support_data(self):
        """Load all required support data from cache."""
        try:
            # Load categories
            categories_file = os.path.join(self.cache_dir, "categories.json")
            if os.path.exists(categories_file):
                with open(categories_file, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
            else:
                self.categories = {}
            
            # Load chains
            chains_file = os.path.join(self.cache_dir, "chains.json")
            if os.path.exists(chains_file):
                with open(chains_file, 'r', encoding='utf-8') as f:
                    self.chains = json.load(f)
            else:
                self.chains = {}
            
            # Load buildings
            buildings_file = os.path.join(self.cache_dir, "buildings.json")
            if os.path.exists(buildings_file):
                with open(buildings_file, 'r', encoding='utf-8') as f:
                    self.buildings = json.load(f)
            else:
                self.buildings = {}
            
            self.logger.info(f"Loaded: {len(self.categories)} categories, {len(self.chains)} chains, {len(self.buildings)} buildings")
            
        except Exception as e:
            self.logger.error(f"Error loading support data: {e}")
            # Set empty defaults
            self.categories = {}
            self.chains = {}
            self.buildings = {}
    
    def load_processed_data(self) -> pd.DataFrame:
        """Load processed data from cache."""
        try:
            processed_data_file = os.path.join(self.cache_dir, "processed_data.csv")
            if os.path.exists(processed_data_file):
                df = pd.read_csv(processed_data_file)
                self.logger.info(f"Using existing processed data: {len(df)} rows")
                return df
            else:
                self.logger.warning("No processed data file found")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error loading processed data: {e}")
            return pd.DataFrame()
    
    def generate_comprehensive_report(self, exchange: str) -> pd.DataFrame:
        """Generate comprehensive report for a specific exchange."""
        try:
            self.logger.info(f"Starting comprehensive report generation for {exchange}")
            
            # Load processed data
            processed_df = self.load_processed_data()
            
            if processed_df.empty:
                self.logger.error(f"No processed data available for {exchange}")
                return pd.DataFrame()
            
            # Filter for specific exchange
            exchange_data = processed_df[processed_df['Exchange'] == exchange].copy()
            
            if exchange_data.empty:
                self.logger.warning(f"No data found for exchange {exchange}")
                # Debug: Show what exchanges are available
                available_exchanges = processed_df['Exchange'].unique()
                self.logger.info(f"Available exchanges: {available_exchanges}")
                return pd.DataFrame()
            
            self.logger.info(f"Generating comprehensive report for {exchange} with {len(exchange_data)} rows")
            
            # Create comprehensive report
            report_data = []
            error_count = 0
            
            for idx, row in exchange_data.iterrows():
                try:
                    ticker = str(row.get('Ticker', '')).upper()
                    
                    # Get material info
                    category = self.categories.get(ticker.lower(), 'Unknown')
                    chain_info = self.chains.get(ticker.lower(), {})
                    
                    # Extract price data safely
                    ask_price = self._safe_float(row.get('Ask_Price', 0))
                    bid_price = self._safe_float(row.get('Bid_Price', 0))
                    
                    # Get availability data
                    ask_avail_col = f"{exchange}-AskAvail"
                    bid_avail_col = f"{exchange}-BidAvail"
                    ask_amt_col = f"{exchange}-AskAmt"
                    bid_amt_col = f"{exchange}-BidAmt"
                    
                    supply = self._safe_int(row.get(ask_avail_col, 0))
                    demand = self._safe_int(row.get(bid_avail_col, 0))
                    ask_amount = self._safe_int(row.get(ask_amt_col, 0))
                    bid_amount = self._safe_int(row.get(bid_amt_col, 0))
                    
                    # Calculate derived metrics
                    price_spread = round(ask_price - bid_price, 2) if ask_price > 0 and bid_price > 0 else 0
                    input_cost = self._safe_float(row.get('Input Cost', 0))
                    profit_ask = round(ask_price - input_cost, 2) if ask_price > 0 and input_cost > 0 else 0
                    profit_bid = round(bid_price - input_cost, 2) if bid_price > 0 and input_cost > 0 else 0
                    
                    # ROI calculations
                    roi_ask = round((profit_ask / input_cost) * 100, 1) if input_cost > 0 else 0
                    roi_bid = round((profit_bid / input_cost) * 100, 1) if input_cost > 0 else 0
                    
                    # Build input materials string
                    inputs = chain_info.get('inputs', [])
                    input_materials = ', '.join(inputs[:3]) if inputs else 'None'  # Limit to 3 for readability
                    
                    report_row = {
                        'Ticker': ticker,
                        'Product': ticker,
                        'Category': category,
                        'Tier': chain_info.get('tier', 0),
                        'Input Materials': input_materials,
                        'Input Cost': round(input_cost, 2),
                        'Ask Price': round(ask_price, 2),
                        'Bid Price': round(bid_price, 2),
                        'Price Spread': price_spread,
                        'Supply': supply,
                        'Demand': demand,
                        'Ask Amount': ask_amount,
                        'Bid Amount': bid_amount,
                        'Profit (Ask)': profit_ask,
                        'Profit (Bid)': profit_bid,
                        'ROI (Ask)': roi_ask,
                        'ROI (Bid)': roi_bid,
                        'Investment Score': round(self._safe_float(row.get('Investment_Score', 0)), 1),
                        'Exchange': exchange
                    }
                    
                    report_data.append(report_row)
                    
                except Exception as e:
                    error_count += 1
                    if error_count <= 3:  # Only log first few errors to avoid spam
                        self.logger.error(f"Error processing row for {ticker} in {exchange}: {e}")
                    continue
            
            if error_count > 3:
                self.logger.warning(f"Total of {error_count} rows had processing errors in {exchange}")
            
            if not report_data:
                self.logger.warning(f"No valid report data generated for {exchange}")
                return pd.DataFrame()
            
            report_df = pd.DataFrame(report_data)
            
            # Sort by Investment Score descending
            report_df = report_df.sort_values('Investment Score', ascending=False)
            
            self.logger.info(f"Generated comprehensive report for {exchange}: {len(report_df)} rows")
            return report_df
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive report for {exchange}: {e}", exc_info=True)
            return pd.DataFrame()
    
    def _safe_float(self, value) -> float:
        """Safely convert value to float."""
        try:
            if pd.isna(value) or value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _safe_int(self, value) -> int:
        """Safely convert value to int."""
        try:
            if pd.isna(value) or value is None:
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0
    
    def build_daily_report(self) -> pd.DataFrame:
        """Build the basic daily report with essential market data only."""
        try:
            # Load market data directly for exchange-specific processing
            market_data_path = os.path.join(self.cache_dir, "market_data.csv")
            if not os.path.exists(market_data_path):
                self.logger.error("Market data not found")
                return pd.DataFrame()
            
            market_df = pd.read_csv(market_data_path)
            
            # Load materials data for names, weight, volume, category, tier
            materials_df = self.load_materials_data()
            
            # Load recipe data for recipe information
            recipe_data = self.load_recipe_data()
            
            # Build exchange-specific basic data (without advanced analysis)
            all_exchange_data = []
            exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
            
            for exchange in exchanges:
                exchange_data = self.build_basic_exchange_data(
                    market_df, materials_df, recipe_data, exchange
                )
                if not exchange_data.empty:
                    exchange_data['exchange'] = exchange
                    all_exchange_data.append(exchange_data)
            
            # Combine all exchange data
            if all_exchange_data:
                final_report = pd.concat(all_exchange_data, ignore_index=True)
                self.logger.info(f"Built daily report with {len(final_report)} rows across {len(all_exchange_data)} exchanges")
                return final_report
            else:
                self.logger.error("No exchange data generated")
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error building daily report: {e}")
            return pd.DataFrame()

    def build_daily_analysis(self) -> pd.DataFrame:
        """Build the optimized daily analysis with unique columns and improved data quality."""
        try:
            # Load market data directly for exchange-specific processing
            market_data_path = os.path.join(self.cache_dir, "market_data.csv")
            if not os.path.exists(market_data_path):
                self.logger.error("Market data not found")
                return pd.DataFrame()
            
            market_df = pd.read_csv(market_data_path)
            
            # Load materials data for names, weight, volume, category, tier
            materials_df = self.load_materials_data()
            
            # Load recipe data for recipe information
            recipe_data = self.load_recipe_data()
            
            # Build exchange-specific optimized analysis data
            all_exchange_data = []
            exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
            
            for exchange in exchanges:
                exchange_data = self.build_optimized_exchange_analysis(
                    market_df, materials_df, recipe_data, exchange
                )
                if not exchange_data.empty:
                    exchange_data['exchange'] = exchange
                    all_exchange_data.append(exchange_data)
            
            # Combine all exchange data
            if all_exchange_data:
                final_analysis = pd.concat(all_exchange_data, ignore_index=True)
                
                # Apply final data quality filters
                final_analysis = self.apply_analysis_filters(final_analysis)
                
                self.logger.info(f"Built optimized daily analysis with {len(final_analysis)} rows across {len(all_exchange_data)} exchanges")
                return final_analysis
            else:
                self.logger.error("No exchange analysis data generated")
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error building daily analysis: {e}")
            return pd.DataFrame()
    
    def calculate_input_cost(self, ticker: str, exchange: str, recipe_data: Dict, market_df: pd.DataFrame) -> float:
        """Calculate the input cost for producing one unit of the given material."""
        try:
            # Handle NaN ticker values
            ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
            if not ticker_str:
                return 0.0
                
            recipe_info = recipe_data.get(ticker_str, {})
            inputs = recipe_info.get('inputs', [])
            amount_per_recipe = recipe_info.get('amount_per_recipe', 1)
            
            if not inputs:
                return 0.0
            
            total_input_cost = 0.0
            
            for input_req in inputs:
                input_material = input_req['material']
                input_amount = input_req['amount']
                
                # Get the current price for this input material on this exchange
                input_price = self.get_material_price(input_material, exchange, market_df)
                
                # Add to total cost
                total_input_cost += input_price * input_amount
            
            # Calculate cost per unit (recipe produces amount_per_recipe units)
            if amount_per_recipe > 0:
                input_cost_per_unit = total_input_cost / amount_per_recipe
            else:
                input_cost_per_unit = 0.0
                
            return input_cost_per_unit
            
        except Exception as e:
            self.logger.error(f"Error calculating input cost for {ticker}: {e}")
            return 0.0
    
    def get_material_price(self, ticker: str, exchange: str, market_df: pd.DataFrame) -> float:
        """Get the current price for a material on a specific exchange."""
        try:
            # Convert ticker to string and handle NaN values
            ticker_str = str(ticker).upper() if pd.notna(ticker) and ticker != 'nan' else ''
            if not ticker_str:
                return 0.0
                
            # Find the row for this ticker
            ticker_data = market_df[market_df['Ticker'].str.upper() == ticker_str]
            
            if ticker_data.empty:
                return 0.0
            
            # Get exchange-specific price columns
            avg_col = f"{exchange}-Average"
            ask_col = f"{exchange}-AskPrice"
            bid_col = f"{exchange}-BidPrice"
            
            row = ticker_data.iloc[0]
            
            # Try average price first, then ask price, then bid price
            if avg_col in row and pd.notna(row[avg_col]) and row[avg_col] > 0:
                return float(row[avg_col])
            elif ask_col in row and pd.notna(row[ask_col]) and row[ask_col] > 0:
                return float(row[ask_col])
            elif bid_col in row and pd.notna(row[bid_col]) and row[bid_col] > 0:
                return float(row[bid_col])
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error getting price for {ticker} on {exchange}: {e}")
            return 0.0

    def build_basic_exchange_data(self, market_df: pd.DataFrame, materials_df: pd.DataFrame, 
                                    recipe_data: Dict, exchange: str) -> pd.DataFrame:
        """Build basic data for a specific exchange without advanced analysis."""
        try:
            exchange_data = []
            
            for _, row in market_df.iterrows():
                ticker = str(row['Ticker']).strip() if pd.notna(row['Ticker']) else ''
                if not ticker:
                    continue
                
                # Get exchange-specific columns
                avg_col = f"{exchange}-Average"
                ask_price_col = f"{exchange}-AskPrice"
                bid_price_col = f"{exchange}-BidPrice"
                ask_amt_col = f"{exchange}-AskAmt"
                bid_amt_col = f"{exchange}-BidAmt"
                ask_avail_col = f"{exchange}-AskAvail"
                bid_avail_col = f"{exchange}-BidAvail"
                
                # Get values (with fallback to 0)
                current_price = row.get(avg_col, 0) if pd.notna(row.get(avg_col, 0)) else 0
                ask_price = row.get(ask_price_col, 0) if pd.notna(row.get(ask_price_col, 0)) else 0
                bid_price = row.get(bid_price_col, 0) if pd.notna(row.get(bid_price_col, 0)) else 0
                supply = row.get(ask_avail_col, 0) if pd.notna(row.get(ask_avail_col, 0)) else 0
                demand = row.get(bid_avail_col, 0) if pd.notna(row.get(bid_avail_col, 0)) else 0
                traded_volume = row.get(ask_amt_col, 0) + row.get(bid_amt_col, 0) if pd.notna(row.get(ask_amt_col, 0)) and pd.notna(row.get(bid_amt_col, 0)) else 0
                
                # Skip if no meaningful data
                if current_price == 0 and ask_price == 0 and bid_price == 0:
                    continue
                
                # Get material information
                material_name = ticker  # Default to ticker
                category = "Unknown"
                tier = 0
                weight = 0
                volume = 0
                
                if not materials_df.empty:
                    # Handle NaN ticker values safely
                    ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
                    if ticker_str:
                        material_info = materials_df[materials_df['Ticker'].str.upper() == ticker_str]
                        if not material_info.empty:
                            material_name = material_info.iloc[0].get('Name', ticker)
                            category = material_info.iloc[0].get('Category', 'Unknown')
                            tier = material_info.iloc[0].get('Tier', 0)
                            weight = material_info.iloc[0].get('Weight', 0)
                            volume = material_info.iloc[0].get('Volume', 0)
                
                # Get recipe information
                ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
                recipe_key = recipe_data.get(ticker_str, {}).get('recipe_key', 'N/A') if ticker_str else 'N/A'
                amount_per_recipe = recipe_data.get(ticker_str, {}).get('amount_per_recipe', 1) if ticker_str else 1
                
                # Use amount_per_recipe as the stack size (recipe output = 1 stack)
                stack_size = amount_per_recipe
                
                # Calculate basic metrics with actual input costs
                input_cost_per_unit = self.calculate_input_cost(ticker, exchange, recipe_data, market_df)
                input_cost_per_stack = input_cost_per_unit * stack_size
                profit_per_unit = current_price - input_cost_per_unit
                profit_per_stack = profit_per_unit * stack_size
                roi_percentage = (profit_per_unit / current_price * 100) if current_price > 0 else 0
                market_cap = current_price * supply
                liquidity_ratio = demand / supply if supply > 0 else 0
                volatility = abs(ask_price - bid_price) / current_price if current_price > 0 else 0
                
                # Basic recommendation (simplified)
                if profit_per_unit > 0:
                    recommendation = "Produce"
                elif current_price > 0:
                    recommendation = "Buy"
                else:
                    recommendation = "Hold"
                
                exchange_data.append({
                    'Material Name': material_name,
                    'ticker': ticker,
                    'category': category,
                    'tier': tier,
                    'Recipe': recipe_key,
                    'Amount per Recipe': amount_per_recipe,
                    'Weight': weight,
                    'Volume': volume,
                    'Current Price': current_price,
                    'Ask Price': ask_price,
                    'Bid Price': bid_price,
                    'Price Spread': abs(ask_price - bid_price) if ask_price > 0 and bid_price > 0 else 0,
                    'Input Cost per Unit': input_cost_per_unit,
                    'Input Cost per Stack': input_cost_per_stack,
                    'Profit per Unit': profit_per_unit,
                    'Profit per Stack': profit_per_stack,
                    'ROI %': roi_percentage,
                    'Supply': supply,
                    'Demand': demand,
                    'Traded Volume': traded_volume,
                    'Market Cap': market_cap,
                    'Liquidity Ratio': liquidity_ratio,
                    'Volatility': volatility,
                    'Recommendation': recommendation
                })
            
            return pd.DataFrame(exchange_data)
            
        except Exception as e:
            self.logger.error(f"Error building basic {exchange} data: {e}")
            return pd.DataFrame()

    def build_advanced_exchange_data(self, market_df: pd.DataFrame, materials_df: pd.DataFrame, 
                                    recipe_data: Dict, exchange: str) -> pd.DataFrame:
        """Build advanced analysis data for a specific exchange with arbitrage, bottlenecks, etc."""
        try:
            exchange_data = []
            
            for _, row in market_df.iterrows():
                ticker = str(row['Ticker']).strip() if pd.notna(row['Ticker']) else ''
                if not ticker:
                    continue
                
                # Get exchange-specific columns
                avg_col = f"{exchange}-Average"
                ask_price_col = f"{exchange}-AskPrice"
                bid_price_col = f"{exchange}-BidPrice"
                ask_amt_col = f"{exchange}-AskAmt"
                bid_amt_col = f"{exchange}-BidAmt"
                ask_avail_col = f"{exchange}-AskAvail"
                bid_avail_col = f"{exchange}-BidAvail"
                
                # Get values (with fallback to 0)
                current_price = row.get(avg_col, 0) if pd.notna(row.get(avg_col, 0)) else 0
                ask_price = row.get(ask_price_col, 0) if pd.notna(row.get(ask_price_col, 0)) else 0
                bid_price = row.get(bid_price_col, 0) if pd.notna(row.get(bid_price_col, 0)) else 0
                supply = row.get(ask_avail_col, 0) if pd.notna(row.get(ask_avail_col, 0)) else 0
                demand = row.get(bid_avail_col, 0) if pd.notna(row.get(bid_avail_col, 0)) else 0
                traded_volume = row.get(ask_amt_col, 0) + row.get(bid_amt_col, 0) if pd.notna(row.get(ask_amt_col, 0)) and pd.notna(row.get(bid_amt_col, 0)) else 0
                
                # Skip if no meaningful data
                if current_price == 0 and ask_price == 0 and bid_price == 0:
                    continue
                
                # Get material information
                material_name = ticker  # Default to ticker
                category = "Unknown"
                tier = 0
                
                if not materials_df.empty:
                    # Handle NaN ticker values safely
                    ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
                    if ticker_str:
                        material_info = materials_df[materials_df['Ticker'].str.upper() == ticker_str]
                        if not material_info.empty:
                            material_name = material_info.iloc[0].get('Name', ticker)
                            category = material_info.iloc[0].get('Category', 'Unknown')
                            tier = material_info.iloc[0].get('Tier', 0)
                
                # Calculate basic metrics first
                input_cost_per_unit = self.calculate_input_cost(ticker, exchange, recipe_data, market_df)
                profit_per_unit = current_price - input_cost_per_unit
                roi_percentage = (profit_per_unit / current_price * 100) if current_price > 0 else 0
                liquidity_ratio = demand / supply if supply > 0 else 0
                volatility = abs(ask_price - bid_price) / current_price if current_price > 0 else 0
                
                # === ADVANCED: ARBITRAGE ANALYSIS ===
                arbitrage_data = self.calculate_arbitrage_opportunities(ticker, market_df)
                best_buy_exchange = arbitrage_data.get('best_buy_exchange', exchange)
                best_sell_exchange = arbitrage_data.get('best_sell_exchange', exchange)
                max_arbitrage_profit = arbitrage_data.get('max_profit', 0)
                arbitrage_roi = arbitrage_data.get('arbitrage_roi', 0)
                
                # === ADVANCED: BOTTLENECK ANALYSIS ===
                bottleneck_data = self.analyze_bottlenecks(ticker, supply, demand, tier, category, market_df)
                bottleneck_type = bottleneck_data.get('type', 'None')
                bottleneck_severity = bottleneck_data.get('severity', 0)
                market_opportunity = bottleneck_data.get('opportunity_score', 0)
                
                # === ADVANCED: ENHANCED PRODUCE VS BUY ===
                production_analysis = self.enhanced_produce_vs_buy(
                    ticker, input_cost_per_unit, current_price, ask_price, bid_price, 
                    supply, demand, tier, recipe_data
                )
                total_production_cost = production_analysis.get('total_cost', input_cost_per_unit)
                recommendation = production_analysis.get('recommendation', 'Buy')
                confidence = production_analysis.get('confidence', 50)
                break_even_quantity = production_analysis.get('break_even_qty', 0)
                production_time_hours = production_analysis.get('production_time', 0)
                
                # === ADVANCED: ENHANCED INVESTMENT SCORING ===
                investment_score = self.calculate_investment_score(
                    profit_per_unit, roi_percentage, liquidity_ratio, volatility,
                    max_arbitrage_profit, market_opportunity, tier
                )
                
                exchange_data.append({
                    'Material Name': material_name,
                    'ticker': ticker,
                    'category': category,
                    'tier': tier,
                    'Current Price': current_price,
                    'Supply': supply,
                    'Demand': demand,
                    'Input Cost per Unit': input_cost_per_unit,
                    'Profit per Unit': profit_per_unit,
                    'ROI %': roi_percentage,
                    # === ARBITRAGE COLUMNS ===
                    'Best Buy Exchange': best_buy_exchange,
                    'Best Sell Exchange': best_sell_exchange,
                    'Max Arbitrage Profit': max_arbitrage_profit,
                    'Arbitrage ROI %': arbitrage_roi,
                    # === BOTTLENECK COLUMNS ===
                    'Bottleneck Type': bottleneck_type,
                    'Bottleneck Severity': bottleneck_severity,
                    'Market Opportunity': market_opportunity,
                    # === ENHANCED PRODUCE VS BUY COLUMNS ===
                    'Recommendation': recommendation,
                    'Confidence %': confidence,
                    'Break-even Quantity': break_even_quantity,
                    'Production Time (hrs)': production_time_hours,
                    'Total Production Cost': total_production_cost,
                    # === SCORING ===
                    'Investment Score': investment_score,
                    'Risk Level': self.calculate_risk_level(tier, volatility, supply),
                    'Volatility': volatility
                })
            
            return pd.DataFrame(exchange_data)
            
        except Exception as e:
            self.logger.error(f"Error building advanced {exchange} data: {e}")
            return pd.DataFrame()

    def build_optimized_exchange_analysis(self, market_df: pd.DataFrame, materials_df: pd.DataFrame, 
                                          recipe_data: Dict, exchange: str) -> pd.DataFrame:
        """Build optimized analysis data for a specific exchange with unique columns only."""
        try:
            exchange_data = []
            
            for _, row in market_df.iterrows():
                ticker = str(row['Ticker']).strip() if pd.notna(row['Ticker']) else ''
                if not ticker:
                    continue
                
                # Get exchange-specific columns
                avg_col = f"{exchange}-Average"
                ask_price_col = f"{exchange}-AskPrice"
                bid_price_col = f"{exchange}-BidPrice"
                ask_avail_col = f"{exchange}-AskAvail"
                bid_avail_col = f"{exchange}-BidAvail"
                
                # Get values (with fallback to 0)
                current_price = row.get(avg_col, 0) if pd.notna(row.get(avg_col, 0)) else 0
                ask_price = row.get(ask_price_col, 0) if pd.notna(row.get(ask_price_col, 0)) else 0
                bid_price = row.get(bid_price_col, 0) if pd.notna(row.get(bid_price_col, 0)) else 0
                supply = row.get(ask_avail_col, 0) if pd.notna(row.get(ask_avail_col, 0)) else 0
                demand = row.get(bid_avail_col, 0) if pd.notna(row.get(bid_avail_col, 0)) else 0
                
                # Skip if no meaningful data
                if current_price == 0 and ask_price == 0 and bid_price == 0:
                    continue
                
                # Get material information
                material_name = ticker  # Default to ticker
                category = "Unknown"
                tier = 0
                
                if not materials_df.empty:
                    ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
                    if ticker_str:
                        material_info = materials_df[materials_df['Ticker'].str.upper() == ticker_str]
                        if not material_info.empty:
                            material_name = material_info.iloc[0].get('Name', ticker)
                            category = material_info.iloc[0].get('Category', 'Unknown')
                            tier = material_info.iloc[0].get('Tier', 0)
                
                # Calculate basic metrics first
                input_cost_per_unit = self.calculate_input_cost(ticker, exchange, recipe_data, market_df)
                profit_per_unit = current_price - input_cost_per_unit
                roi_percentage = (profit_per_unit / current_price * 100) if current_price > 0 else 0
                volatility = abs(ask_price - bid_price) / current_price if current_price > 0 else 0
                
                # === ENHANCED ARBITRAGE ANALYSIS ===
                arbitrage_data = self.calculate_enhanced_arbitrage_opportunities(ticker, market_df)
                best_buy_exchange = arbitrage_data.get('best_buy_exchange', exchange)
                best_sell_exchange = arbitrage_data.get('best_sell_exchange', exchange)
                max_arbitrage_profit = arbitrage_data.get('max_profit', 0)
                arbitrage_roi = arbitrage_data.get('arbitrage_roi', 0)
                
                # === ENHANCED BOTTLENECK ANALYSIS ===
                bottleneck_data = self.analyze_enhanced_bottlenecks(ticker, supply, demand, tier, category, market_df)
                bottleneck_type = bottleneck_data.get('type', 'Market Stable')
                bottleneck_severity = bottleneck_data.get('severity', 0)
                market_opportunity = bottleneck_data.get('opportunity_score', 0)
                
                # === ENHANCED PRODUCE VS BUY ===
                production_analysis = self.enhanced_produce_vs_buy(
                    ticker, input_cost_per_unit, current_price, ask_price, bid_price, 
                    supply, demand, tier, recipe_data
                )
                total_production_cost = production_analysis.get('total_cost', input_cost_per_unit)
                recommendation = production_analysis.get('recommendation', 'Buy')
                confidence = production_analysis.get('confidence', 75)
                break_even_quantity = production_analysis.get('break_even_qty', 0)
                production_time_hours = production_analysis.get('production_time', 0)
                
                # === ENHANCED INVESTMENT SCORING ===
                investment_score = self.calculate_investment_score(
                    profit_per_unit, roi_percentage, demand/supply if supply > 0 else 0, volatility,
                    max_arbitrage_profit, market_opportunity, tier
                )
                
                # Risk level calculation
                risk_level = self.calculate_risk_level(tier, volatility, supply)
                
                # Create analysis record - ONLY UNIQUE COLUMNS (not in daily_report)
                exchange_data.append({
                    # Basic identification (shared but needed for analysis)
                    'Material Name': material_name,
                    'ticker': ticker,
                    'category': category,
                    'tier': tier,
                    'Current Price': current_price,
                    'Supply': supply,
                    'Demand': demand,
                    'Input Cost per Unit': input_cost_per_unit,
                    'Profit per Unit': profit_per_unit,
                    'ROI %': roi_percentage,
                    
                    # === ARBITRAGE ANALYSIS (UNIQUE TO ANALYSIS) ===
                    'Best Buy Exchange': best_buy_exchange,
                    'Best Sell Exchange': best_sell_exchange,
                    'Max Arbitrage Profit': max_arbitrage_profit,
                    'Arbitrage ROI %': arbitrage_roi,
                    
                    # === BOTTLENECK ANALYSIS (UNIQUE TO ANALYSIS) ===
                    'Bottleneck Type': bottleneck_type,
                    'Bottleneck Severity': bottleneck_severity,
                    'Market Opportunity': market_opportunity,
                    
                    # === ENHANCED DECISION SUPPORT (UNIQUE TO ANALYSIS) ===
                    'Recommendation': recommendation,
                    'Confidence %': confidence,
                    'Break-even Quantity': break_even_quantity,
                    'Production Time (hrs)': production_time_hours,
                    'Total Production Cost': total_production_cost,
                    'Investment Score': investment_score,
                    'Risk Level': risk_level,
                    'Volatility': volatility
                })
            
            return pd.DataFrame(exchange_data)
            
        except Exception as e:
            self.logger.error(f"Error building optimized {exchange} analysis: {e}")
            return pd.DataFrame()

    def apply_analysis_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply data quality filters to remove empty/meaningless entries."""
        try:
            if df.empty:
                return df
            
            initial_count = len(df)
            
            # Filter 1: Remove entries with no price data
            df = df[df['Current Price'] > 0]
            
            # Filter 2: Improve arbitrage data - only show meaningful arbitrage
            # Set arbitrage to 0 if profit is too small or exchanges are the same
            mask_same_exchange = df['Best Buy Exchange'] == df['Best Sell Exchange']
            mask_small_profit = df['Max Arbitrage Profit'] < (df['Current Price'] * 0.05)  # Less than 5%
            
            df.loc[mask_same_exchange | mask_small_profit, 'Max Arbitrage Profit'] = 0
            df.loc[mask_same_exchange | mask_small_profit, 'Arbitrage ROI %'] = 0
            df.loc[mask_same_exchange, 'Best Sell Exchange'] = df.loc[mask_same_exchange, 'Best Buy Exchange']
            
            # Filter 3: Improve bottleneck analysis - only show actual bottlenecks
            low_opportunity = df['Market Opportunity'] < 10
            df.loc[low_opportunity, 'Bottleneck Severity'] = 0
            df.loc[low_opportunity & (df['Bottleneck Type'] != 'Market Stable'), 'Market Opportunity'] = 0
            
            # Filter 4: Set realistic break-even quantities
            # If production cost > current price, break-even should be 0
            unprofitable = df['Total Production Cost'] >= df['Current Price']
            df.loc[unprofitable, 'Break-even Quantity'] = 0
            
            # Filter 5: Ensure confidence levels are reasonable (20-95%)
            df.loc[df['Confidence %'] < 20, 'Confidence %'] = 20
            df.loc[df['Confidence %'] > 95, 'Confidence %'] = 95
            
            # Filter 6: Remove materials with tier 0 that have input costs (shouldn't happen)
            invalid_tier0 = (df['tier'] == 0) & (df['Input Cost per Unit'] > 0)
            df.loc[invalid_tier0, 'Input Cost per Unit'] = 0
            df.loc[invalid_tier0, 'Total Production Cost'] = 0
            
            final_count = len(df)
            self.logger.info(f"Applied analysis filters: {initial_count} -> {final_count} rows")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error applying analysis filters: {e}")
            return df

    def calculate_enhanced_arbitrage_opportunities(self, ticker: str, market_df: pd.DataFrame) -> Dict:
        """Enhanced arbitrage calculation with better filtering."""
        try:
            ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
            if not ticker_str:
                return {'best_buy_exchange': 'N/A', 'best_sell_exchange': 'N/A', 'max_profit': 0, 'arbitrage_roi': 0}
            
            # Get ticker data across all exchanges
            ticker_data = market_df[market_df['Ticker'].str.upper() == ticker_str]
            if ticker_data.empty:
                return {'best_buy_exchange': 'N/A', 'best_sell_exchange': 'N/A', 'max_profit': 0, 'arbitrage_roi': 0}
            
            exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
            exchange_prices = {}
            
            # Collect all exchange prices with better data quality
            for exchange in exchanges:
                ask_col = f"{exchange}-AskPrice"
                bid_col = f"{exchange}-BidPrice"
                avg_col = f"{exchange}-Average"
                supply_col = f"{exchange}-AskAvail"
                demand_col = f"{exchange}-BidAvail"
                
                if ask_col in ticker_data.columns:
                    ask_price = ticker_data.iloc[0].get(ask_col, 0)
                    bid_price = ticker_data.iloc[0].get(bid_col, 0)
                    avg_price = ticker_data.iloc[0].get(avg_col, 0)
                    supply = ticker_data.iloc[0].get(supply_col, 0)
                    demand = ticker_data.iloc[0].get(demand_col, 0)
                    
                    # Only consider exchanges with meaningful market activity
                    min_supply = 5
                    min_demand = 1
                    
                    if (pd.notna(supply) and supply >= min_supply) or (pd.notna(demand) and demand >= min_demand):
                        buy_price = ask_price if pd.notna(ask_price) and ask_price > 0 else avg_price
                        sell_price = bid_price if pd.notna(bid_price) and bid_price > 0 else avg_price
                        
                        if buy_price > 0 or sell_price > 0:
                            exchange_prices[exchange] = {
                                'buy_price': buy_price if buy_price > 0 else None,
                                'sell_price': sell_price if sell_price > 0 else None,
                                'supply': supply if pd.notna(supply) else 0,
                                'demand': demand if pd.notna(demand) else 0
                            }
            
            # Find best arbitrage opportunity with stricter criteria
            best_buy_price = float('inf')
            best_sell_price = 0
            best_buy_exchange = 'N/A'
            best_sell_exchange = 'N/A'
            max_profit = 0
            arbitrage_roi = 0
            
            # Find best buy price (lowest ask/avg price with sufficient supply)
            for exchange, data in exchange_prices.items():
                if data['buy_price'] and data['supply'] >= 5:  # Require minimum supply
                    if data['buy_price'] < best_buy_price:
                        best_buy_price = data['buy_price']
                        best_buy_exchange = exchange
            
            # Find best sell price (highest bid/avg price with sufficient demand)
            for exchange, data in exchange_prices.items():
                if data['sell_price'] and data['demand'] >= 1:  # Require minimum demand
                    if data['sell_price'] > best_sell_price:
                        best_sell_price = data['sell_price']
                        best_sell_exchange = exchange
            
            # Calculate arbitrage with stricter thresholds
            if (best_buy_price != float('inf') and best_sell_price > 0 and 
                best_buy_exchange != best_sell_exchange):
                
                potential_profit = best_sell_price - best_buy_price
                min_profit_threshold = max(best_buy_price * 0.10, 200)  # 10% or 200 credits minimum
                
                if potential_profit >= min_profit_threshold:
                    max_profit = potential_profit
                    arbitrage_roi = (potential_profit / best_buy_price * 100)
                else:
                    # Not profitable enough - use same exchange
                    best_sell_exchange = best_buy_exchange
            
            # If no meaningful arbitrage, ensure consistency
            if max_profit <= 0:
                if best_buy_exchange != 'N/A':
                    best_sell_exchange = best_buy_exchange
                elif best_sell_exchange != 'N/A':
                    best_buy_exchange = best_sell_exchange
            
            return {
                'best_buy_exchange': best_buy_exchange,
                'best_sell_exchange': best_sell_exchange,
                'max_profit': round(max_profit, 2),
                'arbitrage_roi': round(arbitrage_roi, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced arbitrage for {ticker}: {e}")
            return {'best_buy_exchange': 'N/A', 'best_sell_exchange': 'N/A', 'max_profit': 0, 'arbitrage_roi': 0}

    def analyze_enhanced_bottlenecks(self, ticker: str, supply: float, demand: float, tier: int, 
                                    category: str, market_df: pd.DataFrame) -> Dict:
        """Enhanced bottleneck analysis with better classification."""
        try:
            bottleneck_type = 'Market Stable'
            severity = 0
            opportunity_score = 0
            
            # Enhanced supply/demand analysis with better thresholds
            total_supply = max(supply, 0.1)  # Avoid division by zero
            total_demand = max(demand, 0.1)
            demand_supply_ratio = total_demand / total_supply
            
            # More realistic bottleneck detection
            if total_supply <= 5 and total_demand >= 50:
                bottleneck_type = 'Critical Shortage'
                severity = 10
                opportunity_score = 100
            elif total_supply <= 10 and demand_supply_ratio > 10:
                bottleneck_type = 'High Demand'
                severity = min(10, int(demand_supply_ratio * 0.8))
                opportunity_score = min(100, severity * 10)
            elif demand_supply_ratio > 3.0:
                bottleneck_type = 'Supply Shortage'
                severity = min(8, int(demand_supply_ratio * 0.5))
                opportunity_score = severity * 8
            elif total_supply > 1000 and total_demand <= 5:
                bottleneck_type = 'Market Saturated'
                severity = 1
                opportunity_score = 5
            elif tier >= 4 and total_supply <= 50:
                bottleneck_type = 'Production Limited'
                severity = tier + 3
                opportunity_score = tier * 15
            
            # Category-specific adjustments
            high_value_categories = ['electronic systems', 'ship engines', 'medical equipment']
            if category in high_value_categories and opportunity_score > 0:
                opportunity_score = min(100, opportunity_score + 20)
                if severity > 0:
                    severity = min(10, severity + 2)
            
            return {
                'type': bottleneck_type,
                'severity': severity,
                'opportunity_score': round(opportunity_score, 1)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing enhanced bottlenecks for {ticker}: {e}")
            return {'type': 'Market Stable', 'severity': 0, 'opportunity_score': 0}

    def build_exchange_specific_data(self, market_df: pd.DataFrame, materials_df: pd.DataFrame, 
                                    recipe_data: Dict, exchange: str) -> pd.DataFrame:
        """Build data for a specific exchange (legacy method - now calls advanced version)."""
        return self.build_advanced_exchange_data(market_df, materials_df, recipe_data, exchange)

    def calculate_arbitrage_opportunities(self, ticker: str, market_df: pd.DataFrame) -> Dict:
        """Calculate arbitrage opportunities for a specific ticker across all exchanges."""
        try:
            ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
            if not ticker_str:
                return {'best_buy_exchange': 'N/A', 'best_sell_exchange': 'N/A', 'max_profit': 0, 'arbitrage_roi': 0}
            
            # Get ticker data across all exchanges
            ticker_data = market_df[market_df['Ticker'].str.upper() == ticker_str]
            if ticker_data.empty:
                return {'best_buy_exchange': 'N/A', 'best_sell_exchange': 'N/A', 'max_profit': 0, 'arbitrage_roi': 0}
            
            exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
            exchange_prices = {}
            
            # Collect all exchange prices
            for exchange in exchanges:
                ask_col = f"{exchange}-AskPrice"
                bid_col = f"{exchange}-BidPrice"
                avg_col = f"{exchange}-Average"
                supply_col = f"{exchange}-AskAvail"
                
                if ask_col in ticker_data.columns:
                    ask_price = ticker_data.iloc[0].get(ask_col, 0)
                    bid_price = ticker_data.iloc[0].get(bid_col, 0)
                    avg_price = ticker_data.iloc[0].get(avg_col, 0)
                    supply = ticker_data.iloc[0].get(supply_col, 0)
                    
                    # Use the best available price
                    buy_price = ask_price if pd.notna(ask_price) and ask_price > 0 else avg_price
                    sell_price = bid_price if pd.notna(bid_price) and bid_price > 0 else avg_price
                    
                    if buy_price > 0 or sell_price > 0:
                        exchange_prices[exchange] = {
                            'buy_price': buy_price if buy_price > 0 else None,
                            'sell_price': sell_price if sell_price > 0 else None,
                            'supply': supply if pd.notna(supply) else 0
                        }
            
            # Find best arbitrage opportunity
            best_buy_price = float('inf')
            best_sell_price = 0
            best_buy_exchange = 'N/A'
            best_sell_exchange = 'N/A'
            max_profit = 0
            arbitrage_roi = 0
            
            # Find best buy price (lowest ask/avg price with sufficient supply)
            for exchange, data in exchange_prices.items():
                if data['buy_price'] and data['supply'] > 0:
                    if data['buy_price'] < best_buy_price:
                        best_buy_price = data['buy_price']
                        best_buy_exchange = exchange
            
            # Find best sell price (highest bid/avg price)
            for exchange, data in exchange_prices.items():
                if data['sell_price'] and data['sell_price'] > best_sell_price:
                    best_sell_price = data['sell_price']
                    best_sell_exchange = exchange
            
            # Calculate arbitrage if we have both buy and sell opportunities
            if best_buy_price != float('inf') and best_sell_price > 0 and best_buy_exchange != best_sell_exchange:
                potential_profit = best_sell_price - best_buy_price
                
                # Only consider it arbitrage if profit is meaningful (>5% or >100 credits)
                if potential_profit > max(best_buy_price * 0.05, 100):
                    max_profit = potential_profit
                    arbitrage_roi = (potential_profit / best_buy_price * 100)
                else:
                    # Reset to same exchange if profit is too small
                    best_buy_exchange = best_sell_exchange
            
            # If no meaningful arbitrage, use the same exchange
            if max_profit <= 0:
                if best_buy_exchange != 'N/A':
                    best_sell_exchange = best_buy_exchange
                elif best_sell_exchange != 'N/A':
                    best_buy_exchange = best_sell_exchange
            
            return {
                'best_buy_exchange': best_buy_exchange,
                'best_sell_exchange': best_sell_exchange,
                'max_profit': round(max_profit, 2),
                'arbitrage_roi': round(arbitrage_roi, 2)
            }
        except Exception as e:
            self.logger.error(f"Error calculating arbitrage for {ticker}: {e}")
            return {'best_buy_exchange': 'N/A', 'best_sell_exchange': 'N/A', 'max_profit': 0, 'arbitrage_roi': 0}

    def analyze_bottlenecks(self, ticker: str, supply: float, demand: float, tier: int, 
                           category: str, market_df: pd.DataFrame) -> Dict:
        """Analyze bottleneck opportunities for a specific material."""
        try:
            bottleneck_type = 'Market Stable'
            severity = 0
            opportunity_score = 0
            
            # Enhanced supply/demand analysis
            total_supply = supply if supply > 0 else 0.1  # Avoid division by zero
            total_demand = demand if demand > 0 else 0.1
            demand_supply_ratio = total_demand / total_supply
            
            # Critical shortage detection
            if total_supply < 10 and total_demand > 50:
                bottleneck_type = 'Critical Shortage'
                severity = 10
                opportunity_score = 95
            elif demand_supply_ratio > 5.0:
                bottleneck_type = 'High Demand'
                severity = min(10, int(demand_supply_ratio * 1.5))
                opportunity_score = severity * 8
            elif demand_supply_ratio > 2.0:
                bottleneck_type = 'Supply Shortage'
                severity = min(8, int(demand_supply_ratio))
                opportunity_score = severity * 6
            elif total_supply > 1000 and total_demand < 10:
                bottleneck_type = 'Oversupply'
                severity = 2
                opportunity_score = 10  # Low opportunity for oversupply
            elif total_supply > 500 and demand_supply_ratio < 0.1:
                bottleneck_type = 'Market Saturated'
                severity = 1
                opportunity_score = 5
            
            # Production complexity analysis (tier-based)
            if tier >= 4:
                complexity_bonus = tier * 2
                if bottleneck_type in ['Market Stable', 'Market Saturated']:
                    if total_supply < 100:
                        bottleneck_type = 'Production Limited'
                        severity = 3 + tier
                        opportunity_score = tier * 12
                elif bottleneck_type in ['Supply Shortage', 'High Demand', 'Critical Shortage']:
                    severity = min(10, severity + complexity_bonus)
                    opportunity_score = min(100, opportunity_score + complexity_bonus * 5)
            
            # Market concentration analysis (cross-exchange availability)
            ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
            if ticker_str:
                ticker_data = market_df[market_df['Ticker'].str.upper() == ticker_str]
                if not ticker_data.empty:
                    exchanges_with_supply = 0
                    exchanges_with_demand = 0
                    total_market_supply = 0
                    total_market_demand = 0
                    
                    for exchange in ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']:
                        ask_avail_col = f"{exchange}-AskAvail"
                        bid_avail_col = f"{exchange}-BidAvail"
                        
                        if ask_avail_col in ticker_data.columns:
                            supply_val = ticker_data.iloc[0].get(ask_avail_col, 0)
                            demand_val = ticker_data.iloc[0].get(bid_avail_col, 0)
                            
                            if pd.notna(supply_val) and supply_val > 0:
                                exchanges_with_supply += 1
                                total_market_supply += supply_val
                            
                            if pd.notna(demand_val) and demand_val > 0:
                                exchanges_with_demand += 1
                                total_market_demand += demand_val
                    
                    # Market concentration scoring
                    if exchanges_with_supply <= 1 and total_market_supply > 0:
                        if bottleneck_type == 'Market Stable':
                            bottleneck_type = 'Single Exchange'
                            severity = 6
                            opportunity_score = 50
                        else:
                            severity = min(10, severity + 3)
                            opportunity_score = min(100, opportunity_score + 25)
                    elif exchanges_with_supply <= 2 and total_market_supply < 50:
                        if bottleneck_type == 'Market Stable':
                            bottleneck_type = 'Limited Distribution'
                            severity = 4
                            opportunity_score = 35
                        else:
                            severity = min(10, severity + 2)
                            opportunity_score = min(100, opportunity_score + 15)
            
            # Category-specific adjustments
            high_value_categories = ['electronic systems', 'ship engines', 'medical equipment', 'electronic devices']
            essential_categories = ['construction materials', 'agricultural products', 'metals', 'gases']
            
            if category in high_value_categories:
                opportunity_score = min(100, opportunity_score + 10)
            elif category in essential_categories and bottleneck_type in ['Supply Shortage', 'High Demand']:
                opportunity_score = min(100, opportunity_score + 15)
            
            return {
                'type': bottleneck_type,
                'severity': severity,
                'opportunity_score': round(opportunity_score, 1)
            }
        except Exception as e:
            self.logger.error(f"Error analyzing bottlenecks for {ticker}: {e}")
            return {'type': 'Analysis Error', 'severity': 0, 'opportunity_score': 0}

    def enhanced_produce_vs_buy(self, ticker: str, input_cost: float, current_price: float,
                               ask_price: float, bid_price: float, supply: float, demand: float,
                               tier: int, recipe_data: Dict) -> Dict:
        """Enhanced produce vs buy analysis with additional cost factors."""
        try:
            # Get recipe information for more accurate calculations
            ticker_str = str(ticker).upper() if pd.notna(ticker) and str(ticker) != 'nan' else ''
            recipe_info = recipe_data.get(ticker_str, {}) if ticker_str else {}
            
            # Realistic production time based on tier and recipe complexity
            base_production_times = {0: 0.5, 1: 1.0, 2: 2.0, 3: 4.0, 4: 8.0, 5: 16.0}
            production_time_hours = base_production_times.get(tier, tier * 2)
            
            # Add complexity based on number of inputs
            inputs = recipe_info.get('inputs', [])
            if len(inputs) > 5:
                production_time_hours *= 1.5
            elif len(inputs) > 3:
                production_time_hours *= 1.2
            
            # Enhanced cost calculations
            workforce_cost_multiplier = {0: 1.0, 1: 1.05, 2: 1.15, 3: 1.25, 4: 1.4, 5: 1.6}
            infrastructure_cost_multiplier = {0: 1.0, 1: 1.02, 2: 1.08, 3: 1.15, 4: 1.25, 5: 1.35}
            
            tier_workforce = workforce_cost_multiplier.get(tier, 1.0 + tier * 0.1)
            tier_infra = infrastructure_cost_multiplier.get(tier, 1.0 + tier * 0.05)
            
            # Calculate additional costs
            workforce_cost = input_cost * (tier_workforce - 1) if tier > 0 else 0
            infrastructure_cost = input_cost * (tier_infra - 1) if tier > 0 else 0
            
            # Time-based opportunity cost (longer production = higher cost)
            time_opportunity_cost = (production_time_hours / 24) * input_cost * 0.1
            
            total_production_cost = input_cost + workforce_cost + infrastructure_cost + time_opportunity_cost
            
            # Market analysis for recommendation
            market_price = ask_price if ask_price > 0 else current_price
            market_competition = min(supply / 100, 2.0) if supply > 0 else 0
            demand_strength = min(demand / 50, 3.0) if demand > 0 else 0
            
            # Production profitability threshold
            minimum_profit_margin = 0.15 + (tier * 0.05)  # Higher tier needs higher margin
            production_threshold = total_production_cost * (1 + minimum_profit_margin)
            
            # Enhanced recommendation logic
            confidence = 60  # Base confidence
            
            if input_cost == 0:
                # Raw materials - always buy
                recommendation = 'Buy'
                confidence = 95
            elif market_price < total_production_cost * 0.8:
                # Very cheap market price
                recommendation = 'Buy'
                confidence = 90
            elif market_price <= production_threshold:
                # Market price too low for profitable production
                recommendation = 'Buy'
                confidence = 75 + min(15, int(demand_strength * 5))
            else:
                # Production may be profitable
                profit_per_unit = market_price - total_production_cost
                roi = (profit_per_unit / total_production_cost) * 100
                
                if roi > 30:
                    recommendation = 'Produce'
                    confidence = 85
                elif roi > 15:
                    recommendation = 'Produce'
                    confidence = 70
                else:
                    recommendation = 'Buy'
                    confidence = 60
                
                # Adjust confidence based on market conditions
                if demand_strength > 1.5:
                    confidence += 10  # High demand boosts confidence
                if market_competition < 0.5:
                    confidence += 10  # Low competition boosts confidence
                if tier >= 4 and supply < 50:
                    confidence += 5   # Rare high-tier items
            
            # Calculate realistic break-even quantity
            if market_price > total_production_cost:
                profit_per_unit = market_price - total_production_cost
                fixed_setup_cost = 1000 + (tier * 500)  # Setup costs
                break_even_qty = max(1, int(fixed_setup_cost / profit_per_unit))
            else:
                break_even_qty = 0
            
            confidence = min(95, max(20, confidence))
            
            return {
                'total_cost': round(total_production_cost, 2),
                'recommendation': recommendation,
                'confidence': confidence,
                'break_even_qty': break_even_qty,
                'production_time': round(production_time_hours, 1),
                'workforce_cost': round(workforce_cost, 2),
                'infrastructure_cost': round(infrastructure_cost, 2)
            }
        except Exception as e:
            self.logger.error(f"Error in enhanced produce vs buy for {ticker}: {e}")
            return {
                'total_cost': input_cost if input_cost > 0 else 0,
                'recommendation': 'Buy',
                'confidence': 50,
                'break_even_qty': 0,
                'production_time': tier * 2 if tier > 0 else 1,
                'workforce_cost': 0,
                'infrastructure_cost': 0
            }

    def calculate_investment_score(self, profit_per_unit: float, roi_percentage: float,
                                  liquidity_ratio: float, volatility: float, arbitrage_profit: float,
                                  market_opportunity: float, tier: int) -> float:
        """Calculate comprehensive investment score (0-100 scale)."""
        try:
            score = 0
            
            # Profitability component (0-35 points)
            if profit_per_unit > 0:
                # Logarithmic scaling for diminishing returns
                profit_score = min(35, 10 * np.log10(profit_per_unit + 1))
                score += profit_score
            elif profit_per_unit < 0:
                # Penalty for losses
                score -= min(20, abs(profit_per_unit) / 100)
            
            # ROI component (0-25 points)
            if roi_percentage > 0:
                # Cap at 25 points for ROI over 100%
                roi_score = min(25, roi_percentage / 4)
                score += roi_score
            elif roi_percentage < 0:
                score -= min(15, abs(roi_percentage) / 2)
            
            # Market liquidity component (0-15 points)
            if liquidity_ratio > 0:
                # Good liquidity (1.0+) gets full points
                liquidity_score = min(15, liquidity_ratio * 10)
                score += liquidity_score
            
            # Volatility penalty (0 to -10 points)
            if volatility > 0:
                # Higher volatility = higher risk
                volatility_penalty = min(10, volatility * 20)
                score -= volatility_penalty
            
            # Arbitrage opportunity bonus (0-10 points)
            if arbitrage_profit > 0:
                # Meaningful arbitrage opportunities
                arbitrage_score = min(10, arbitrage_profit / 200)
                score += arbitrage_score
            
            # Market opportunity bonus (0-15 points)
            if market_opportunity > 0:
                # Convert opportunity score (0-100) to points (0-15)
                opportunity_score = min(15, market_opportunity / 6.67)
                score += opportunity_score
            
            # Tier complexity factor (-5 to +10 points)
            if tier == 0:
                # Raw materials - stable but low profit
                score += 2
            elif tier == 1:
                # Basic processing - good balance
                score += 5
            elif tier == 2:
                # Moderate complexity - good opportunity
                score += 6
            elif tier == 3:
                # High complexity - higher risk/reward
                score += 4
            elif tier == 4:
                # Very high complexity - specialist market
                score += 2
            elif tier == 5:
                # Extreme complexity - niche market
                score -= 2
            
            # Normalize to 0-100 scale
            final_score = max(0, min(100, score))
            
            return round(final_score, 1)
        except Exception as e:
            self.logger.error(f"Error calculating investment score: {e}")
            return 0.0

    def calculate_risk_level(self, tier: int, volatility: float, supply: float) -> str:
        """Calculate risk level based on various factors."""
        try:
            risk_score = 0
            
            # Tier risk (higher tier = higher risk)
            risk_score += tier * 1.5
            
            # Volatility risk
            risk_score += volatility * 10
            
            # Supply risk (lower supply = higher risk)
            if supply < 10:
                risk_score += 5
            elif supply < 50:
                risk_score += 2
            
            if risk_score <= 3:
                return 'Low'
            elif risk_score <= 7:
                return 'Medium'
            elif risk_score <= 12:
                return 'High'
            else:
                return 'Very High'
        except Exception as e:
            self.logger.error(f"Error calculating risk level: {e}")
            return 'Unknown'

    def load_materials_data(self) -> pd.DataFrame:
        """Load materials data from cache."""
        try:
            materials_path = os.path.join(self.cache_dir, "materials.csv")
            if os.path.exists(materials_path):
                return pd.read_csv(materials_path)
            else:
                self.logger.warning("Materials data not found")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading materials data: {e}")
            return pd.DataFrame()
    
    def load_recipe_data(self) -> Dict:
        """Load recipe data from cache."""
        try:
            recipe_outputs_path = os.path.join(self.cache_dir, "recipe_outputs.csv")
            recipe_inputs_path = os.path.join(self.cache_dir, "recipe_inputs.csv")
            
            recipe_data = {}
            
            if os.path.exists(recipe_outputs_path):
                outputs_df = pd.read_csv(recipe_outputs_path)
                # Group by material to get recipe info
                for _, row in outputs_df.iterrows():
                    material = row['Material']
                    if material not in recipe_data:
                        recipe_data[material] = {
                            'recipe_key': row['Key'],
                            'amount_per_recipe': row['Amount'],
                            'inputs': []
                        }
            
            # Load input requirements
            if os.path.exists(recipe_inputs_path):
                inputs_df = pd.read_csv(recipe_inputs_path)
                # Group inputs by recipe key
                for _, row in inputs_df.iterrows():
                    recipe_key = row['Key']
                    input_material = row['Material']
                    input_amount = row['Amount']
                    
                    # Find the output material for this recipe key
                    for material, data in recipe_data.items():
                        if data['recipe_key'] == recipe_key:
                            recipe_data[material]['inputs'].append({
                                'material': input_material,
                                'amount': input_amount
                            })
                            break
            
            return recipe_data
        except Exception as e:
            self.logger.error(f"Error loading recipe data: {e}")
            return {}
    
    def add_recipe_info(self, df: pd.DataFrame, recipe_data: Dict) -> pd.DataFrame:
        """Add recipe information to the dataframe."""
        try:
            # Safe function to handle NaN ticker values
            def get_recipe_info(ticker, key, default):
                if pd.notna(ticker) and str(ticker) != 'nan':
                    ticker_upper = str(ticker).upper()
                    return recipe_data.get(ticker_upper, {}).get(key, default)
                return default
            
            df['Recipe'] = df['ticker'].map(lambda x: get_recipe_info(x, 'recipe_key', 'N/A'))
            df['Amount per Recipe'] = df['ticker'].map(lambda x: get_recipe_info(x, 'amount_per_recipe', 1))
            return df
        except Exception as e:
            self.logger.error(f"Error adding recipe info: {e}")
            df['Recipe'] = 'N/A'
            df['Amount per Recipe'] = 1
            return df
    
    def calculate_advanced_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate advanced metrics like market cap, liquidity ratio, etc."""
        try:
            # Current Price (use average of ask/bid or first available price)
            price_columns = ['ai1_price', 'ci1_price', 'ci2_price', 'nc1_price', 'nc2_price', 'ic1_price']
            available_price_cols = [col for col in price_columns if col in df.columns]
            
            if available_price_cols:
                df['Current Price'] = df[available_price_cols].mean(axis=1, skipna=True)
            else:
                df['Current Price'] = 0
            
            # Input Cost per Stack (using recipe amount as stack size)
            # Use Amount per Recipe as Stack Size if available, otherwise default to 1
            df['Stack Size'] = df.get('Amount per Recipe', 1)
            df['Input Cost per Stack'] = df.get('input_cost', 0) * df['Stack Size']
            
            # Profit per Stack
            df['Profit per Stack'] = df.get('profit_margin', 0) * df['Stack Size']
            
            # Market Cap (Current Price * Total Supply across all exchanges)
            supply_columns = ['ai1_supply', 'ci1_supply', 'ci2_supply', 'nc1_supply', 'nc2_supply', 'ic1_supply']
            available_supply_cols = [col for col in supply_columns if col in df.columns]
            
            if available_supply_cols:
                df['Total Supply'] = df[available_supply_cols].sum(axis=1, skipna=True)
                df['Market Cap'] = df['Current Price'] * df['Total Supply']
            else:
                df['Market Cap'] = 0
            
            # Liquidity Ratio (simplified as demand/supply ratio)
            demand_columns = ['ai1_demand', 'ci1_demand', 'ci2_demand', 'nc1_demand', 'nc2_demand', 'ic1_demand']
            available_demand_cols = [col for col in demand_columns if col in df.columns]
            
            if available_demand_cols and available_supply_cols:
                total_demand = df[available_demand_cols].sum(axis=1, skipna=True)
                total_supply = df[available_supply_cols].sum(axis=1, skipna=True)
                df['Liquidity Ratio'] = np.where(total_supply > 0, total_demand / total_supply, 0)
            else:
                df['Liquidity Ratio'] = 0
            
            # Volatility (simplified calculation based on price spread)
            ask_columns = ['ai1_ask_price', 'ci1_ask_price', 'ci2_ask_price', 'nc1_ask_price', 'nc2_ask_price', 'ic1_ask_price']
            bid_columns = ['ai1_bid_price', 'ci1_bid_price', 'ci2_bid_price', 'nc1_bid_price', 'nc2_bid_price', 'ic1_bid_price']
            
            available_ask_cols = [col for col in ask_columns if col in df.columns]
            available_bid_cols = [col for col in bid_columns if col in df.columns]
            
            if available_ask_cols and available_bid_cols:
                avg_ask = df[available_ask_cols].mean(axis=1, skipna=True)
                avg_bid = df[available_bid_cols].mean(axis=1, skipna=True)
                df['Volatility'] = np.where(avg_bid > 0, (avg_ask - avg_bid) / avg_bid, 0)
            else:
                df['Volatility'] = 0
            
            return df
        except Exception as e:
            self.logger.error(f"Error calculating advanced metrics: {e}")
            return df
    
    def create_final_report_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create the final report with proper column names and structure."""
        try:
            # Define the mapping from internal columns to display headers
            column_mapping = {
                'Name': 'Material Name',
                'ticker': 'Ticker', 
                'Recipe': 'Recipe',
                'Amount per Recipe': 'Amount per Recipe',
                'category': 'Category',
                'tier': 'Tier',
                'Weight': 'Weight',
                'Volume': 'Volume',
                'Current Price': 'Current Price',
                'input_cost': 'Input Cost per Unit',
                'Input Cost per Stack': 'Input Cost per Stack',
                'profit_margin': 'Profit per Unit',
                'Profit per Stack': 'Profit per Stack',
                'roi_percentage': 'ROI %',
                'ai1_supply': 'Supply',
                'ai1_demand': 'Demand',
                'Market Cap': 'Market Cap',
                'Liquidity Ratio': 'Liquidity Ratio',
                'investment_score': 'Investment Score',
                'risk_level': 'Risk Level',
                'Volatility': 'Volatility'
            }
            
            # Create final report with only available columns
            final_df = pd.DataFrame()
            
            for internal_col, display_col in column_mapping.items():
                if internal_col in df.columns:
                    final_df[display_col] = df[internal_col]
                else:
                    # Provide default values for missing columns
                    if display_col in ['Material Name', 'Recipe', 'Risk Level']:
                        final_df[display_col] = 'N/A'
                    else:
                        final_df[display_col] = 0
            
            # Ensure we have at least the core columns
            required_headers = [
                'Material Name', 'Ticker', 'Recipe', 'Amount per Recipe', 
                'Category', 'Tier', 'Weight', 'Volume', 'Current Price',
                'Input Cost per Unit', 'Input Cost per Stack', 
                'Profit per Unit', 'Profit per Stack', 'ROI %',
                'Supply', 'Demand', 'Market Cap', 'Liquidity Ratio',
                'Investment Score', 'Risk Level', 'Volatility'
            ]
            
            for header in required_headers:
                if header not in final_df.columns:
                    if header in ['Material Name', 'Recipe', 'Risk Level']:
                        final_df[header] = 'N/A'
                    else:
                        final_df[header] = 0
            
            # Reorder columns to match expected header order
            final_df = final_df[required_headers]
            
            # Clean up data types and fill missing values
            numeric_columns = [col for col in required_headers if col not in ['Material Name', 'Ticker', 'Recipe', 'Category', 'Risk Level']]
            for col in numeric_columns:
                final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0)
            
            return final_df
            
        except Exception as e:
            self.logger.error(f"Error creating final report structure: {e}")
            return df
            self.logger.error(f"Error building daily report: {e}")
            return pd.DataFrame()
    
    def get_top_opportunities(self, exchange: str, metric: str = 'ROI (Ask)', limit: int = 20) -> pd.DataFrame:
        """Get top opportunities for a specific exchange and metric."""
        try:
            report_df = self.generate_comprehensive_report(exchange)
            
            if report_df.empty:
                return pd.DataFrame()
            
            # Filter out items with zero or negative values for the metric
            filtered_df = report_df[report_df[metric] > 0]
            
            # Sort and limit
            top_df = filtered_df.nlargest(limit, metric)
            
            self.logger.info(f"Found {len(top_df)} top opportunities for {exchange} by {metric}")
            return top_df
            
        except Exception as e:
            self.logger.error(f"Error getting top opportunities for {exchange}: {e}")
            return pd.DataFrame()