"""
Unified Sheets Manager
Consolidates sheets_api.py, sheets_optimizer.py, and sheets_rate_limiter.py
"""
import time
import logging
import json
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread
from pathlib import Path
import sys

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import config with fallback
try:
    from unified_config import (
        TARGET_SPREADSHEET_ID, CREDENTIALS_FILE, 
        PRUN_SPREADSHEET_ID, VALID_EXCHANGES
    )
except ImportError:
    # Fallback values
    TARGET_SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
    PRUN_SPREADSHEET_ID = TARGET_SPREADSHEET_ID
    CREDENTIALS_FILE = current_dir / 'prun-profit-7e0c3bafd690.json'
    VALID_EXCHANGES = ['AI1', 'IC1', 'CI1', 'CI2', 'NC1', 'NC2']

logger = logging.getLogger(__name__)

def column_number_to_letter(col_num: int) -> str:
    """Convert column number to Excel-style letter notation (1->A, 27->AA, etc.)"""
    result = ""
    while col_num > 0:
        col_num -= 1  # Convert to 0-based
        result = chr(65 + (col_num % 26)) + result
        col_num //= 26
    return result

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
    
    def update(self, range_name: str, values: List[List], **kwargs):
        """Update worksheet with rate limiting - FIXED parameter order"""
        self._ensure_delay()
        return self.worksheet.update(range_name=range_name, values=values, **kwargs)
    
    def format(self, ranges: str, format_dict: Dict):
        """Format worksheet with rate limiting."""
        self._ensure_delay()
        return self.worksheet.format(ranges, format_dict)
    
    @property
    def title(self) -> str:
        return self.worksheet.title
    
    @property
    def id(self) -> str:
        return str(self.worksheet.id)

class RateLimitedSpreadsheet:
    """Wrapper for gspread spreadsheet with rate limiting."""
    
    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet
        self._worksheet_cache: Dict[str, RateLimitedWorksheet] = {}
    
    def worksheet(self, title: str) -> RateLimitedWorksheet:
        """Get worksheet with rate limiting wrapper."""
        if title not in self._worksheet_cache:
            ws = self.spreadsheet.worksheet(title)
            self._worksheet_cache[title] = RateLimitedWorksheet(ws)
        return self._worksheet_cache[title]
    
    def add_worksheet(self, title: str, rows: int = 1000, cols: int = 26) -> RateLimitedWorksheet:
        """Add worksheet with rate limiting."""
        ws = self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
        rate_limited_ws = RateLimitedWorksheet(ws)
        self._worksheet_cache[title] = rate_limited_ws
        return rate_limited_ws
    
    def worksheets(self):
        """Get all worksheets."""
        return self.spreadsheet.worksheets()
    
    @property
    def title(self) -> str:
        return self.spreadsheet.title
    
    @property
    def id(self) -> str:
        return str(self.spreadsheet.id)

class SheetsManager:
    """Simplified Google Sheets manager for the main pipeline."""
    
    def __init__(self):
        self.client = None
        self.credentials_file = CREDENTIALS_FILE
        
    def connect(self):
        """Connect to Google Sheets API"""
        try:
            if not self.credentials_file.exists():
                print(f"[ERROR] Credentials file not found: {self.credentials_file}")
                return False
                
            # Define scopes
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Load credentials
            credentials = Credentials.from_service_account_file(
                str(self.credentials_file), 
                scopes=scopes
            )
            
            # Create client
            self.client = gspread.authorize(credentials)
            print("[SUCCESS] Connected to Google Sheets API")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to connect to Google Sheets: {e}")
            return False
    
    def upload_to_sheet(self, spreadsheet_id, worksheet_name, dataframe, clear_first=True):
        """Upload DataFrame to specific worksheet - FIXED VERSION"""
        try:
            if self.client is None:
                print("[ERROR] Not connected to Google Sheets")
                return False
                
            print(f"[INFO] Uploading to {worksheet_name} - {len(dataframe)} rows, {len(dataframe.columns)} columns")
            
            # Open spreadsheet
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            
            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                print(f"[INFO] Creating new worksheet: {worksheet_name}")
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=max(1000, len(dataframe) + 100),
                    cols=max(30, len(dataframe.columns) + 5)
                )
            
            # Clear existing data if requested
            if clear_first:
                worksheet.clear()
                time.sleep(1)  # Rate limiting
                
            # Convert DataFrame to list of lists for upload
            data_to_upload = []
            
            # Add headers
            headers = [str(col) for col in dataframe.columns]
            data_to_upload.append(headers)
            
            # Add data rows - IMPROVED data handling
            for _, row in dataframe.iterrows():
                row_data = []
                for value in row:
                    if pd.isna(value):
                        row_data.append('')
                    elif isinstance(value, (int, float, np.integer, np.floating)):
                        # Handle numeric values properly
                        try:
                            numeric_val = float(value)
                            if np.isnan(numeric_val) or np.isinf(numeric_val):
                                row_data.append(0)
                            else:
                                # Convert to appropriate type
                                if isinstance(value, (int, np.integer)):
                                    row_data.append(int(value))
                                else:
                                    row_data.append(float(value))
                        except (ValueError, TypeError, OverflowError):
                            row_data.append(0)
                    else:
                        row_data.append(str(value))
                data_to_upload.append(row_data)
            
            # Upload data - FIXED parameter order
            if data_to_upload:
                try:
                    # Calculate range properly
                    num_cols = len(dataframe.columns)
                    end_col = column_number_to_letter(num_cols)
                    end_row = len(data_to_upload)
                    range_name = f"A1:{end_col}{end_row}"
                    
                    print(f"[INFO] Uploading to range: {range_name}")
                    
                    # FIXED: Use explicit parameter names to avoid confusion
                    worksheet.update(values=data_to_upload, range_name=range_name)
                    time.sleep(2)  # Rate limiting
                    
                    print(f"[SUCCESS] Uploaded {len(dataframe)} rows to {worksheet_name}")
                    return True
                    
                except Exception as upload_error:
                    print(f"[ERROR] Upload failed: {upload_error}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print(f"[WARNING] No data to upload to {worksheet_name}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Upload failed for {worksheet_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

class UnifiedSheetsManager:
    """Advanced Google Sheets manager with formatting and optimization."""
    
    def __init__(self, service_account_file: Optional[str] = None, spreadsheet_id: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Use defaults if not provided
        self.service_account_file = service_account_file or str(CREDENTIALS_FILE)
        self.spreadsheet_id = spreadsheet_id or PRUN_SPREADSHEET_ID
        
        # Validate inputs
        if not self.service_account_file:
            raise ValueError("Service account file path is required")
        if not self.spreadsheet_id:
            raise ValueError("Spreadsheet ID is required")
        
        # Initialize credentials and clients
        self._init_credentials()
        self._init_clients()
        
        # Rate limiting
        self.last_request_time = 0.0
        self.min_interval = 1.5  # Default delay between operations
    
    def _init_credentials(self):
        """Initialize Google Sheets credentials."""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            self.credentials = Credentials.from_service_account_file(
                self.service_account_file, 
                scopes=scopes
            )
            self.logger.info("✅ Google Sheets credentials initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize credentials: {e}")
            raise
    
    def _init_clients(self):
        """Initialize Google Sheets API clients."""
        try:
            # gspread client for easy operations
            self.gspread_client = gspread.authorize(self.credentials)
            self.spreadsheet = RateLimitedSpreadsheet(
                self.gspread_client.open_by_key(self.spreadsheet_id)
            )
            
            # Google Sheets API service for advanced operations
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            
            self.logger.info(f"✅ Connected to spreadsheet: {self.spreadsheet.title}")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize clients: {e}")
            raise
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def upload_dataframe_to_sheet(self, sheet_name: str, df: pd.DataFrame) -> bool:
        """Upload a DataFrame to a Google Sheet - SIMPLIFIED VERSION"""
        try:
            self._rate_limit()
            
            # Get or create worksheet
            try:
                worksheet = self.spreadsheet.worksheet(sheet_name)
            except Exception:
                worksheet = self.spreadsheet.add_worksheet(
                    title=sheet_name, 
                    rows=max(1000, len(df) + 100), 
                    cols=max(26, len(df.columns))
                )
                self.logger.info(f"Created new worksheet: {sheet_name}")
            
            # Clear and prepare data
            worksheet.clear()
            df_clean = df.fillna(0).replace([float('inf'), float('-inf')], 0)
            
            # Convert DataFrame to list of lists
            headers = df_clean.columns.tolist()
            data_rows = []
            
            for _, row in df_clean.iterrows():
                row_list = []
                for value in row:
                    if pd.isna(value):
                        row_list.append(0)
                    elif isinstance(value, (int, float, np.integer, np.floating)):
                        try:
                            numeric_val = float(value)
                            if np.isnan(numeric_val) or np.isinf(numeric_val):
                                row_list.append(0)
                            else:
                                if isinstance(value, (int, np.integer)):
                                    row_list.append(int(value))
                                else:
                                    row_list.append(float(value))
                        except (ValueError, TypeError, OverflowError):
                            row_list.append(0)
                    else:
                        row_list.append(str(value))
                data_rows.append(row_list)
            
            values = [headers] + data_rows
            
            # Upload data - FIXED parameter order
            if values:
                num_cols = len(df.columns)
                end_col = column_number_to_letter(num_cols)
                range_name = f"A1:{end_col}{len(values)}"
                
                # FIXED: Use explicit parameter names
                worksheet.update(
                    range_name=range_name,
                    values=values,
                    value_input_option='RAW'
                )
                
                self.logger.info(f"✅ Updated {sheet_name}: {len(df)} rows, {len(df.columns)} columns")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update {sheet_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

# Legacy compatibility functions
def upload_to_sheets(spreadsheet_id, worksheet_name, dataframe):
    """Legacy function for backward compatibility"""
    manager = SheetsManager()
    if manager.connect():
        return manager.upload_to_sheet(spreadsheet_id, worksheet_name, dataframe)
    return False

def authenticate_sheets():
    """Legacy function for backward compatibility."""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(
            str(CREDENTIALS_FILE), 
            scopes=scopes
        )
        return gspread.authorize(credentials)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise

def get_sheets_service():
    """Get Google Sheets API service."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_file(
        str(CREDENTIALS_FILE), 
        scopes=scopes
    )
    return build('sheets', 'v4', credentials=credentials)