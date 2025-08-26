import pandas as pd
import numpy as np
import json
import os
import logging
import requests
from datetime import datetime, timezone, timedelta
from historical_data.config import CACHE_DIR, REFRESH_INTERVAL_HOURS, TARGET_SPREADSHEET_ID
from historical_data.sheets_api import authenticate_sheets
from historical_data.config import TIER_0_RESOURCES, VALID_EXCHANGES
from io import StringIO
from .rate_limiter import rate_limited_api_call, safe_api_request



logger = logging.getLogger(__name__)

# Expected headers to match data_processor.py output
EXPECTED_HEADERS = [
    'BuyingOrders', 'SellingOrders', 'CXDataModelId', 'MaterialName', 'Ticker',
    'MaterialId', 'ExchangeName', 'ExchangeCode', 'Currency', 'Previous', 'Price',
    'PriceTimeEpochMs', 'High', 'AllTimeHigh', 'Low', 'AllTimeLow', 'Ask_Price',
    'Ask_Avail', 'Bid_Price', 'Bid_Avail', 'Supply', 'Demand', 'Traded',
    'VolumeAmount', 'PriceAverage', 'NarrowPriceBandLow', 'NarrowPriceBandHigh',
    'WidePriceBandLow', 'WidePriceBandHigh', 'MMBuy', 'MMSell', 'UserNameSubmitted',
    'Timestamp', 'Exchange', 'Price_Spread', 'Saturation', 'Category', 'Product',
    'Tier', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid',
    'Risk', 'Viability', 'Investment_Score'
]

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
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Loaded data sheets from cache: {cache_file}")
                return pd.DataFrame(json.load(f))
        except Exception as e:
            logger.error(f"Error loading cache {cache_file}: {e}")
    
    try:
        worksheets = [ws for ws in spreadsheet.worksheets() if ws.title.startswith('DATA ')]
        all_data = []
        for ws in worksheets:
            try:
                logger.info(f"Loading worksheet {ws.title} with headers: {EXPECTED_HEADERS}")
                data = ws.get_all_records(expected_headers=EXPECTED_HEADERS)
                if data:
                    df = pd.DataFrame(data)
                    ticker = ws.title.replace('DATA ', '')
                    df['Ticker'] = ticker
                    exchange_mapping = {
                        'AI1': 'Antares I',
                        'IC1': 'Interstellar Coalition I',
                        'NC1': 'New Ceres I',
                        'NC2': 'New Ceres II',
                        'CI1': 'Ceres I',
                        'CI2': 'Ceres II'
                    }
                    df['Exchange'] = exchange_mapping.get(ticker, ticker)
                    all_data.append(df)
                    logger.info(f"Loaded {len(df)} rows from {ws.title}")
                else:
                    logger.warning(f"No data in worksheet {ws.title}")
            except Exception as e:
                logger.error(f"Error loading {ws.title}: {e}")
                df = pd.DataFrame(columns=EXPECTED_HEADERS)
                df['Ticker'] = ticker
                df['Exchange'] = exchange_mapping.get(ticker, ticker)
                all_data.append(df)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            os.makedirs(CACHE_DIR, exist_ok=True)
            combined_df.to_json(cache_file, orient='records', indent=2)
            logger.info(f"Saved data sheets to cache: {cache_file}")
            return combined_df
        else:
            logger.warning("No data loaded from sheets, using fallback")
            return pd.DataFrame(columns=EXPECTED_HEADERS)
    except Exception as e:
        logger.error(f"Error loading sheets: {e}")
        return pd.DataFrame(columns=EXPECTED_HEADERS)

def calculate_arbitrage_opportunities(df):
    """Placeholder for calculating arbitrage opportunities across exchanges."""
    try:
        arbitrage_df = pd.DataFrame(columns=['Ticker', 'Buy_Exchange', 'Sell_Exchange', 'Profit', 'Profit_Pct'])
        # Implement arbitrage logic if needed
        logger.info("Arbitrage calculation not implemented, returning empty DataFrame")
        return arbitrage_df
    except Exception as e:
        logger.error(f"Error in calculate_arbitrage_opportunities: {e}")
        return pd.DataFrame(columns=['Ticker', 'Buy_Exchange', 'Sell_Exchange', 'Profit', 'Profit_Pct'])

def calculate_buy_vs_produce(df, chains, tiers):
    """Placeholder for calculating buy vs produce decisions."""
    try:
        decisions_df = pd.DataFrame(columns=['Ticker', 'Input_Cost', 'Cost_Ratio', 'Recommendation', 'Risk', 'Viability'])
        # Implement buy vs produce logic if needed
        logger.info("Buy vs produce calculation not implemented, returning empty DataFrame")
        return decisions_df
    except Exception as e:
        logger.error(f"Error in calculate_buy_vs_produce: {e}")
        return pd.DataFrame(columns=['Ticker', 'Input_Cost', 'Cost_Ratio', 'Recommendation', 'Risk', 'Viability'])

def analyze_data(processed_df, chains=None, tickers=None, tiers=None):
    """Analyze processed data and return results grouped by exchange."""
    try:
        if processed_df.empty:
            logger.warning("Empty processed DataFrame, returning empty results")
            return {cx: pd.DataFrame(columns=EXPECTED_HEADERS) for cx in VALID_EXCHANGES}, {}, []

        # Load tickers, chains, and tiers from cache if not provided
        if tickers is None:
            tickers_file = os.path.join(CACHE_DIR, 'tickers.json')
            tickers = json.load(open(tickers_file)) if os.path.exists(tickers_file) else {t: TIER_0_RESOURCES[t]['name'] for t in TIER_0_RESOURCES}
        if chains is None:
            chains_file = os.path.join(CACHE_DIR, 'recipes.json')
            chains = json.load(open(chains_file)) if os.path.exists(chains_file) else {t.lower(): {'inputs': {}, 'building': 'MINE'} for t in TIER_0_RESOURCES}
        if tiers is None:
            tiers_file = os.path.join(CACHE_DIR, 'tiers.json')
            tiers = json.load(open(tiers_file)) if os.path.exists(tiers_file) else {t.lower(): TIER_0_RESOURCES[t]['tier'] for t in TIER_0_RESOURCES}

        analysis_results = {}
        trends = {}
        recommendations = []

        # Calculate spread percentage
        processed_df['spread_pct'] = ((processed_df['Ask_Price'] - processed_df['Bid_Price']) / processed_df['Bid_Price'].replace(0, 1)) * 100

        for ticker in processed_df['Ticker'].unique():
            ticker_data = processed_df[processed_df['Ticker'] == ticker]
            avg_spread = ticker_data['spread_pct'].mean() if 'spread_pct' in ticker_data.columns else np.nan
            trends[ticker] = {'avg_spread': avg_spread}
            if pd.notna(avg_spread) and avg_spread > 5:
                recommendations.append({'Ticker': ticker, 'Recommendation': f'Buy on {ticker_data["Exchange"].iloc[0]}'})

        for exchange in VALID_EXCHANGES:
            exchange_df = processed_df[processed_df['Exchange'] == exchange].copy()
            if exchange_df.empty:
                logger.warning(f"No data for exchange {exchange}")
                analysis_results[exchange] = pd.DataFrame(columns=EXPECTED_HEADERS)
                continue

            # Arbitrage opportunities
            arbitrage_df = calculate_arbitrage_opportunities(exchange_df)
            if not arbitrage_df.empty:
                buy_opportunities = arbitrage_df[arbitrage_df['Buy_Exchange'] == exchange]
                exchange_df = exchange_df.merge(
                    buy_opportunities[['Ticker', 'Profit', 'Profit_Pct']].groupby('Ticker').max().reset_index(),
                    on='Ticker', how='left'
                )

            # Buy vs produce decisions
            decisions_df = calculate_buy_vs_produce(exchange_df, chains, tiers)
            if not decisions_df.empty:
                exchange_df = exchange_df.merge(
                    decisions_df[['Ticker', 'Input_Cost', 'Cost_Ratio', 'Recommendation', 'Risk', 'Viability']],
                    on='Ticker', how='left'
                )

            # Ensure all expected columns
            for col in EXPECTED_HEADERS:
                if col not in exchange_df.columns:
                    exchange_df[col] = 0.0 if col in ['Profit', 'Profit_Pct', 'ROI_Ask', 'Investment_Score', 'Risk', 'Viability', 'Input_Cost', 'Cost_Ratio', 'Ask_Price', 'Bid_Price', 'Saturation'] else ''

            exchange_df['ROI_Ask'] = exchange_df.apply(
                lambda row: (row['Profit'] / row['Ask_Price'] * 100) if pd.notna(row['Ask_Price']) and row['Ask_Price'] > 0 else 0, axis=1
            )
            exchange_df['Investment_Score'] = exchange_df['Profit'].rank(method='dense')
            exchange_df['Product'] = exchange_df['Ticker'].map(tickers).fillna(exchange_df['Ticker'])
            exchange_df['Material'] = exchange_df['Ticker']
            exchange_df['Tier'] = exchange_df['Ticker'].map(tiers).fillna(0)

            for col in ['Profit', 'Profit_Pct', 'ROI_Ask', 'Investment_Score', 'Risk', 'Viability']:
                exchange_df[col] = exchange_df.get(col, 0)

            analysis_results[exchange] = exchange_df[EXPECTED_HEADERS]
            logger.info(f"Analyzed {exchange}: {len(exchange_df)} rows")

        return analysis_results, trends, recommendations
    except Exception as e:
        logger.error(f"Error analyzing data: {e}")
        return {cx: pd.DataFrame(columns=EXPECTED_HEADERS) for cx in VALID_EXCHANGES}, {}, []

@rate_limited_api_call
def fetch_csv_data(url):
    """Fetch CSV data from URL with rate limiting."""
    logger.info(f"Fetching data from: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))

def fetch_and_cache_market_data():
    """Fetch market data with rate limiting."""
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
    cache_file = os.path.join(cache_dir, 'market_data.csv')
    
    try:
        # Try to fetch fresh data
        df = fetch_csv_data("https://rest.fnar.net/csv/prices")
        
        # Cache the data
        os.makedirs(cache_dir, exist_ok=True)
        df.to_csv(cache_file, index=False)
        logger.info(f"Successfully fetched and cached {len(df)} market data records")
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch market data: {e}")
        
        # Try to load from cache as fallback
        if os.path.exists(cache_file):
            logger.info("Loading market data from cache as fallback")
            return pd.read_csv(cache_file)
        else:
            logger.error("No cached market data available")
            return pd.DataFrame()

def fetch_and_cache_buildings():
    """Fetch buildings data with rate limiting."""
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
    cache_file = os.path.join(cache_dir, 'buildings.json')
    
    try:
        # Fetch buildings data
        df = fetch_csv_data("https://rest.fnar.net/csv/buildings")
        
        # Convert to dictionary
        buildings_dict = {}
        for _, row in df.iterrows():
            ticker = str(row.get('Ticker', '')).lower()
            if ticker:
                buildings_dict[ticker] = {
                    'name': row.get('Name', ''),
                    'expertise': row.get('Expertise', ''),
                    'pioneers': row.get('Pioneers', 0),
                    'settlers': row.get('Settlers', 0),
                    'technicians': row.get('Technicians', 0),
                    'engineers': row.get('Engineers', 0),
                    'scientists': row.get('Scientists', 0)
                }
        
        # Cache the data
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(buildings_dict, f, indent=2)
        
        logger.info(f"Successfully fetched and cached {len(buildings_dict)} buildings")
        return buildings_dict
        
    except Exception as e:
        logger.error(f"Failed to fetch buildings data: {e}")
        
        # Try to load from cache as fallback
        if os.path.exists(cache_file):
            logger.info("Loading buildings data from cache as fallback")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.error("No cached buildings data available")
            return {}

def fetch_and_cache_chains():
    """Fetch chains data with rate limiting."""
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
    cache_file = os.path.join(cache_dir, 'chains.json')
    
    try:
        # Fetch required data with delays between requests
        logger.info("Fetching materials data...")
        materials_df = fetch_csv_data("https://rest.fnar.net/csv/materials")
        
        logger.info("Fetching buildings data...")
        buildings_df = fetch_csv_data("https://rest.fnar.net/csv/buildings")
        
        logger.info("Fetching recipe inputs...")
        recipe_inputs_df = fetch_csv_data("https://rest.fnar.net/csv/recipeinputs")
        
        logger.info("Fetching recipe outputs...")
        recipe_outputs_df = fetch_csv_data("https://rest.fnar.net/csv/recipeoutputs")
        
        logger.info("Fetching building workforces...")
        workforces_df = fetch_csv_data("https://rest.fnar.net/csv/buildingworkforces")
        
        # Process the data to create chains
        chains = {}
        
        # Process recipe outputs to get basic recipe info
        for _, output_row in recipe_outputs_df.iterrows():
            ticker = str(output_row.get('Ticker', '')).lower()
            if ticker:
                chains[ticker] = {
                    'inputs': {},
                    'tier': 0,
                    'time': 24,  # Default production time
                    'building': ''
                }
        
        # Add input materials
        for _, input_row in recipe_inputs_df.iterrows():
            ticker = str(input_row.get('Ticker', '')).lower()
            material_ticker = str(input_row.get('MaterialTicker', '')).lower()
            amount = input_row.get('Amount', 1)
            
            if ticker in chains:
                chains[ticker]['inputs'][material_ticker] = amount
        
        # Add tier information from materials
        for _, material_row in materials_df.iterrows():
            ticker = str(material_row.get('Ticker', '')).lower()
            tier = material_row.get('Tier', 0)
            
            if ticker in chains:
                chains[ticker]['tier'] = tier
        
        # Cache the data
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(chains, f, indent=2)
        
        logger.info(f"Successfully processed and cached {len(chains)} chains")
        return chains
        
    except Exception as e:
        logger.error(f"Failed to fetch chains data: {e}")
        
        # Try to load from cache as fallback
        if os.path.exists(cache_file):
            logger.info("Loading chains data from cache as fallback")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.error("No cached chains data available")
            return {}