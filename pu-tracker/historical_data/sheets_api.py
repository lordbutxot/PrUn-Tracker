import logging
import json
import os
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread
from historical_data.config import CREDENTIALS_FILE, CACHE_DIR, TARGET_SPREADSHEET_ID
from historical_data.formatting_config import get_performance_color, FORMATTING_CONFIG

logger = logging.getLogger(__name__)

def authenticate_sheets():
    """Authenticate with Google Sheets API using service account."""
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    try:
        # Use service account authentication instead of OAuth
        from google.oauth2.service_account import Credentials
        
        # Load service account credentials
        credentials = Credentials.from_service_account_file(
            CREDENTIALS_FILE, 
            scopes=SCOPES
        )
        
        # Use gspread client for easier spreadsheet operations
        client = gspread.authorize(credentials)
        return client
        
    except Exception as e:
        print(f"Authentication failed: {e}")
        raise

def get_or_create_worksheet(spreadsheet, sheet_name):
    """Get or create a worksheet in the spreadsheet using gspread."""
    try:
        # Try to get existing worksheet
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            return worksheet
        except gspread.WorksheetNotFound:
            # Create new worksheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            return worksheet
            
    except Exception as e:
        print(f"Error getting/creating worksheet {sheet_name}: {e}")
        raise
        
        new_sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        logger.info(f"Created new sheet: {sheet_name}")
        return new_sheet_id, None
        
    except Exception as e:
        logger.error(f"Error getting/creating worksheet {sheet_name}: {e}")
        return None, None

def upload_dataframe_to_sheet(service, spreadsheet_id, sheet_name, df):
    """Upload a DataFrame to a Google Sheet."""
    try:
        # Convert DataFrame to values list
        values = [df.columns.tolist()] + df.values.tolist()
        
        # Convert any special data types to strings
        for i, row in enumerate(values):
            values[i] = [str(cell) if pd.isna(cell) else cell for cell in row]
        
        # Clear existing content
        range_name = f"{sheet_name}!A:Z"
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        # Upload new data
        body = {
            'values': values
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info(f"Uploaded {len(df)} rows to {sheet_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading to {sheet_name}: {e}")
        return False

class SheetsFormatter:
    """Handle Google Sheets formatting and styling."""
    
    def __init__(self, service=None):
        self.service = service or authenticate_sheets()
    
    def get_column_headers(self, spreadsheet_id, sheet_name):
        """Get the column headers from the sheet to determine column positions."""
        try:
            range_name = f"{sheet_name}!1:1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            headers = result.get('values', [[]])[0] if result.get('values') else []
            logger.info(f"Found headers in {sheet_name}: {headers}")
            return headers
        except Exception as e:
            logger.error(f"Error getting headers for {sheet_name}: {e}")
            return []
    
    def find_column_indices(self, headers):
        """Find column indices for different data types."""
        indices = {
            'price_columns': [],
            'percentage_columns': [],
            'integer_columns': [],
            'roi_columns': [],
            'score_columns': []
        }
        
        # Price/Cost columns (should be formatted as currency/numbers with 2 decimals)
        price_keywords = ['price', 'cost', 'profit']
        for i, header in enumerate(headers):
            if any(keyword in header.lower() for keyword in price_keywords):
                indices['price_columns'].append(i)
        
        # ROI columns (should be formatted as percentages)
        roi_keywords = ['roi']
        for i, header in enumerate(headers):
            if any(keyword in header.lower() for keyword in roi_keywords):
                indices['roi_columns'].append(i)
                indices['percentage_columns'].append(i)
        
        # Score columns (1 decimal place)
        score_keywords = ['risk', 'viability', 'investment score', 'score']
        for i, header in enumerate(headers):
            if any(keyword in header.lower() for keyword in score_keywords):
                indices['score_columns'].append(i)
        
        # Integer columns
        integer_keywords = ['supply', 'demand', 'traded', 'tier']
        for i, header in enumerate(headers):
            if any(keyword in header.lower() for keyword in integer_keywords):
                indices['integer_columns'].append(i)
        
        logger.info(f"Column indices found: {indices}")
        return indices
    
    def apply_header_formatting(self, spreadsheet_id, sheet_name):
        """Apply formatting to header row."""
        sheet_id = self._get_sheet_id(spreadsheet_id, sheet_name)
        if sheet_id is None:
            return False
        
        headers = self.get_column_headers(spreadsheet_id, sheet_name)
        total_cols = len(headers)
        
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": total_cols
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.2,
                                "green": 0.2,
                                "blue": 0.2
                            },
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0
                                },
                                "fontSize": 11,
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                }
            }
        ]
        
        return self._execute_batch_update(spreadsheet_id, requests)
    
    def apply_conditional_formatting(self, spreadsheet_id, sheet_name, data_rows):
        """Apply conditional formatting based on values."""
        sheet_id = self._get_sheet_id(spreadsheet_id, sheet_name)
        if sheet_id is None:
            return False
        
        headers = self.get_column_headers(spreadsheet_id, sheet_name)
        requests = []
        
        # Find ROI columns dynamically
        roi_columns = [i for i, header in enumerate(headers) if 'roi' in header.lower()]
        
        for col_index in roi_columns:
            # Green for positive ROI (>10%)
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_rows + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_GREATER",
                                "values": [{"userEnteredValue": "10"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.8,
                                    "green": 1.0,
                                    "blue": 0.8
                                }
                            }
                        }
                    },
                    "index": len(requests)
                }
            })
            
            # Red for negative ROI (<0%)
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_rows + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_LESS",
                                "values": [{"userEnteredValue": "0"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 1.0,
                                    "green": 0.8,
                                    "blue": 0.8
                                }
                            }
                        }
                    },
                    "index": len(requests)
                }
            })
        
        # Find Investment Score columns
        investment_columns = [i for i, header in enumerate(headers) if 'investment' in header.lower() and 'score' in header.lower()]
        
        for col_index in investment_columns:
            # Green for high investment scores (>7)
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_rows + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_GREATER",
                                "values": [{"userEnteredValue": "7"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.7,
                                    "green": 1.0,
                                    "blue": 0.7
                                }
                            }
                        }
                    },
                    "index": len(requests)
                }
            })
            
            # Red for low investment scores (<3)
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_rows + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_LESS",
                                "values": [{"userEnteredValue": "3"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 1.0,
                                    "green": 0.7,
                                    "blue": 0.7
                                }
                            }
                        }
                    },
                    "index": len(requests)
                }
            })
        
        # Find Risk columns (inverted: low risk = green)
        risk_columns = [i for i, header in enumerate(headers) if header.lower() == 'risk']
        
        for col_index in risk_columns:
            # Green for low risk (<3)
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_rows + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_LESS",
                                "values": [{"userEnteredValue": "3"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.8,
                                    "green": 1.0,
                                    "blue": 0.8
                                }
                            }
                        }
                    },
                    "index": len(requests)
                }
            })
            
            # Red for high risk (>7)
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_rows + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_GREATER",
                                "values": [{"userEnteredValue": "7"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 1.0,
                                    "green": 0.8,
                                    "blue": 0.8
                                }
                            }
                        }
                    },
                    "index": len(requests)
                }
            })
        
        return self._execute_batch_update(spreadsheet_id, requests)
    
    def apply_column_formatting(self, spreadsheet_id, sheet_name, total_rows, total_cols):
        """Apply general column formatting to ALL columns dynamically."""
        sheet_id = self._get_sheet_id(spreadsheet_id, sheet_name)
        if sheet_id is None:
            return False
        
        headers = self.get_column_headers(spreadsheet_id, sheet_name)
        column_indices = self.find_column_indices(headers)
        
        requests = []
        
        # Auto-resize ALL columns
        requests.append({
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": total_cols
                }
            }
        })
        
        # Freeze header row
        requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        })
        
        # Format price/cost columns (2 decimal places)
        for col in column_indices['price_columns']:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": total_rows + 1,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "#,##0.00"
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
        
        # Format ROI columns as percentages
        for col in column_indices['roi_columns']:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": total_rows + 1,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "PERCENT",
                                "pattern": "0.00%"
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
        
        # Format score columns (1 decimal place)
        for col in column_indices['score_columns']:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": total_rows + 1,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "#,##0.0"
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
        
        # Format integer columns (no decimals)
        for col in column_indices['integer_columns']:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": total_rows + 1,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": {
                                "type": "NUMBER",
                                "pattern": "#,##0"
                            }
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
        
        return self._execute_batch_update(spreadsheet_id, requests)
    
    def _get_sheet_id(self, spreadsheet_id, sheet_name):
        """Get the sheet ID for a given sheet name."""
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return None
        except Exception as e:
            logger.error(f"Error getting sheet ID for {sheet_name}: {e}")
            return None
    
    def _execute_batch_update(self, spreadsheet_id, requests):
        """Execute a batch update request."""
        try:
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error executing batch update: {e}")
            return False

class AdvancedSheetsFormatter(SheetsFormatter):
    """Enhanced formatter with performance-based coloring and advanced features."""
    
    def apply_performance_based_formatting(self, spreadsheet_id, sheet_name, df):
        """Apply performance-based cell coloring to the entire dataset."""
        sheet_id = self._get_sheet_id(spreadsheet_id, sheet_name)
        if sheet_id is None:
            return False
        
        headers = self.get_column_headers(spreadsheet_id, sheet_name)
        requests = []
        
        # Find performance columns
        performance_columns = {
            'roi_ask': next((i for i, h in enumerate(headers) if 'roi' in h.lower() and 'ask' in h.lower()), None),
            'roi_bid': next((i for i, h in enumerate(headers) if 'roi' in h.lower() and 'bid' in h.lower()), None),
            'investment_score': next((i for i, h in enumerate(headers) if 'investment' in h.lower() and 'score' in h.lower()), None),
            'risk': next((i for i, h in enumerate(headers) if h.lower() == 'risk'), None),
            'viability': next((i for i, h in enumerate(headers) if h.lower() == 'viability'), None),
        }
        
        # Apply conditional formatting for each performance metric
        for metric, col_index in performance_columns.items():
            if col_index is None:
                continue
            self._add_performance_formatting(requests, sheet_id, col_index, len(df), metric.replace('_', ' '))
        
        return self._execute_batch_update(spreadsheet_id, requests)
    
    def _add_performance_formatting(self, requests, sheet_id, col_index, data_rows, metric_type):
        """Add performance-based conditional formatting for a column."""
        colors = FORMATTING_CONFIG['colors']
        
        if metric_type in ['roi ask', 'roi bid']:
            metric_key = 'roi'
        elif 'investment' in metric_type:
            metric_key = 'investment_score'
        else:
            metric_key = metric_type
        
        thresholds = FORMATTING_CONFIG['thresholds'].get(metric_key, {})
        
        # Create conditional formatting rules
        if metric_key == 'risk':  # Risk is inverted
            rules = [
                (f"<={thresholds.get('excellent', 3)}", colors['excellent']),
                (f"<={thresholds.get('good', 5)}", colors['good']),
                (f"<={thresholds.get('neutral', 7)}", colors['neutral']),
                (f"<={thresholds.get('poor', 8.5)}", colors['poor']),
                (f">{thresholds.get('poor', 8.5)}", colors['bad']),
            ]
        else:  # Higher is better
            rules = [
                (f">={thresholds.get('excellent', 50)}", colors['excellent']),
                (f">={thresholds.get('good', 20)}", colors['good']),
                (f">={thresholds.get('neutral', 5)}", colors['neutral']),
                (f">={thresholds.get('poor', 0)}", colors['poor']),
                (f"<{thresholds.get('poor', 0)}", colors['bad']),
            ]
        
        for i, (condition, color) in enumerate(rules):
            condition_type, value = self._parse_condition(condition)
            
            requests.append({
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_rows + 1,
                            "startColumnIndex": col_index,
                            "endColumnIndex": col_index + 1
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": condition_type,
                                "values": [{"userEnteredValue": str(value)}]
                            },
                            "format": {
                                "backgroundColor": color,
                                "textFormat": {
                                    "bold": True if color == colors['excellent'] else False
                                }
                            }
                        }
                    },
                    "index": len(requests)
                }
            })
    
    def _parse_condition(self, condition_str):
        """Parse condition string into Google Sheets condition type and value."""
        if condition_str.startswith('>='):
            return "NUMBER_GREATER_THAN_EQ", float(condition_str[2:])
        elif condition_str.startswith('<='):
            return "NUMBER_LESS_THAN_EQ", float(condition_str[2:])
        elif condition_str.startswith('>'):
            return "NUMBER_GREATER", float(condition_str[1:])
        elif condition_str.startswith('<'):
            return "NUMBER_LESS", float(condition_str[1:])
        else:
            return "NUMBER_EQUAL", float(condition_str)

def format_exchange_sheet(spreadsheet_id, sheet_name, data_rows):
    """Apply all formatting to an exchange sheet."""
    try:
        formatter = SheetsFormatter()
        
        # Apply all formatting
        success = True
        success &= formatter.apply_header_formatting(spreadsheet_id, sheet_name)
        success &= formatter.apply_conditional_formatting(spreadsheet_id, sheet_name, data_rows)
        
        # Get actual column count from headers
        headers = formatter.get_column_headers(spreadsheet_id, sheet_name)
        total_cols = len(headers)
        success &= formatter.apply_column_formatting(spreadsheet_id, sheet_name, data_rows, total_cols)
        
        if success:
            logger.info(f"✅ Complete formatting applied to {sheet_name} ({data_rows} rows, {total_cols} columns)")
        else:
            logger.warning(f"⚠️ Some formatting failed for {sheet_name}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error formatting {sheet_name}: {e}")
        return False

def format_exchange_sheet_advanced(spreadsheet_id, sheet_name, df):
    """Apply comprehensive advanced formatting to an exchange sheet."""
    try:
        formatter = AdvancedSheetsFormatter()
        data_rows = len(df)
        
        success = True
        success &= formatter.apply_header_formatting(spreadsheet_id, sheet_name)
        success &= formatter.apply_performance_based_formatting(spreadsheet_id, sheet_name, df)
        success &= formatter.apply_column_formatting(spreadsheet_id, sheet_name, data_rows, len(df.columns))
        
        if success:
            logger.info(f"✅ Complete advanced formatting applied to {sheet_name}")
        else:
            logger.warning(f"⚠️ Some formatting failed for {sheet_name}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Error applying advanced formatting to {sheet_name}: {e}")
        return False

# Legacy compatibility functions (keeping your existing functions)
def convert_timestamps_to_strings(data):
    """Convert pandas Timestamp objects to strings in a dictionary or DataFrame."""
    if isinstance(data, pd.DataFrame):
        for col in data.columns:
            if data[col].dtype == 'datetime64[ns]' or data[col].dtype == 'datetime64[ns, UTC]':
                data[col] = data[col].astype(str)
        return data
    elif isinstance(data, dict):
        return {k: convert_timestamps_to_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_timestamps_to_strings(item) for item in data]
    elif isinstance(data, pd.Timestamp):
        return data.isoformat()
    return data

class MarketProcessor:
    def __init__(self):
        self.service = authenticate_sheets()
    
    def process(self, analysis_results):
        """Process analysis results and update sheets."""
        try:
            for exchange, df in analysis_results.items():
                sheet_name = f"DATA {exchange}"
                
                if df.empty:
                    logger.warning(f"No data for {exchange}, skipping")
                    continue
                
                # Get or create worksheet
                sheet_id, _ = get_or_create_worksheet(self.service, TARGET_SPREADSHEET_ID, sheet_name)
                if sheet_id is None:
                    logger.error(f"Failed to get/create sheet for {exchange}")
                    continue
                
                # Upload data
                success = upload_dataframe_to_sheet(self.service, TARGET_SPREADSHEET_ID, sheet_name, df)
                if success:
                    logger.info(f"✅ Updated {sheet_name} with {len(df)} rows")
                else:
                    logger.error(f"❌ Failed to update {sheet_name}")
                    
            logger.info("Google Sheets processing completed")
        except Exception as e:
            logger.error(f"Error processing analysis results: {e}")
            raise