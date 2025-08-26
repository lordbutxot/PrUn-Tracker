"""
Environment-specific settings
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EnvironmentConfig:
    def __init__(self):
        self.required_env_vars = [
            'PRUN_SPREADSHEET_ID',
        ]
        self.optional_env_vars = {
            'PRUN_CACHE_TTL': '300',
            'PRUN_API_TIMEOUT': '30',
            'PRUN_RATE_LIMIT': '10'
        }
    
    def load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        # Load required variables
        for var in self.required_env_vars:
            value = os.getenv(var)
            if value is None:
                logger.warning(f"Required environment variable {var} not set")
            config[var] = value
        
        # Load optional variables with defaults
        for var, default in self.optional_env_vars.items():
            config[var] = os.getenv(var, default)
        
        return config
    
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are available"""
        missing = []
        for var in self.required_env_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            logger.error(f"Missing required environment variables: {missing}")
            return False
        
        return True
    
    def get_spreadsheet_id(self) -> Optional[str]:
        """Get spreadsheet ID from environment or fallback"""
        return os.getenv('PRUN_SPREADSHEET_ID', '1YourSpreadsheetIdHere')