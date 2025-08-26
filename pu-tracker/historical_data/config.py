"""
Configuration constants and settings
"""
import json
import os
# Remove the problematic relative import for now
# from ..configuration.app_config import config

# Directory paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Valid exchanges for Prosperous Universe
VALID_EXCHANGES = ['AI1', 'IC1', 'CI1', 'CI2', 'NC1', 'NC2']

# Expected exchanges (used in sheet_updater.py, can be same as VALID_EXCHANGES)
EXPECTED_EXCHANGES = VALID_EXCHANGES

# Cache refresh interval (hours)
REFRESH_INTERVAL_HOURS = 24

# Google Sheets configuration
TARGET_SPREADSHEET_ID = '1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI'
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'historical_data', 'prun-profit-7e0c3bafd690.json')

# Formatting configurations for Google Sheets
FORMAT_CONFIGS = [
    ('A:A', {'numberFormat': {'type': 'TEXT'}}),  # Ticker
    ('B:B', {'numberFormat': {'type': 'TEXT'}}),  # Product
    ('C:C', {'numberFormat': {'type': 'TEXT'}}),  # Category
    ('D:D', {'numberFormat': {'type': 'NUMBER', 'pattern': '0'}}),  # Tier
    ('E:E', {'numberFormat': {'type': 'TEXT'}}),  # Input Materials
    ('F:Z', {'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00'}}),  # Numeric columns
]

# Try to load TIER_0_RESOURCES from JSON file, fallback to hardcoded list
try:
    tier0_file = os.path.join(CACHE_DIR, "tier0_resources.json")
    if os.path.exists(tier0_file):
        with open(tier0_file, "r", encoding="utf-8") as f:
            TIER_0_RESOURCES = json.load(f)
    else:
        # Fallback to hardcoded list
        TIER_0_RESOURCES = [
            'H2O', 'O', 'C', 'SI', 'FE', 'CU', 'S', 'CA', 'NA', 'CL', 'AR', 'HE', 
            'LI', 'B', 'F', 'NE', 'MG', 'AL', 'P', 'K', 'TI', 'CR', 'MN', 'NI', 
            'BR', 'KR', 'RB', 'SR', 'ZR', 'AG', 'SN', 'XE', 'CS', 'BA', 'AU', 
            'HG', 'PB', 'BI', 'RN', 'RA', 'AC', 'TH', 'U'
        ]
except Exception:
    # Fallback to hardcoded list if any error occurs
    TIER_0_RESOURCES = [
        'H2O', 'O', 'C', 'SI', 'FE', 'CU', 'S', 'CA', 'NA', 'CL', 'AR', 'HE', 
        'LI', 'B', 'F', 'NE', 'MG', 'AL', 'P', 'K', 'TI', 'CR', 'MN', 'NI', 
        'BR', 'KR', 'RB', 'SR', 'ZR', 'AG', 'SN', 'XE', 'CS', 'BA', 'AU', 
        'HG', 'PB', 'BI', 'RN', 'RA', 'AC', 'TH', 'U'
    ]

# Rate limiting settings
RATE_LIMIT_SETTINGS = {
    'api_calls': {
        'max_retries': 3,
        'base_delay': 1.0,
        'max_delay': 30.0,
        'backoff_factor': 2.0
    },
    'google_sheets': {
        'max_retries': 5,
        'base_delay': 2.0,
        'max_delay': 60.0,
        'backoff_factor': 2.5,
        'min_delay_between_ops': 1.5
    }
}

# Google Sheets API quotas (for reference)
SHEETS_QUOTAS = {
    'read_requests_per_minute': 100,
    'write_requests_per_minute': 100,
    'requests_per_100_seconds': 1000
}

# Add missing constants if they don't exist
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache')

# Use the TARGET_SPREADSHEET_ID defined earlier, don't override it
# TARGET_SPREADSHEET_ID = os.getenv('PRUN_SPREADSHEET_ID', '1YourSpreadsheetIdHere')

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Export configuration as a dictionary
CONFIG = {
    'BASE_DIR': BASE_DIR,
    'CACHE_DIR': CACHE_DIR,
    'DATA_DIR': DATA_DIR,
    'VALID_EXCHANGES': VALID_EXCHANGES,
    'EXPECTED_EXCHANGES': EXPECTED_EXCHANGES,
    'REFRESH_INTERVAL_HOURS': REFRESH_INTERVAL_HOURS,
    'TARGET_SPREADSHEET_ID': TARGET_SPREADSHEET_ID,
    'CREDENTIALS_FILE': CREDENTIALS_FILE,
    'GOOGLE_SERVICE_ACCOUNT_FILE': CREDENTIALS_FILE,  # Add this key for compatibility
    'FORMAT_CONFIGS': FORMAT_CONFIGS,
    'TIER_0_RESOURCES': TIER_0_RESOURCES,
    'RATE_LIMIT_SETTINGS': RATE_LIMIT_SETTINGS,
    'SHEETS_QUOTAS': SHEETS_QUOTAS
}

