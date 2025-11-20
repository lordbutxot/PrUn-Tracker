"""
Configuration Module
Centralized configuration for PrUn-Tracker data processing
"""

from pathlib import Path

# ==================== DIRECTORIES ====================
# Base directories
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR.parent / 'cache'
LOGS_DIR = BASE_DIR.parent / 'logs'
DATA_DIR = BASE_DIR.parent / 'data'

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Financial data subdirectory
FINANCIAL_DATA_DIR = CACHE_DIR / 'financial_data'
FINANCIAL_DATA_DIR.mkdir(exist_ok=True)

# ==================== EXCHANGES ====================
VALID_EXCHANGES = ['AI1', 'CI1', 'CI2', 'NC1', 'NC2', 'IC1']

# Exchange display names
EXCHANGE_NAMES = {
    'AI1': 'Antares',
    'CI1': 'Katoa',
    'CI2': 'Vallis',
    'NC1': 'Montem',
    'NC2': 'Hubur',
    'IC1': 'Moria'
}

# ==================== API ENDPOINTS ====================
# FIO (FreeRangeGames) API base URL
FIO_API_BASE = "https://rest.fnar.net"

# FIO API endpoints
FIO_ENDPOINTS = {
    'building': f"{FIO_API_BASE}/building/{{ticker}}",
    'material': f"{FIO_API_BASE}/material/{{ticker}}",
    'recipe': f"{FIO_API_BASE}/recipes/allrecipes",
    'exchange': f"{FIO_API_BASE}/exchange/{{exchange}}",
    'systemstars': f"{FIO_API_BASE}/systemstars",
}

# CSV data endpoints
FIO_CSV_ENDPOINTS = {
    'materials': "https://doc.fnar.net/csv/materials.csv",
    'recipes': "https://doc.fnar.net/csv/recipes.csv",
    'buildings': "https://doc.fnar.net/csv/buildings.csv",
    'buildingrecipes': "https://doc.fnar.net/csv/buildingrecipes.csv",
    'workforceneeds': "https://doc.fnar.net/csv/workforceneeds.csv",
}

# ==================== GOOGLE SHEETS ====================
# Spreadsheet IDs
SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
FINANCIAL_SPREADSHEET_ID = "1nHiC8xHg2wWpEP_KCFmOXBgRkTZ09MQFshNOiIWDmFs"

# Sheet names for data upload
DATA_SHEET_NAMES = {
    'AI1': 'DATA AI1',
    'CI1': 'DATA CI1',
    'CI2': 'DATA CI2',
    'NC1': 'DATA NC1',
    'NC2': 'DATA NC2',
    'IC1': 'DATA IC1',
}

# Report sheet names
REPORT_SHEET_NAMES = {
    'AI1': 'Report AI1',
    'CI1': 'Report CI1',
    'CI2': 'Report CI2',
    'NC1': 'Report NC1',
    'NC2': 'Report NC2',
    'IC1': 'Report IC1',
    'Overall': 'Overall Report',
    'Financial': 'Financial Overview',
    'PriceAnalyser': 'Price Analyser',
    'PriceAnalyserData': 'Price Analyser Data',
}

# ==================== DATA STRUCTURE ====================
# Required columns for processed data
REQUIRED_DATA_COLUMNS = [
    'Ticker', 'Exchange', 'Category', 'Tier',
    'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded',
    'Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid',
    'ROI_Ask', 'ROI_Bid', 'Investment_Score', 'Risk', 'Viability'
]

# Target columns for enhanced analysis
ENHANCED_ANALYSIS_COLUMNS = [
    'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe', 
    'Amount per Recipe', 'Weight', 'Volume', 
    'Ask_Price', 'Bid_Price',
    'Input Cost per Unit', 'Input Cost per Stack', 'Input Cost per Hour',
    'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %',
    'Supply', 'Demand', 'Traded Volume', 'Saturation', 'Market Cap',
    'Liquidity Ratio', 'Investment Score', 'Risk Level', 'Volatility',
    'Exchange'
]

# ==================== CATEGORIES ====================
# Material categories for sectioned reports
MATERIAL_CATEGORIES = [
    'METALLURGY',
    'MANUFACTURING',
    'CONSTRUCTION',
    'CHEMISTRY',
    'FOOD_INDUSTRIES',
    'AGRICULTURE',
    'FUEL_REFINING',
    'ELECTRONICS',
    'RESOURCE_EXTRACTION'
]

# Category display names
CATEGORY_DISPLAY_NAMES = {
    'METALLURGY': 'Metallurgy',
    'MANUFACTURING': 'Manufacturing',
    'CONSTRUCTION': 'Construction',
    'CHEMISTRY': 'Chemistry',
    'FOOD_INDUSTRIES': 'Food Industries',
    'AGRICULTURE': 'Agriculture',
    'FUEL_REFINING': 'Fuel Refining',
    'ELECTRONICS': 'Electronics',
    'RESOURCE_EXTRACTION': 'Resource Extraction'
}

# ==================== WORKFORCE ====================
# Workforce types
WORKFORCE_TYPES = ['PIONEER', 'SETTLER', 'TECHNICIAN', 'ENGINEER', 'SCIENTIST']

# Workforce consumable tickers (for validation)
WORKFORCE_CONSUMABLES = {
    'PIONEER': ['DW', 'RAT', 'OVE'],
    'SETTLER': ['DW', 'RAT', 'OVE', 'EXO', 'PT', 'COF'],
    'TECHNICIAN': ['DW', 'RAT', 'OVE', 'EXO', 'PT', 'COF', 'PWO', 'MED'],
    'ENGINEER': ['DW', 'RAT', 'OVE', 'EXO', 'PT', 'COF', 'PWO', 'MED', 'HSS', 'SCN'],
    'SCIENTIST': ['DW', 'RAT', 'OVE', 'EXO', 'PT', 'COF', 'PWO', 'MED', 'HSS', 'SCN', 'WS', 'NV1']
}

# ==================== PROCESSING SETTINGS ====================
# Rate limiting for API calls
API_RATE_LIMIT_DELAY = 0.15  # seconds between requests

# Cache expiration (hours)
CACHE_EXPIRATION_HOURS = 24

# Data quality thresholds
MIN_TRADED_VOLUME = 0  # Minimum traded volume to consider material active
MIN_PRICE = 0.01  # Minimum price to avoid division by zero

# Investment scoring weights
INVESTMENT_WEIGHTS = {
    'roi': 0.4,
    'liquidity': 0.3,
    'risk': 0.3
}

# Risk level thresholds
RISK_THRESHOLDS = {
    'very_low': 0.2,
    'low': 0.4,
    'medium': 0.6,
    'high': 0.8,
}

# ==================== FILE NAMES ====================
# Cache file names
CACHE_FILES = {
    'materials': 'materials.csv',
    'materials_json': 'materials.json',
    'market_data': 'market_data.csv',
    'market_data_long': 'market_data_long.csv',
    'processed_data': 'processed_data.csv',
    'daily_analysis': 'daily_analysis.csv',
    'daily_analysis_enhanced': 'daily_analysis_enhanced.csv',
    'daily_report': 'daily_report.csv',
    'orders': 'orders.csv',
    'bids': 'bids.csv',
    'buildings': 'buildings.csv',
    'buildings_json': 'buildings.json',
    'buildingrecipes': 'buildingrecipes.csv',
    'recipe_inputs': 'recipe_inputs.csv',
    'recipe_outputs': 'recipe_outputs.csv',
    'recipes_json': 'recipes.json',
    'byproduct_recipes': 'byproduct_recipes.json',
    'workforceneeds': 'workforceneeds.json',
    'workforces': 'workforces.csv',
    'categories': 'categories.json',
    'tiers': 'tiers.json',
    'chains': 'chains.json',
    'tier0_resources': 'tier0_resources.json',
    'tickers': 'tickers.json',
    'prices_all': 'prices_all.csv',
    'cache_metadata': 'cache_metadata.json',
}

# ==================== LOGGING ====================
LOG_FORMAT = '[%(levelname)s] %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Log file naming
def get_log_filename(prefix='pipeline'):
    """Generate timestamped log filename"""
    timestamp = Path(__file__).parent.parent / 'logs' / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    return timestamp

# Color codes for terminal output
COLORS = {
    'HEADER': '\033[1;35m',
    'INFO': '\033[1;32m',
    'STEP': '\033[1;36m',
    'WARNING': '\033[1;33m',
    'ERROR': '\033[1;31m',
    'SUCCESS': '\033[1;32m',
    'RUNNING': '\033[1;33m',
    'RESET': '\033[0m'
}

# ==================== HELPER FUNCTIONS ====================
def get_cache_path(file_key):
    """Get full path to cache file by key"""
    filename = CACHE_FILES.get(file_key)
    if not filename:
        raise ValueError(f"Unknown cache file key: {file_key}")
    return CACHE_DIR / filename

def get_exchange_name(exchange_code):
    """Get display name for exchange code"""
    return EXCHANGE_NAMES.get(exchange_code, exchange_code)

def validate_exchange(exchange):
    """Check if exchange code is valid"""
    return exchange in VALID_EXCHANGES

# Import datetime for log filename generation
from datetime import datetime
