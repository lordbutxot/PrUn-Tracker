import os
import json
import pandas as pd
import time
import hashlib
from datetime import datetime, timedelta
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SmartCache:
    """Intelligent caching system to minimize API calls."""
    
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.cache_metadata_file = os.path.join(cache_dir, 'cache_metadata.json')
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """Load cache metadata."""
        if os.path.exists(self.cache_metadata_file):
            with open(self.cache_metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """Save cache metadata."""
        with open(self.cache_metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _get_file_hash(self, filepath: Optional[str]) -> Optional[str]:
        """Get hash of file contents."""
        if not filepath or not isinstance(filepath, str) or not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def is_cache_valid(self, cache_key: str, max_age_minutes: int = 60) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.metadata:
            return False
        
        cache_info = self.metadata[cache_key]
        cache_time = datetime.fromisoformat(cache_info['timestamp'])
        age = datetime.now() - cache_time
        
        return age < timedelta(minutes=max_age_minutes)
    
    def get_cached_data(self, cache_key: str, file_path: Optional[str] = None):
        """Get cached data if valid."""
        if not self.is_cache_valid(cache_key):
            return None

        if file_path is not None and os.path.exists(file_path):
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)

        return None
    
    def cache_data(self, cache_key: str, data, file_path: Optional[str] = None):
        """Cache data with metadata."""
        if file_path is None:
            # Only update metadata, don't try to save a file
            self.metadata[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'file_path': "",
                'file_hash': None
            }
            self._save_metadata()
            logger.info(f"Cached data for key: {cache_key} (no file)")
            return

        # At this point, file_path is guaranteed to be a str
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if file_path.endswith('.csv') and hasattr(data, 'to_csv'):
            data.to_csv(file_path, index=False)
        elif file_path.endswith('.json'):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        # Update metadata
        self.metadata[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'file_path': file_path,
            'file_hash': self._get_file_hash(file_path)
        }

        self._save_metadata()
        logger.info(f"Cached data for key: {cache_key}")
    
    def invalidate_cache(self, cache_key: str):
        """Invalidate specific cache entry."""
        if cache_key in self.metadata:
            del self.metadata[cache_key]
            self._save_metadata()
    
    def cleanup_old_cache(self, max_age_hours: int = 24):
        """Remove old cache entries."""
        current_time = datetime.now()
        to_remove = []
        
        for key, info in self.metadata.items():
            cache_time = datetime.fromisoformat(info['timestamp'])
            if current_time - cache_time > timedelta(hours=max_age_hours):
                to_remove.append(key)
        
        for key in to_remove:
            self.invalidate_cache(key)
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old cache entries")