"""
Unified Configuration for PrUn-Tracker
Consolidates all configuration from config.py, app_config.py, and environment_config.py
"""
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class UnifiedConfig:
    """Unified configuration class combining all config sources."""
    
    def __init__(self):
        # Base directory paths
        self.BASE_DIR = Path(__file__).parent.parent.absolute()  # pu-tracker level
        self.CACHE_DIR = self.BASE_DIR / 'cache'
        self.DATA_DIR = self.BASE_DIR / 'data'
        self.LOGS_DIR = self.BASE_DIR / 'logs'
        
        # Ensure directories exist
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        
        # Load environment variables
        self._load_environment_config()
        
        # Initialize all configuration sections
        self._init_exchange_config()
        self._init_google_sheets_config()
        self._init_api_config()
        self._init_cache_config()
        self._init_rate_limiting_config()
        self._init_formatting_config()
        
        # Load dynamic resources
        self._load_tier0_resources()
    
    def _load_environment_config(self):
        """Load configuration from environment variables."""
        self.required_env_vars = ['PRUN_SPREADSHEET_ID']
        self.optional_env_vars = {
            'PRUN_CACHE_TTL': '300',
            'PRUN_API_TIMEOUT': '30',
            'PRUN_RATE_LIMIT': '10'
        }
        
        self.env_config = {}
        
        # Load required variables
        for var in self.required_env_vars:
            value = os.getenv(var)
            if value:
                self.env_config[var] = value
            else:
                logger.warning(f"Required environment variable {var} not set")
        
        # Load optional variables with defaults
        for var, default in self.optional_env_vars.items():
            self.env_config[var] = os.getenv(var, default)
    
    def _init_exchange_config(self):
        """Initialize exchange-related configuration."""
        self.VALID_EXCHANGES = ['AI1', 'IC1', 'CI1', 'CI2', 'NC1', 'NC2']
        self.EXPECTED_EXCHANGES = self.VALID_EXCHANGES
        
        # Exchange mappings
        self.EXCHANGE_MAPPING = {
            'AI1': 'Antares I',
            'IC1': 'Interstellar Coalition I', 
            'NC1': 'New Ceres I',
            'NC2': 'New Ceres II',
            'CI1': 'Ceres I',
            'CI2': 'Ceres II'
        }
    
    def _init_google_sheets_config(self):
        """Initialize Google Sheets configuration."""
        # Spreadsheet IDs - Use environment variable or fallback
        spreadsheet_id = os.getenv('PRUN_SPREADSHEET_ID', '1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI')
        
        self.TARGET_SPREADSHEET_ID = spreadsheet_id
        self.PRUN_CALCULATOR_SPREADSHEET_ID = spreadsheet_id
        self.ONN_HISTORICAL_DATA_SPREADSHEET_ID = '1JhIzAhi435loaUxBog2qeJzYAKWPdmlL1GVDBm0lWiQ'
        
        # Credentials file
        self.CREDENTIALS_FILE = Path(__file__).parent / 'prun-profit-42c5889f620d.json'
        self.GOOGLE_SERVICE_ACCOUNT_FILE = self.CREDENTIALS_FILE  # Compatibility alias
        
        # Sheet names configuration
        self.CALCULATOR_SHEETS = {
            'DATA_AI1': 'DATA AI1',
            'DATA_CI1': 'DATA CI1',
            'DATA_CI2': 'DATA CI2',
            'DATA_NC1': 'DATA NC1',
            'DATA_NC2': 'DATA NC2',
            'DATA_IC1': 'DATA IC1',
            'REPORT_AI1': 'Report AI1',
            'REPORT_CI1': 'Report CI1',
            'REPORT_CI2': 'Report CI2',
            'REPORT_NC1': 'Report NC1',
            'REPORT_NC2': 'Report NC2',
            'REPORT_IC1': 'Report IC1',
            'HISTORICAL': 'ONN_Historical_Data'
        }
        
        # Google Sheets API scopes
        self.SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

    def _init_api_config(self):
        """Initialize API configuration."""
        self.API_BASE_URL = "https://rest.fnar.net"
        self.API_TIMEOUT = int(self.env_config.get('PRUN_API_TIMEOUT', 30))
        self.API_RETRY_COUNT = 3
        
    def _init_cache_config(self):
        """Initialize cache configuration."""
        self.CACHE_TTL = int(self.env_config.get('PRUN_CACHE_TTL', 300))
        self.CACHE_ENABLED = True
        
    def _init_rate_limiting_config(self):
        """Initialize rate limiting configuration."""
        self.RATE_LIMIT = int(self.env_config.get('PRUN_RATE_LIMIT', 10))
        
        # Structured rate limiting settings for different services
        self.RATE_LIMIT_SETTINGS = {
            'requests_per_minute': self.RATE_LIMIT,
            'burst_limit': 5,
            'google_sheets': {
                'min_delay_between_ops': 1.5,
                'batch_delay': 2.0,
                'max_retries': 3
            },
            'api_calls': {
                'min_delay': 1.0,
                'max_retries': 5
            }
        }
        self.SHEETS_QUOTAS = {
            'requests_per_100_seconds': 100,
            'requests_per_100_seconds_per_user': 100
        }
        
    def _init_formatting_config(self):
        """Initialize formatting configuration."""
        self.FORMAT_CONFIGS = {
            'header': {'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.8}},
            'currency': {'numberFormat': {'type': 'CURRENCY'}},
            'percentage': {'numberFormat': {'type': 'PERCENT'}}
        }
        
    def _load_tier0_resources(self):
        """Load tier 0 resources configuration."""
        self.TIER_0_RESOURCES = [
            'H', 'C', 'O', 'N', 'S', 'Ca', 'Fe', 'Mg', 'Si', 'Al'
        ]
        
    def _use_fallback_tier0_resources(self):
        """Use fallback tier 0 resources."""
        return self.TIER_0_RESOURCES
        
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are present."""
        return bool(self.TARGET_SPREADSHEET_ID and self.CREDENTIALS_FILE.exists())
        
    def get_spreadsheet_id(self) -> Optional[str]:
        """Get the current spreadsheet ID."""
        return self.TARGET_SPREADSHEET_ID
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'BASE_DIR': str(self.BASE_DIR),
            'CACHE_DIR': str(self.CACHE_DIR),
            'TARGET_SPREADSHEET_ID': self.TARGET_SPREADSHEET_ID,
            'VALID_EXCHANGES': self.VALID_EXCHANGES,
            'CALCULATOR_SHEETS': self.CALCULATOR_SHEETS
        }

# Add missing attributes that are referenced in the export section
# Default values for backward compatibility
REFRESH_INTERVAL_HOURS = 24
GOOGLE_SHEETS_CONFIG = {}

# Global configuration instance
config = UnifiedConfig()

# Export individual components for backward compatibility
BASE_DIR = config.BASE_DIR
CACHE_DIR = config.CACHE_DIR
DATA_DIR = config.DATA_DIR
VALID_EXCHANGES = config.VALID_EXCHANGES
EXPECTED_EXCHANGES = config.EXPECTED_EXCHANGES
TARGET_SPREADSHEET_ID = config.TARGET_SPREADSHEET_ID
PRUN_CALCULATOR_SPREADSHEET_ID = config.PRUN_CALCULATOR_SPREADSHEET_ID
ONN_HISTORICAL_DATA_SPREADSHEET_ID = config.ONN_HISTORICAL_DATA_SPREADSHEET_ID
CALCULATOR_SHEETS = config.CALCULATOR_SHEETS
CREDENTIALS_FILE = config.CREDENTIALS_FILE
FORMAT_CONFIGS = config.FORMAT_CONFIGS
TIER_0_RESOURCES = config.TIER_0_RESOURCES
RATE_LIMIT_SETTINGS = config.RATE_LIMIT_SETTINGS
SHEETS_QUOTAS = config.SHEETS_QUOTAS
CONFIG = config.to_dict()

# Add this line for import compatibility
unified_config = config

import os
from pathlib import Path

# Spreadsheet IDs
HISTORICAL_SPREADSHEET_ID = "1JhIzAhi435loaUxBog2qeJzYAKWPdmlL1GVDBm0lWiQ"  # ONN_Historical_Data
TARGET_SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"      # PrUn Calculator

# Use environment variable or default to TARGET
PRUN_SPREADSHEET_ID = os.getenv('PRUN_SPREADSHEET_ID', TARGET_SPREADSHEET_ID)

# Valid exchanges
VALID_EXCHANGES = ['AI1', 'IC1', 'CI1', 'CI2', 'NC1', 'NC2']

# Required columns for Google Sheets DATA tabs (COMPLETE LIST)
REQUIRED_DATA_COLUMNS = [
    'Ticker', 'Product', 'Exchange', 'Category', 'Tier',
    'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded',
    'Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 
    'ROI_Ask', 'ROI_Bid', 'Investment_Score', 'Risk', 'Viability',
    'Timestamp', 'Recommendation', 'Price_Spread'
]

# Report tab columns
REPORT_COLUMNS = [
    'Exchange', 'Total_Products', 'Avg_ROI', 'Best_Product', 
    'Total_Volume', 'Analysis_Date'
]

# File paths
CREDENTIALS_FILE = Path(__file__).parent / 'prun-profit-42c5889f620d.json'
CACHE_DIR = Path(__file__).parent.parent / 'cache'

# API settings
API_BASE_URL = "https://rest.fnar.net"
MAX_RETRIES = 3
RETRY_DELAY = 2

# Debug info
print(f"[CONFIG] Using spreadsheet: {PRUN_SPREADSHEET_ID}")
print(f"[CONFIG] Credentials exist: {CREDENTIALS_FILE.exists()}")
print(f"[CONFIG] Cache directory: {CACHE_DIR}")