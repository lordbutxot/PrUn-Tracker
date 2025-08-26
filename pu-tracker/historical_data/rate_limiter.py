import time
import random
import logging
from functools import wraps
import requests
from gspread.exceptions import APIError

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter with exponential backoff and jitter."""
    
    def __init__(self, max_retries=5, base_delay=1.0, max_delay=60.0, backoff_factor=2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.last_request_time = 0
        self.min_interval = 0.5  # Minimum time between requests
    
    def wait_if_needed(self):
        """Ensure minimum interval between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def calculate_delay(self, attempt):
        """Calculate delay with exponential backoff and jitter."""
        delay = min(self.base_delay * (self.backoff_factor ** attempt), self.max_delay)
        # Add jitter (random factor between 0.5 and 1.5)
        jitter = random.uniform(0.5, 1.5)
        return delay * jitter
    
    def retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with retry logic and exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                self.wait_if_needed()
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Request succeeded after {attempt} retries")
                return result
                
            except (APIError, requests.exceptions.RequestException) as e:
                last_exception = e
                
                # Check if it's a rate limit error
                is_rate_limit = False
                if isinstance(e, APIError) and '429' in str(e):
                    is_rate_limit = True
                elif isinstance(e, requests.exceptions.RequestException) and hasattr(e, 'response'):
                    if e.response and e.response.status_code == 429:
                        is_rate_limit = True
                
                if is_rate_limit and attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries + 1}). "
                                 f"Waiting {delay:.2f} seconds before retry...")
                    time.sleep(delay)
                    continue
                elif attempt < self.max_retries:
                    # For other errors, shorter delay
                    delay = min(1.0 * (attempt + 1), 5.0)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}). "
                                 f"Error: {str(e)}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    logger.error(f"Request failed after {self.max_retries + 1} attempts. Final error: {str(e)}")
                    raise last_exception
            
            except Exception as e:
                # Non-retryable error
                logger.error(f"Non-retryable error: {str(e)}")
                raise e
        
        # This should never be reached, but just in case
        raise last_exception

# Global rate limiter instances
API_RATE_LIMITER = RateLimiter(max_retries=3, base_delay=1.0, max_delay=30.0)
SHEETS_RATE_LIMITER = RateLimiter(max_retries=5, base_delay=2.0, max_delay=60.0, backoff_factor=2.5)

def rate_limited_api_call(func):
    """Decorator for API calls with rate limiting."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return API_RATE_LIMITER.retry_with_backoff(func, *args, **kwargs)
    return wrapper

def rate_limited_sheets_call(func):
    """Decorator for Google Sheets calls with rate limiting."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return SHEETS_RATE_LIMITER.retry_with_backoff(func, *args, **kwargs)
    return wrapper

def safe_sheets_operation(operation_func, *args, **kwargs):
    """Safely execute a Google Sheets operation with rate limiting."""
    return SHEETS_RATE_LIMITER.retry_with_backoff(operation_func, *args, **kwargs)

def safe_api_request(request_func, *args, **kwargs):
    """Safely execute an API request with rate limiting."""
    return API_RATE_LIMITER.retry_with_backoff(request_func, *args, **kwargs)