import pandas as pd
import numpy as np
import logging
from historical_data.config import VALID_EXCHANGES

logger = logging.getLogger(__name__)

def calculate_input_cost(ticker, chains, prices_df, exchange, depth=0, max_depth=5):
    """Calculate the input cost for a ticker based on production chains."""
    if depth > max_depth:
        logger.warning(f"Max recursion depth reached for ticker {ticker} on {exchange}")
        return 0.0
    
    chain = chains.get(ticker.lower())
    if not chain or not chain.get('inputs'):
        logger.warning(f"No production chain defined for ticker {ticker} on {exchange}, assuming 0 cost")
        return 0.0
    
    total_cost = 0.0
    try:
        for input_ticker, amount in chain['inputs'].items():
            input_prices = prices_df[
                (prices_df['Ticker'] == input_ticker) & (prices_df['Exchange'] == exchange)
            ]
            if input_prices.empty:
                logger.warning(f"No price data for input {input_ticker} on {exchange}, assuming 0 cost")
                continue
            input_cost = input_prices['Ask_Price'].iloc[0] if not input_prices['Ask_Price'].isna().all() else 0.0
            total_cost += input_cost * amount
    except Exception as e:
        logger.error(f"Error calculating input cost for {ticker} on {exchange}: {e}")
        return 0.0
    
    return total_cost

def transform_prices_df(prices_df, exchanges):
    """Transform prices DataFrame for analysis."""
    try:
        logger.info(f"Transforming {len(prices_df['Ticker'].unique())} tickers across exchanges: {exchanges}")
        processed_df = prices_df.copy()
        
        required_columns = ['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price', 'Ask_Avail', 'Bid_Avail', 'Traded', 'Saturation']
        for col in required_columns:
            if col not in processed_df.columns:
                logger.warning(f"Column {col} missing, filling with 0")
                processed_df[col] = 0.0 if col in ['Ask_Price', 'Bid_Price', 'Saturation'] else 0
        
        processed_df['Ask_Price'] = pd.to_numeric(processed_df['Ask_Price'], errors='coerce').fillna(0.0)
        processed_df['Bid_Price'] = pd.to_numeric(processed_df['Bid_Price'], errors='coerce').fillna(0.0)
        processed_df['Ask_Avail'] = pd.to_numeric(processed_df['Ask_Avail'], errors='coerce').fillna(0)
        processed_df['Bid_Avail'] = pd.to_numeric(processed_df['Bid_Avail'], errors='coerce').fillna(0)
        processed_df['Traded'] = pd.to_numeric(processed_df['Traded'], errors='coerce').fillna(0)
        processed_df['Saturation'] = pd.to_numeric(processed_df.get('Saturation', pd.Series(0.0, index=processed_df.index)), errors='coerce').fillna(0.0)
        
        processed_df['Price_Spread'] = processed_df['Ask_Price'] - processed_df['Bid_Price']
        
        logger.info(f"Transformed {len(processed_df)} rows")
        return processed_df
    except Exception as e:
        logger.error(f"Error transforming prices DataFrame: {e}")
        return pd.DataFrame()

def process_data(prices_df, building_dict, categories, tickers, product_tiers, chains):
    """Process price data with additional calculations."""
    try:
        if prices_df.empty:
            logger.warning("Empty prices_df provided, returning empty DataFrame")
            return pd.DataFrame()
        
        processed_df = transform_prices_df(prices_df, VALID_EXCHANGES)
        if processed_df.empty:
            logger.warning("Transformed DataFrame is empty")
            return processed_df
        
        processed_df['Category'] = processed_df['Ticker'].str.lower().map(categories).fillna('unknown')
        processed_df['Product'] = processed_df['Ticker'].map(tickers).fillna(processed_df['Ticker'])
        processed_df['Tier'] = processed_df['Ticker'].str.lower().map(product_tiers).fillna(0)
        
        logger.info("Calculating input costs...")
        processed_df['Input_Cost'] = 0.0
        for exchange in VALID_EXCHANGES:
            mask = processed_df['Exchange'] == exchange
            processed_df.loc[mask, 'Input_Cost'] = processed_df[mask].apply(
                lambda row: calculate_input_cost(row['Ticker'], chains, prices_df, exchange), axis=1
            )
        
        processed_df['Profit_Ask'] = processed_df['Ask_Price'] - processed_df['Input_Cost']
        processed_df['Profit_Bid'] = processed_df['Bid_Price'] - processed_df['Input_Cost']
        processed_df['ROI_Ask'] = (processed_df['Profit_Ask'] / processed_df['Input_Cost'].replace(0, 1)) * 100
        processed_df['ROI_Bid'] = (processed_df['Profit_Bid'] / processed_df['Input_Cost'].replace(0, 1)) * 100
        
        processed_df['Risk'] = 7.5
        processed_df['Viability'] = 2.5
        processed_df['Investment_Score'] = 2.5
        
        logger.info(f"Processed {len(processed_df)} rows with columns: {list(processed_df.columns)}")
        return processed_df
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return pd.DataFrame()