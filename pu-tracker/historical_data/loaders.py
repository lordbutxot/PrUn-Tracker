"""
Data Loading Module
Centralized data loading functions for CSV and JSON files
"""

import pandas as pd
import json
from pathlib import Path
from config import CACHE_DIR, CACHE_FILES


# ==================== CSV LOADERS ====================

def load_materials():
    """Load materials.csv with basic material information"""
    path = CACHE_DIR / CACHE_FILES['materials']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=['Ticker', 'Name', 'Category', 'Weight', 'Volume', 'Tier'])


def load_market_data():
    """
    Load market data (prices, supply, demand) for all exchanges.
    Returns long format DataFrame with columns: Ticker, Exchange, Ask_Price, Bid_Price, etc.
    """
    # Try long format first
    path_long = CACHE_DIR / CACHE_FILES['market_data_long']
    if path_long.exists():
        return pd.read_csv(path_long)
    
    # Fallback to wide format and transform
    path_wide = CACHE_DIR / CACHE_FILES['market_data']
    if not path_wide.exists():
        return pd.DataFrame(columns=['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price'])
    
    df = pd.read_csv(path_wide)
    
    # Check if transformation is needed
    if 'Exchange' in df.columns:
        return df
    
    # Transform wide to long format
    exchanges = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']
    records = []
    
    for _, row in df.iterrows():
        ticker = row['Ticker']
        for exch in exchanges:
            ask_col = f"{exch}-AskPrice"
            bid_col = f"{exch}-BidPrice"
            ask_amt_col = f"{exch}-AskAmt"
            bid_amt_col = f"{exch}-BidAmt"
            ask_avail_col = f"{exch}-AskAvail"
            bid_avail_col = f"{exch}-BidAvail"
            avg_col = f"{exch}-Average"
            
            ask_price = row.get(ask_col, None)
            bid_price = row.get(bid_col, None)
            
            if pd.notnull(ask_price) or pd.notnull(bid_price):
                records.append({
                    'Ticker': ticker,
                    'Exchange': exch,
                    'Ask_Price': pd.to_numeric(ask_price, errors='coerce') if pd.notnull(ask_price) else 0,
                    'Bid_Price': pd.to_numeric(bid_price, errors='coerce') if pd.notnull(bid_price) else 0,
                    'Ask_Amount': pd.to_numeric(row.get(ask_amt_col, 0), errors='coerce'),
                    'Bid_Amount': pd.to_numeric(row.get(bid_amt_col, 0), errors='coerce'),
                    'Ask_Available': pd.to_numeric(row.get(ask_avail_col, 0), errors='coerce'),
                    'Bid_Available': pd.to_numeric(row.get(bid_avail_col, 0), errors='coerce'),
                    'Average': pd.to_numeric(row.get(avg_col, 0), errors='coerce'),
                })
    
    df_long = pd.DataFrame(records)
    
    # Save transformed data for future use
    df_long.to_csv(path_long, index=False)
    
    return df_long


def load_processed_data():
    """Load processed_data.csv with calculated metrics"""
    path = CACHE_DIR / CACHE_FILES['processed_data']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def load_daily_analysis():
    """Load daily_analysis.csv"""
    path = CACHE_DIR / CACHE_FILES['daily_analysis']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def load_daily_analysis_enhanced():
    """Load daily_analysis_enhanced.csv with all enhanced metrics"""
    path = CACHE_DIR / CACHE_FILES['daily_analysis_enhanced']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def load_orders():
    """Load orders.csv (sell orders)"""
    path = CACHE_DIR / CACHE_FILES['orders']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def load_bids():
    """Load bids.csv (buy orders)"""
    path = CACHE_DIR / CACHE_FILES['bids']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def load_buildings():
    """Load buildings.csv with building information"""
    path = CACHE_DIR / CACHE_FILES['buildings']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def load_buildingrecipes():
    """
    Load buildingrecipes.csv and enhance with workforce data from buildings.json.
    Returns DataFrame indexed by 'Key' with columns including Workforce and WorkforceAmount.
    """
    path = CACHE_DIR / CACHE_FILES['buildingrecipes']
    if not path.exists():
        print("[WARN] buildingrecipes.csv not found, workforce costs will be skipped.")
        return None
    
    df = pd.read_csv(path)
    
    if "Key" not in df.columns:
        print("[WARN] buildingrecipes.csv missing 'Key' column.")
        return None
    
    # Load buildings.json to get workforce requirements
    buildings_path = CACHE_DIR / CACHE_FILES['buildings_json']
    if buildings_path.exists():
        with open(buildings_path, 'r', encoding='utf-8') as f:
            buildings_data = json.load(f)
        
        def get_workforce_info(building_ticker):
            """Extract workforce type and amount from buildings.json"""
            if building_ticker in buildings_data:
                building = buildings_data[building_ticker]
                for wf_type in ['PIONEER', 'SETTLER', 'TECHNICIAN', 'ENGINEER', 'SCIENTIST']:
                    wf_key = wf_type.lower() + 's'  # pioneers, settlers, etc.
                    amount = building.get(wf_key, 0)
                    if amount > 0:
                        return wf_type, amount
            return None, 0
        
        df['Workforce'] = df['Building'].apply(lambda x: get_workforce_info(x)[0])
        df['WorkforceAmount'] = df['Building'].apply(lambda x: get_workforce_info(x)[1])
        
        # Convert Duration from seconds to minutes
        if 'Duration' in df.columns:
            df['Time'] = df['Duration'].astype(float) / 60
    else:
        print("[WARN] buildings.json not found, workforce costs will be missing.")
    
    return df.set_index("Key")


def load_recipe_inputs():
    """Load recipe_inputs.csv (materials required for each recipe)"""
    path = CACHE_DIR / CACHE_FILES['recipe_inputs']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=['Key', 'Material', 'Amount'])


def load_recipe_outputs():
    """Load recipe_outputs.csv (materials produced by each recipe)"""
    path = CACHE_DIR / CACHE_FILES['recipe_outputs']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=['Key', 'Material', 'Amount'])


def load_workforces():
    """Load workforces.csv"""
    path = CACHE_DIR / CACHE_FILES['workforces']
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


# ==================== JSON LOADERS ====================

def load_materials_json():
    """Load materials.json with detailed material information"""
    path = CACHE_DIR / CACHE_FILES['materials_json']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_buildings_json():
    """Load buildings.json with building and workforce information"""
    path = CACHE_DIR / CACHE_FILES['buildings_json']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_recipes_json():
    """Load recipes.json with recipe information"""
    path = CACHE_DIR / CACHE_FILES['recipes_json']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_byproduct_recipes():
    """Load byproduct_recipes.json (recipes with multiple outputs)"""
    path = CACHE_DIR / CACHE_FILES['byproduct_recipes']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_workforceneeds():
    """
    Load workforceneeds.json and convert to per-worker per-hour consumption rates.
    Returns dict with structure:
    {
        "PIONEER": {
            "necessary": {"DW": 0.00167, "RAT": 0.00125, "OVE": 0.00021},
            "luxury": {"PWO": 0.000083, "COF": 0.00021}
        },
        ...
    }
    """
    path = CACHE_DIR / CACHE_FILES['workforceneeds']
    if not path.exists():
        print("[WARN] workforceneeds.json not found, using empty mapping.")
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    needs = {}
    for wf in data:
        # Try both possible key names
        name = wf.get("name") or wf.get("WorkforceType")
        if name:
            needs[name] = {"necessary": {}, "luxury": {}}
            needs_list = wf.get("needs", wf.get("Needs", []))
            for need in needs_list:
                ticker = need.get("ticker") or need.get("MaterialTicker")
                amount = need.get("amountPerWorkerPerHour") or need.get("Amount", 0)
                material_name = need.get("MaterialName", "")
                
                if ticker and amount:
                    # JSON stores consumption per 100 workers per day
                    # Convert to per single worker per hour: amount / 100 / 24
                    per_hour_per_worker = float(amount) / 100.0 / 24.0
                    
                    # Categorize as luxury or necessary based on MaterialName
                    if "Luxury" in material_name or "luxury" in material_name:
                        needs[name]["luxury"][ticker] = per_hour_per_worker
                    else:
                        needs[name]["necessary"][ticker] = per_hour_per_worker
    
    return needs


def load_categories():
    """Load categories.json"""
    path = CACHE_DIR / CACHE_FILES['categories']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_tiers():
    """Load tiers.json (material tier mappings)"""
    path = CACHE_DIR / CACHE_FILES['tiers']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_chains():
    """Load chains.json (production chain information)"""
    path = CACHE_DIR / CACHE_FILES['chains']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_tier0_resources():
    """Load tier0_resources.json (extractable materials)"""
    path = CACHE_DIR / CACHE_FILES['tier0_resources']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_tickers():
    """Load tickers.json"""
    path = CACHE_DIR / CACHE_FILES['tickers']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_cache_metadata():
    """Load cache_metadata.json (timestamp and hash information)"""
    path = CACHE_DIR / CACHE_FILES['cache_metadata']
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# ==================== HELPER FUNCTIONS ====================

def get_market_price(ticker, market_prices, exchange="AI1", price_type="Ask"):
    """
    Get market price for a specific ticker and exchange.
    
    Args:
        ticker: Material ticker symbol
        market_prices: DataFrame from load_market_data()
        exchange: Exchange code (AI1, CI1, etc.)
        price_type: "Ask" or "Bid"
    
    Returns:
        Price as float, or 0.0 if not found
    """
    if market_prices.empty:
        return 0.0
    
    row = market_prices[
        (market_prices['Ticker'] == ticker) & 
        (market_prices['Exchange'] == exchange)
    ]
    
    if not row.empty:
        price_col = f'{price_type}_Price'
        price = row.iloc[0].get(price_col, 0)
        return float(price) if pd.notnull(price) else 0.0
    
    return 0.0


def load_market_prices_as_dict(exchange="AI1", price_type="Ask"):
    """
    Load market prices as a dictionary for quick lookup.
    
    Args:
        exchange: Exchange code
        price_type: "Ask" or "Bid"
    
    Returns:
        Dict of {ticker: price}
    """
    market_data = load_market_data()
    prices = {}
    
    for _, row in market_data[market_data['Exchange'] == exchange].iterrows():
        ticker = row['Ticker']
        price_col = f'{price_type}_Price'
        price = row.get(price_col, 0)
        prices[ticker] = float(price) if pd.notnull(price) else 0.0
    
    return prices


def check_cache_exists():
    """Check if all essential cache files exist"""
    essential_files = ['materials', 'market_data', 'buildingrecipes', 'workforceneeds']
    missing = []
    
    for file_key in essential_files:
        filename = CACHE_FILES.get(file_key)
        if filename:
            path = CACHE_DIR / filename
            if not path.exists():
                missing.append(filename)
    
    return len(missing) == 0, missing


def get_cache_file_info():
    """Get information about all cache files"""
    info = {}
    
    for key, filename in CACHE_FILES.items():
        path = CACHE_DIR / filename
        info[key] = {
            'filename': filename,
            'exists': path.exists(),
            'size': path.stat().st_size if path.exists() else 0,
            'modified': path.stat().st_mtime if path.exists() else 0
        }
    
    return info
