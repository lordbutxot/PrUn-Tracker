import os
import sys
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional

class DataProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def standardize_columns(self, df):
        """Standardize column names to expected format"""
        column_mapping = {
            'Ask Price': 'Ask_Price',
            'Bid Price': 'Bid_Price',
            'MaterialTicker': 'Ticker',
            'ExchangeCode': 'Exchange',
            'CXDataPointType': 'Type'
        }
        
        # Apply mapping
        df = df.rename(columns=column_mapping)
        self.logger.info(f"Standardized columns: {list(df.columns)}")
        return df
    
    def expand_exchange_data(self, market_df):
        """Expand market data to include all exchanges with proper column mapping"""
        try:
            self.logger.info("Expanding exchange data...")
            
            exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
            expanded_rows = []
            
            # Get ticker column
            ticker_col = 'Ticker' if 'Ticker' in market_df.columns else market_df.columns[0]
            
            for _, row in market_df.iterrows():
                ticker = row[ticker_col]
                
                # Fix: Handle NaN and non-string tickers
                if pd.isna(ticker) or ticker == '':
                    continue
                
                # Convert to string and handle any data type
                ticker = str(ticker).strip()
                if not ticker:
                    continue
                
                for exchange in exchanges:
                    # Map the actual column names from your data
                    price_col = f'{exchange}-Average'
                    supply_col = f'{exchange}-AskAvail'  # Supply = Ask Available
                    demand_col = f'{exchange}-BidAvail'  # Demand = Bid Available
                    ask_price_col = f'{exchange}-AskPrice'
                    bid_price_col = f'{exchange}-BidPrice'
                    
                    # Check if this exchange has data for this ticker
                    if price_col in market_df.columns and not pd.isna(row.get(price_col)):
                        price_value = row.get(price_col, 0)
                        if price_value and price_value > 0:  # Only include if there's actual price data
                            new_row = {
                                'ticker': ticker.lower(),  # Ensure lowercase for consistency
                                'exchange': exchange,
                                f'{exchange.lower()}_price': float(price_value) if price_value else 0.0,
                                f'{exchange.lower()}_supply': float(row.get(supply_col, 0)) if row.get(supply_col) else 0.0,
                                f'{exchange.lower()}_demand': float(row.get(demand_col, 0)) if row.get(demand_col) else 0.0,
                                f'{exchange.lower()}_ask_price': float(row.get(ask_price_col, 0)) if row.get(ask_price_col) else 0.0,
                                f'{exchange.lower()}_bid_price': float(row.get(bid_price_col, 0)) if row.get(bid_price_col) else 0.0,
                            }
                            expanded_rows.append(new_row)
            
            if expanded_rows:
                expanded_df = pd.DataFrame(expanded_rows)
                self.logger.info(f"Expanded to {len(expanded_df)} exchange-specific rows")
                return expanded_df
            else:
                self.logger.warning("No exchange-specific data found")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error expanding exchange data: {e}", exc_info=True)
            return pd.DataFrame()
    
    def calculate_input_costs(self, df, chains):
        """Calculate input costs for manufactured items"""
        try:
            self.logger.info("Calculating input costs...")
            
            # Add input_cost column
            df['input_cost'] = 0.0
            
            for idx, row in df.iterrows():
                try:
                    ticker = row['ticker'].upper()
                    exchange = row['exchange']
                    
                    if ticker in chains:
                        chain = chains[ticker]
                        inputs = chain.get('inputs', {})
                        
                        if inputs:
                            total_cost = 0
                            for input_ticker, quantity in inputs.items():
                                input_price = self.get_material_price(df, input_ticker, exchange)
                                total_cost += input_price * quantity
                            
                            df.at[idx, 'input_cost'] = total_cost
                
                except Exception as e:
                    self.logger.debug(f"Error calculating input cost for {ticker}: {e}")
                    continue
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error in calculate_input_costs: {e}")
            return df
    
    def get_material_price(self, df, ticker, exchange):
        """Get material price for specific exchange"""
        try:
            price_col = f'{exchange.lower()}_price'
            mask = (df['ticker'] == ticker.lower()) & (df['exchange'] == exchange)
            matches = df[mask]
            
            if not matches.empty and price_col in df.columns:
                price = matches.iloc[0].get(price_col, 0)
                return float(price) if price and not pd.isna(price) else 0.0
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def calculate_advanced_scores(self, df):
        """Calculate investment scores and risk metrics"""
        try:
            self.logger.info("Calculating advanced scores...")
            
            # Add scoring columns
            df['profit_margin'] = 0.0
            df['roi_percentage'] = 0.0
            df['investment_score'] = 0.0
            df['risk_level'] = 'Unknown'
            df['liquidity_score'] = 0.0
            
            for idx, row in df.iterrows():
                try:
                    exchange = row['exchange']
                    price_col = f'{exchange.lower()}_price'
                    supply_col = f'{exchange.lower()}_supply'
                    demand_col = f'{exchange.lower()}_demand'
                    
                    current_price = float(row.get(price_col, 0)) if not pd.isna(row.get(price_col, 0)) else 0
                    input_cost = float(row.get('input_cost', 0)) if not pd.isna(row.get('input_cost', 0)) else 0
                    supply = float(row.get(supply_col, 0)) if not pd.isna(row.get(supply_col, 0)) else 0
                    demand = float(row.get(demand_col, 0)) if not pd.isna(row.get(demand_col, 0)) else 0
                    
                    # Calculate profit and ROI
                    if current_price > 0 and input_cost > 0:
                        profit = current_price - input_cost
                        roi = (profit / input_cost) * 100
                        
                        df.at[idx, 'profit_margin'] = profit
                        df.at[idx, 'roi_percentage'] = roi
                        
                        # Calculate investment score (1-10)
                        score = min(10, max(1, (roi / 10) + (profit / 100)))
                        df.at[idx, 'investment_score'] = score
                        
                        # Risk assessment
                        if roi > 50:
                            risk = 'High Reward'
                        elif roi > 20:
                            risk = 'Medium'
                        elif roi > 0:
                            risk = 'Low'
                        else:
                            risk = 'Loss'
                        
                        df.at[idx, 'risk_level'] = risk
                    
                    # Liquidity score
                    if supply > 0 and demand > 0:
                        liquidity = min(10, (demand / supply) * 5)
                        df.at[idx, 'liquidity_score'] = liquidity
                
                except Exception:
                    continue
            
            self.logger.info("Advanced scores calculated successfully")
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating advanced scores: {e}")
            return df
    
    def add_material_categories(self, df, materials):
        """Add material category and tier information"""
        try:
            # Add category columns
            df['category'] = ''
            df['tier'] = ''
            
            # Create ticker to category mapping
            if hasattr(materials, 'iterrows'):
                for _, mat_row in materials.iterrows():
                    ticker = mat_row.get('Ticker', '')
                    # Fix the float issue - ensure ticker is a string
                    if pd.notna(ticker) and ticker != '':
                        ticker = str(ticker).upper()
                        category = str(mat_row.get('Category', ''))  # Fixed: was 'CategoryName'
                        tier = str(mat_row.get('Tier', ''))
                        
                        # Update matching rows
                        mask = df['ticker'] == ticker.lower()
                        df.loc[mask, 'category'] = category
                        df.loc[mask, 'tier'] = tier
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error adding material categories: {e}")
            return df
    
    def process_data(self, market_data, materials, chains, buildings=None):
        """Main data processing method"""
        try:
            self.logger.info("Starting data processing...")
            
            # Standardize columns
            market_data = self.standardize_columns(market_data)
            
            # Expand exchange data
            processed_df = self.expand_exchange_data(market_data)
            
            if processed_df.empty:
                self.logger.error("No data after expansion")
                return pd.DataFrame()
            
            # Add material categories
            processed_df = self.add_material_categories(processed_df, materials)
            
            # Calculate costs and scores
            processed_df = self.calculate_input_costs(processed_df, chains)
            processed_df = self.calculate_advanced_scores(processed_df)
            
            self.logger.info(f"Data processing completed: {len(processed_df)} rows")
            return processed_df
            
        except Exception as e:
            self.logger.error(f"Error in process_data: {e}")
            return pd.DataFrame()

# Standalone function for backwards compatibility
def process_data(prices_df, materials, chains, buildings=None):
    """
    Standalone function to process data using DataProcessor class.
    """
    processor = DataProcessor()
    return processor.process_data(prices_df, materials, chains, buildings)

