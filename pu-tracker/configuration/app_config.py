"""
Application-wide configuration
"""
import os
from typing import Dict, Any

class CacheConfig:
    def __init__(self):
        self.cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
        self.ttl_seconds = 300  # 5 minutes
        self.max_cache_size = 1000
    
    @property
    def cache_path(self):
        return self.cache_dir

class APIConfig:
    def __init__(self):
        self.base_url = "https://rest.fnar.net"
        self.timeout = 30
        self.max_retries = 3
        self.rate_limit_per_second = 10

class SheetsConfig:
    def __init__(self):
        self.credentials_file = "prun-profit-7e0c3bafd690.json"
        self.spreadsheet_id = "1YourSpreadsheetIdHere"  # Replace with actual ID
        self.batch_size = 3
        self.rate_limit_delay = 10

class AppConfig:
    def __init__(self):
        self._cache_settings = CacheConfig()
        self._api_settings = APIConfig()
        self._sheets_settings = SheetsConfig()
    
    @property
    def cache_settings(self):
        return self._cache_settings
    
    @property
    def api_settings(self):
        return self._api_settings
    
    @property
    def sheets_settings(self):
        return self._sheets_settings

# Global configuration instance
config = AppConfig()

"""
Environment-specific settings
"""
class EnvironmentConfig:
    def load_from_env(self):
        pass
    
    def validate_required_settings(self):
        pass