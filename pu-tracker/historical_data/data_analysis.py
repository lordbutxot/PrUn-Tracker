import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import logging
from datetime import datetime, timezone, timedelta
from historical_data.config import CACHE_DIR, REFRESH_INTERVAL_HOURS, CREDENTIALS_FILE, TARGET_SPREADSHEET_ID

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def authenticate_sheets():
    """Authenticate with Google Sheets API."""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def is_cache_fresh(file):
    """Check if cache file is fresh."""
    if not os.path.exists(file):
        return False
    cache_time = datetime.fromtimestamp(os.path.getmtime(file), tz=timezone.utc)
    return (datetime.now(timezone.utc) - cache_time) < timedelta(hours=REFRESH_INTERVAL_HOURS)

def load_data_sheets(spreadsheet):
    """Load data from Google Sheets."""
    cache_file = os.path.join(CACHE_DIR, 'data_sheets_cache.json')
    if is_cache_fresh(cache_file):
        with open(cache_file, 'r') as f:
            logger.info(f"Loaded data sheets from cache: {cache_file}")
            return pd.DataFrame(json.load(f))
    
    worksheets = [ws for ws in spreadsheet.worksheets() if ws.title.startswith('DATA ')]
    all_data = []
    for ws in worksheets:
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # Extract ticker from worksheet title (e.g., "DATA AI1" -> "AI1")
            ticker = ws.title.replace('DATA ', '')
            df['Ticker'] = ticker
            # Add Exchange column based on ticker mapping
            # Map exchange tickers back to full names for consistency
            exchange_mapping = {
                'AI1': 'Antares I',
                'IC1': 'Interstellar Coalition I', 
                'NC1': 'New Ceres I',
                'IC2': 'New Ceres II',  # Note: This might be 'Interstellar Coalition II'
                'CI1': 'Ceres I',
                'CI2': 'Ceres II'
            }
            df['Exchange'] = exchange_mapping.get(ticker, ticker)
            all_data.append(df)
    
    all_df = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    if not all_df.empty:
        all_df.to_json(cache_file, orient='records')
        logger.info(f"Saved data sheets to cache: {cache_file}")
    return all_df

def calculate_arbitrage_opportunities(df):
    """Calculate arbitrage opportunities."""
    arbitrage_data = []
    for ticker in df['Ticker'].unique():
        ticker_data = df[df['Ticker'] == ticker]
        for _, row1 in ticker_data.iterrows():
            for _, row2 in ticker_data.iterrows():
                if (row1['Exchange'] != row2['Exchange'] and 
                    pd.notna(row1['Ask Price']) and pd.notna(row2['Bid Price']) and
                    row1['Ask Price'] < row2['Bid Price']):
                    profit = row2['Bid Price'] - row1['Ask Price']
                    arbitrage_data.append({
                        'Ticker': ticker,
                        'Buy_Exchange': row1['Exchange'],
                        'Sell_Exchange': row2['Exchange'],
                        'Profit': profit,
                        'Profit_Pct': (profit / row1['Ask Price'] * 100) if row1['Ask Price'] > 0 else 0
                    })
    return pd.DataFrame(arbitrage_data)

def calculate_input_cost(ticker, chains, price_data):
    """Calculate input cost for a product."""
    if ticker not in chains:
        return 0
    inputs = chains[ticker].get('inputs', {})
    total_cost = 0
    for input_ticker, quantity in inputs.items():
        # Filter rows for the input ticker
        input_prices = price_data[(price_data['Ticker'] == input_ticker) & pd.notna(price_data['Ask Price'])]['Ask Price']
        if not input_prices.empty:
            total_cost += input_prices.min() * quantity
    return total_cost

def calculate_buy_vs_produce(df, chains, tiers):
    """Calculate buy vs produce decisions."""
    decisions = []
    for _, row in df.iterrows():
        ticker = row['Ticker']
        ask_price = row.get('Ask Price')
        if pd.isna(ask_price):
            continue
        input_cost = calculate_input_cost(ticker, chains, df)
        tier = tiers.get(ticker, 0)
        risk = 7.5 if tier == 0 else 5.0
        if input_cost > 0:
            viability = 2.5 if ask_price > input_cost else 5.0
            recommendation = 'Buy' if ask_price <= input_cost * 1.1 else 'Produce'
            cost_ratio = ask_price / input_cost
        else:
            viability = 5.0
            recommendation = 'Buy'
            cost_ratio = 1.0
        decisions.append({
            'Ticker': ticker,
            'Exchange': row['Exchange'],
            'Input_Cost': input_cost,
            'Ask_Price': ask_price,
            'Cost_Ratio': cost_ratio,
            'Recommendation': recommendation,
            'Risk': risk,
            'Viability': viability
        })
    return pd.DataFrame(decisions)

def analyze_data(data_sheets, processed_data, chains, tiers, tickers):
    """Analyze data for insights."""
    if processed_data.empty:
        logger.warning("No processed data")
        return {}, {}, []
    
    df = processed_data.copy()
    
    # Only merge if data_sheets is not empty and has the required columns
    if not data_sheets.empty:
        # Check if both DataFrames have the required columns for merging
        merge_columns = []
        if 'Ticker' in data_sheets.columns and 'Ticker' in df.columns:
            merge_columns.append('Ticker')
        if 'Exchange' in data_sheets.columns and 'Exchange' in df.columns:
            merge_columns.append('Exchange')
        
        if merge_columns:
            logger.info(f"Merging on columns: {merge_columns}")
            df = df.merge(data_sheets, on=merge_columns, how='left', suffixes=('', '_sheet'))
        else:
            logger.warning("No common columns found for merging data_sheets and processed_data")

    analysis_results = {}
    trends = {}
    recommendations = []
    
    for ticker in df['Ticker'].unique():
        ticker_data = df[df['Ticker'] == ticker]
        avg_spread = ticker_data['spread_pct'].mean() if 'spread_pct' in ticker_data.columns else np.nan
        trends[ticker] = {'avg_spread': avg_spread}
        if pd.notna(avg_spread) and avg_spread > 5:
            recommendations.append({'Ticker': ticker, 'Recommendation': f'Buy on {ticker_data["Exchange"].iloc[0]}'})

    for exchange in df['Exchange'].unique():
        exchange_df = df[df['Exchange'] == exchange].copy()
        arbitrage_df = calculate_arbitrage_opportunities(df)
        if not arbitrage_df.empty:
            buy_opportunities = arbitrage_df[arbitrage_df['Buy_Exchange'] == exchange]
            exchange_df = exchange_df.merge(
                buy_opportunities[['Ticker', 'Profit', 'Profit_Pct']].groupby('Ticker').max().reset_index(),
                on='Ticker', how='left'
            )
        
        exchange_df['Profit'] = exchange_df.get('Profit', 0)
        exchange_df['Profit_Pct'] = exchange_df.get('Profit_Pct', 0)
        
        decisions_df = calculate_buy_vs_produce(exchange_df, chains, tiers)
        if not decisions_df.empty:
            exchange_df = exchange_df.merge(
                decisions_df[['Ticker', 'Input_Cost', 'Cost_Ratio', 'Recommendation', 'Risk', 'Viability']],
                on='Ticker', how='left'
            )
        
        exchange_df['ROI (Ask)'] = exchange_df.apply(
            lambda row: (row['Profit'] / row['Ask Price'] * 100) if pd.notna(row['Ask Price']) and row['Ask Price'] > 0 else 0, axis=1
        )
        exchange_df['Investment Score'] = exchange_df['Profit'].rank(method='dense')
        exchange_df['Product'] = exchange_df['Ticker'].map(tickers).fillna(exchange_df['Ticker'])
        exchange_df['Material'] = exchange_df['Ticker']
        exchange_df['Tier'] = exchange_df['Ticker'].map(tiers).fillna(0)
        
        for col in ['Profit', 'Profit_Pct', 'ROI (Ask)', 'Investment Score', 'Risk', 'Viability']:
            exchange_df[col] = exchange_df.get(col, 0)
        
        analysis_results[exchange] = exchange_df
        logger.info(f"Analyzed {exchange}: {len(exchange_df)} rows")

    return analysis_results, trends, recommendations