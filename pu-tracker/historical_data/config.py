import os

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