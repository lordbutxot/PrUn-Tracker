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
    CREDENTIALS_FILE = current_dir / 'prun-profit-42c5889f620d.json'
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
        """Connect to Google Sheets API using credentials from file or environment"""
        try:
            # Define scopes
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Try to use GOOGLE_APPLICATION_CREDENTIALS environment variable first
            import os
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            
            if creds_path and Path(creds_path).exists():
                print(f"[INFO] Using credentials from environment: {creds_path}")
                credentials = Credentials.from_service_account_file(
                    creds_path, 
                    scopes=scopes
                )
            elif self.credentials_file.exists():
                print(f"[INFO] Using credentials file: {self.credentials_file}")
                credentials = Credentials.from_service_account_file(
                    str(self.credentials_file), 
                    scopes=scopes
                )
            else:
                print(f"[ERROR] No credentials found. Set GOOGLE_APPLICATION_CREDENTIALS or provide {self.credentials_file}")
                return False
            
            # Create client
            self.client = gspread.authorize(credentials)
            print("[SUCCESS] Connected to Google Sheets API")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to connect to Google Sheets: {e}")
            import traceback
            traceback.print_exc()
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
                        row_data.append("")
                    elif isinstance(value, (int, float)):
                        row_data.append(value)
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
            self.logger.info(" Google Sheets credentials initialized")
        except Exception as e:
            self.logger.error(f" Failed to initialize credentials: {e}")
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
            
            self.logger.info(f" Connected to spreadsheet: {self.spreadsheet.title}")
        except Exception as e:
            self.logger.error(f" Failed to initialize clients: {e}")
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
                        row_list.append("")
                    elif isinstance(value, (int, float)):
                        row_list.append(value)
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
                
                self.logger.info(f" Updated {sheet_name}: {len(df)} rows, {len(df.columns)} columns")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f" Failed to update {sheet_name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_sheet_id(self, sheet_name: str) -> int:
        """Helper to get the sheet ID from the spreadsheet."""
        spreadsheet = self.sheets_service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id
        ).execute()
        for sheet in spreadsheet['sheets']:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        raise ValueError(f"Sheet {sheet_name} not found")
    
    def add_pie_chart(self, sheet_name: str, title: str, data_range: Dict[str, Any], 
                      position: Dict[str, int], chart_id: Optional[int] = None) -> bool:
        """
        Add a pie chart to a specific sheet.
        
        Args:
            sheet_name: Name of the sheet to add chart to
            title: Chart title
            data_range: Dictionary with 'startRowIndex', 'endRowIndex', 'startColumnIndex', 'endColumnIndex'
            position: Dictionary with 'overlayPosition' containing 'anchorCell' with 'rowIndex' and 'columnIndex'
            chart_id: Optional chart ID (for updating existing chart)
        
        Returns:
            bool: True if successful
        """
        try:
            sheet_id = self._get_sheet_id(sheet_name)
            
            # For pie charts, we need both label column and data column
            # The data_range should span from label column to data column
            chart_spec = {
                "title": title,
                "pieChart": {
                    "legendPosition": "RIGHT_LEGEND",
                    "pieHole": 0.0,  # Set to 0.4 for donut chart
                    "domain": {
                        "sourceRange": {
                            "sources": [{
                                "sheetId": sheet_id,
                                "startRowIndex": data_range['startRowIndex'],
                                "endRowIndex": data_range['endRowIndex'],
                                "startColumnIndex": data_range['startColumnIndex'],
                                "endColumnIndex": data_range['startColumnIndex'] + 1  # Just the label column
                            }]
                        }
                    },
                    "series": {
                        "sourceRange": {
                            "sources": [{
                                "sheetId": sheet_id,
                                "startRowIndex": data_range['startRowIndex'],
                                "endRowIndex": data_range['endRowIndex'],
                                "startColumnIndex": data_range['endColumnIndex'] - 1,  # The numeric data column
                                "endColumnIndex": data_range['endColumnIndex']
                            }]
                        }
                    }
                }
            }
            
            request = {
                "addChart": {
                    "chart": {
                        "spec": chart_spec,
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {
                                    "sheetId": sheet_id,
                                    "rowIndex": position.get('rowIndex', 0),
                                    "columnIndex": position.get('columnIndex', 0)
                                },
                                "offsetXPixels": position.get('offsetXPixels', 0),
                                "offsetYPixels": position.get('offsetYPixels', 0),
                                "widthPixels": position.get('widthPixels', 400),
                                "heightPixels": position.get('heightPixels', 300)
                            }
                        }
                    }
                }
            }
            
            if chart_id is not None:
                request = {
                    "updateChartSpec": {
                        "chartId": chart_id,
                        "spec": chart_spec
                    }
                }
            
            self._rate_limit()
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [request]}
            ).execute()
            
            self.logger.info(f"Added/updated pie chart '{title}' on {sheet_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add pie chart: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def delete_all_charts(self, sheet_name: str) -> bool:
        """Delete all charts from a specific sheet."""
        try:
            sheet_id = self._get_sheet_id(sheet_name)
            
            # Get all charts on the sheet
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id,
                fields="sheets(charts,properties)"
            ).execute()
            
            requests = []
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['sheetId'] == sheet_id:
                    for chart in sheet.get('charts', []):
                        requests.append({
                            "deleteEmbeddedObject": {
                                "objectId": chart['chartId']
                            }
                        })
            
            if requests:
                self._rate_limit()
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"requests": requests}
                ).execute()
                self.logger.info(f"Deleted {len(requests)} charts from {sheet_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete charts: {e}")
            return False

    def apply_data_tab_formatting(self, sheet_name: str, df):
        """
        Applies conditional formatting and header styling to the DATA tab according to business rules.
        Also auto-resizes columns to fit content, except 'Recipe' which is set to double default width.
        Ensures Traded Volume data cells have NO color formatting (header only).
        """
        from googleapiclient.errors import HttpError

        col_idx = {col: idx for idx, col in enumerate(df.columns)}
        requests = []

        sheet_id = self._get_sheet_id(sheet_name)

        # --- Remove all conditional formatting rules for this sheet first ---
        try:
            sheet_metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id, fields="sheets.properties,sheets.conditionalFormats"
            ).execute()
            for sheet in sheet_metadata['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    # conditionalFormats is a list of rules for this sheet
                    cf_rules = sheet.get('conditionalFormats', [])
                    for i in reversed(range(len(cf_rules))):
                        requests.append({
                            "deleteConditionalFormatRule": {
                                "index": i,
                                "sheetId": sheet_id
                            }
                        })
        except Exception as e:
            print(f" Could not clear old conditional formatting: {e}")

        # --- 0. Auto-resize all columns except 'Recipe' ---
        recipe_idx = col_idx.get('Recipe')
        if recipe_idx is not None:
            # Auto-resize before 'Recipe'
            if recipe_idx > 0:
                requests.append({
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": recipe_idx
                        }
                    }
                })
            # Auto-resize after 'Recipe'
            if recipe_idx < len(df.columns) - 1:
                requests.append({
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": recipe_idx + 1,
                            "endIndex": len(df.columns)
                        }
                    }
                })
            # Set 'Recipe' column to fixed width (double the default, e.g., 200px)
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": recipe_idx,
                        "endIndex": recipe_idx + 1
                    },
                    "properties": {
                        "pixelSize": 200  # Double the default (default is ~100)
                    },
                    "fields": "pixelSize"
                }
            })
        else:
            # Fallback: auto-resize all if 'Recipe' not found
            requests.append({
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": len(df.columns)
                    }
                }
            })

        # --- 1. Header background colors ---
        informative_headers = [
            'Material Name', 'Ticker', 'Category', 'Tier', 'Recipe',
            'Amount per Recipe', 'Weight', 'Volume'
        ]
        actual_data_headers = [
            'Ask Price', 'Bid Price', 'Input Cost per Unit', 'Input Cost per Stack',
            'Profit per Unit', 'Profit per Stack', 'ROI Ask %', 'ROI Bid %',
            'Supply', 'Demand', 'Traded Volume'
        ]
        formula_headers = [
            'Saturation', 'Market Cap', 'Liquidity Ratio',
            'Investment Score', 'Risk Level', 'Volatility'
        ]

        informative_color = {"red": 0.2, "green": 0.4, "blue": 0.8}
        actual_data_color = {"red": 0.2, "green": 0.7, "blue": 0.2}
        formula_color = {"red": 0.85, "green": 0.6, "blue": 0.15}

        def add_header_format(col_names, color):
            for col in col_names:
                if col in col_idx:
                    idx = col_idx[col]
                    requests.append({
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                                "startColumnIndex": idx,
                                "endColumnIndex": idx + 1
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": color,
                                    "horizontalAlignment": "CENTER",
                                    "textFormat": {
                                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                                        "bold": True
                                    }
                                }
                            },
                            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                        }
                    })

        add_header_format(informative_headers, informative_color)
        add_header_format(actual_data_headers, actual_data_color)
        add_header_format(formula_headers, formula_color)

        # --- 2. Profits per Unit/Stack: green (high), yellow (avg), red (negative) ---
        for col in ['Profit per Unit', 'Profit per Stack']:
            if col in col_idx:
                c = col_idx[col]
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": c,
                                "endColumnIndex": c + 1
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_LESS",
                                    "values": [{"userEnteredValue": "0"}]
                                },
                                "format": {"backgroundColor": {"red": 1, "green": 0.2, "blue": 0.2}}
                            }
                        },
                        "index": 0
                    }
                })
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": c,
                                "endColumnIndex": c + 1
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_BETWEEN",
                                    "values": [{"userEnteredValue": "0"}, {"userEnteredValue": "1000"}]
                                },
                                "format": {"backgroundColor": {"red": 1, "green": 1, "blue": 0.4}}
                            }
                        },
                        "index": 1
                    }
                })
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": c,
                                "endColumnIndex": c + 1
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_GREATER_THAN_EQ",
                                    "values": [{"userEnteredValue": "1000"}]
                                },
                                "format": {"backgroundColor": {"red": 0.2, "green": 1, "blue": 0.2}}
                            }
                        },
                        "index": 2
                    }
                })

        # --- 3. ROI columns: green (>=75), yellow (7.5-75), red (<7.5 or negative) ---
        for col in ['ROI Ask %', 'ROI Bid %']:
            if col in col_idx:
                c = col_idx[col]
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": c,
                                "endColumnIndex": c + 1
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_LESS",
                                    "values": [{"userEnteredValue": "8"}]
                                },
                                "format": {"backgroundColor": {"red": 1, "green": 0.2, "blue": 0.2}}
                            }
                        },
                        "index": 0
                    }
                })
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": c,
                                "endColumnIndex": c + 1
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_BETWEEN",
                                    "values": [{"userEnteredValue": "8"}, {"userEnteredValue": "75"}]
                                },
                                "format": {"backgroundColor": {"red": 1, "green": 1, "blue": 0.4}}
                            }
                        },
                        "index": 1
                    }
                })
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": c,
                                "endColumnIndex": c + 1
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_GREATER_THAN_EQ",
                                    "values": [{"userEnteredValue": "75"}]
                                },
                                "format": {"backgroundColor": {"red": 0.2, "green": 1, "blue": 0.2}}
                            }
                        },
                        "index": 2
                    }
                })

        # --- 4. Supply, Demand: brown/red if 0 ---
        # Traded Volume data cells: NO formatting (skip conditional formatting for this column)
        for col in ['Supply', 'Demand']:
            if col in col_idx:
                c = col_idx[col]
                requests.append({
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": sheet_id,
                                "startRowIndex": 1,
                                "startColumnIndex": c,
                                "endColumnIndex": c + 1
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "NUMBER_EQ",
                                    "values": [{"userEnteredValue": "0"}]
                                },
                                "format": {
                                    "backgroundColor": {"red": 0.6, "green": 0.3, "blue": 0.1}
                                }
                            }
                        },
                        "index": 0
                    }
                })
        # --- Traded Volume: header only, no data cell formatting ---
        # (No conditional formatting rule for Traded Volume data cells)

        # --- 5. Saturation: red if >=100, yellow if 60-99.99, green if <60 ---
        if 'Saturation' in col_idx:
            c = col_idx['Saturation']
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_GREATER_THAN_EQ",
                                "values": [{"userEnteredValue": "100"}]
                            },
                            "format": {"backgroundColor": {"red": 1, "green": 0.2, "blue": 0.2}}
                        }
                    },
                    "index": 0
                }
            })
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_BETWEEN",
                                "values": [{"userEnteredValue": "60"}, {"userEnteredValue": "99"}]
                            },
                            "format": {"backgroundColor": {"red": 1, "green": 1, "blue": 0.4}}
                        }
                    },
                    "index": 1
                }
            })
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_LESS",
                                "values": [{"userEnteredValue": "60"}]
                            },
                            "format": {"backgroundColor": {"red": 0.2, "green": 1, "blue": 0.2}}
                        }
                    },
                    "index": 2
                }
            })

        # --- 6. Investment Score: 4-color scale from red (0) to green (100) ---
        if 'Investment Score' in col_idx:
            c = col_idx['Investment Score']
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1
                        }],
                        "gradientRule": {
                            "minpoint": {"color": {"red": 1, "green": 0.2, "blue": 0.2}, "type": "NUMBER", "value": "0"},
                            "midpoint": {"color": {"red": 1, "green": 1, "blue": 0.4}, "type": "NUMBER", "value": "50"},
                            "maxpoint": {"color": {"red": 0.2, "green": 1, "blue": 0.2}, "type": "NUMBER", "value": "100"}
                        }
                    },
                    "index": 0
                }
            })

        # --- 7. Risk Level: text color (not background) - Green for Low, Yellow for Medium, Red for High ---
        if 'Risk Level' in col_idx:
            c = col_idx['Risk Level']
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Low"}]
                            },
                            "format": {"textFormat": {"foregroundColor": {"red": 0.2, "green": 0.7, "blue": 0.2}, "bold": True}}
                        }
                    },
                    "index": 0
                }
            })
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Medium"}]
                            },
                            "format": {"textFormat": {"foregroundColor": {"red": 1, "green": 0.7, "blue": 0.2}, "bold": True}}
                        }
                    },
                    "index": 1
                }
            })
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "startColumnIndex": c,
                            "endColumnIndex": c + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "High"}]
                            },
                            "format": {"textFormat": {"foregroundColor": {"red": 1, "green": 0.2, "blue": 0.2}, "bold": True}}
                        }
                    },
                    "index": 2
                }
            })

        # --- Send batchUpdate request ---
        if requests:
            try:
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={"requests": requests}
                ).execute()
                if hasattr(self, "logger"):
                    self.logger.info(f" Applied formatting to {sheet_name}")
                else:
                    print(f" Applied formatting to {sheet_name}")
            except HttpError as e:
                if hasattr(self, "logger"):
                    self.logger.error(f" Failed to apply formatting: {e}")
                print(e)

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