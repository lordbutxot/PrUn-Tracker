import time
import logging

logger = logging.getLogger(__name__)

class RateLimitedWorksheet:
    """Wrapper for gspread worksheet with rate limiting."""
    
    def __init__(self, worksheet):
        self.worksheet = worksheet
        self._last_operation_time = 0
        self.min_delay = 1.5  # Minimum delay between operations in seconds
    
    def _ensure_delay(self):
        """Ensure minimum delay between operations."""
        current_time = time.time()
        time_since_last = current_time - self._last_operation_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self._last_operation_time = time.time()
    
    def clear(self):
        """Clear worksheet with rate limiting."""
        self._ensure_delay()
        return self.worksheet.clear()
    
    def update(self, values, range_name=None, **kwargs):
        """Update worksheet with rate limiting."""
        self._ensure_delay()
        if range_name:
            return self.worksheet.update(values=values, range_name=range_name, **kwargs)
        else:
            return self.worksheet.update(values, **kwargs)
    
    def format(self, ranges, format_dict):
        """Format worksheet with rate limiting."""
        self._ensure_delay()
        return self.worksheet.format(ranges, format_dict)
    
    @property
    def title(self):
        return self.worksheet.title
    
    @property
    def id(self):
        return self.worksheet.id

class RateLimitedSpreadsheet:
    """Wrapper for gspread spreadsheet with rate limiting."""
    
    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet
        self._worksheet_cache = {}
    
    def worksheet(self, title):
        """Get worksheet with rate limiting wrapper."""
        if title not in self._worksheet_cache:
            ws = self.spreadsheet.worksheet(title)
            self._worksheet_cache[title] = RateLimitedWorksheet(ws)
        return self._worksheet_cache[title]
    
    def add_worksheet(self, title, rows=1000, cols=26):
        """Add worksheet with rate limiting."""
        ws = self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
        rate_limited_ws = RateLimitedWorksheet(ws)
        self._worksheet_cache[title] = rate_limited_ws
        return rate_limited_ws
    
    def worksheets(self):
        """Get all worksheets."""
        return self.spreadsheet.worksheets()
    
    @property
    def title(self):
        return self.spreadsheet.title
    
    @property
    def id(self):
        return self.spreadsheet.id

def create_rate_limited_client(client):
    """Create a rate-limited version of the gspread client."""
    class RateLimitedClient:
        def __init__(self, gspread_client):
            self.client = gspread_client
        
        def open_by_key(self, key):
            spreadsheet = self.client.open_by_key(key)
            return RateLimitedSpreadsheet(spreadsheet)
        
        def open(self, title):
            spreadsheet = self.client.open(title)
            return RateLimitedSpreadsheet(spreadsheet)
    
    return RateLimitedClient(client)