import logging
import json
import os
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from historical_data.config import CREDENTIALS_FILE, CACHE_DIR, TARGET_SPREADSHEET_ID

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def authenticate_sheets():
    """Authenticate with Google Sheets API."""
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error authenticating with Google Sheets: {e}")
        raise

def get_or_create_worksheet(spreadsheet, title, headers=None):
    """Get or create a worksheet in the spreadsheet."""
    try:
        cache_file = os.path.join(CACHE_DIR, 'sheet_metadata.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                metadata = json.load(f)
                logger.info(f"Using cached sheet metadata: {cache_file}")
        else:
            metadata = {}
        
        sheet_id = metadata.get(title)
        if sheet_id:
            try:
                worksheet = spreadsheet.worksheet(title)
                return worksheet, False
            except Exception:
                logger.warning(f"Worksheet {title} not found, creating new one")
        
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=50)
        if headers:
            worksheet.append_row(headers)
        metadata[title] = worksheet.id
        with open(cache_file, 'w') as f:
            json.dump(metadata, f)
        logger.info(f"Created new worksheet: {title}")
        logger.info(f"Updated sheet metadata cache")
        return worksheet, True
    except Exception as e:
        logger.error(f"Error getting or creating worksheet {title}: {e}")
        raise

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

def batch_update_sheets(spreadsheet, updates):
    """Perform batch update on Google Sheets."""
    try:
        service = spreadsheet.spreadsheets()
        # Convert any Timestamp objects to strings
        updates = convert_timestamps_to_strings(updates)
        requests = []
        for update in updates:
            sheet_id = update.get('sheet_id')
            values = update.get('values')
            range_name = update.get('range')
            if sheet_id and values and range_name:
                requests.append({
                    'updateCells': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': range_name.get('startRowIndex', 0),
                            'endRowIndex': range_name.get('endRowIndex'),
                            'startColumnIndex': range_name.get('startColumnIndex', 0),
                            'endColumnIndex': range_name.get('endColumnIndex')
                        },
                        'rows': [
                            {
                                'values': [
                                    {'userEnteredValue': {'stringValue': str(v)} for v in row}
                                    for row in values
                                ]
                            }
                        ],
                        'fields': 'userEnteredValue'
                    }
                })
        
        if requests:
            service.batchUpdate(
                spreadsheetId=spreadsheet.id,
                body={'requests': requests}
            ).execute()
            logger.info(f"Batch updated {len(requests)} sheets")
        else:
            logger.warning("No valid update requests provided")
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        raise

class MarketProcessor:
    def __init__(self, spreadsheet=None):
        self.client = authenticate_sheets()
        self.spreadsheet = spreadsheet or self.client.spreadsheets().get(spreadsheetId=TARGET_SPREADSHEET_ID).execute()
    
    async def process(self, analysis_results):
        """Process analysis results and update sheets."""
        try:
            updates = []
            for exchange, df in analysis_results.items():
                worksheet, _ = get_or_create_worksheet(self.spreadsheet, f"DATA {exchange}")
                if df.empty:
                    logger.warning(f"No data for {exchange}, skipping")
                    continue
                # Convert DataFrame to list of lists for update
                values = [df.columns.tolist()] + df.values.tolist()
                updates.append({
                    'sheet_id': worksheet.id,
                    'values': values,
                    'range': {
                        'startRowIndex': 0,
                        'startColumnIndex': 0,
                        'endRowIndex': len(values),
                        'endColumnIndex': len(values[0])
                    }
                })
            if updates:
                batch_update_sheets(self.spreadsheet, updates)
            logger.info("Google Sheets updated")
        except Exception as e:
            logger.error(f"Error processing analysis results: {e}")
            raise