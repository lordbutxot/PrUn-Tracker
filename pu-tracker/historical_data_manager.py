import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime, timedelta, timezone
import time
import os
import re
import sqlite3
from gspread_formatting import CellFormat, NumberFormat
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import gspread.utils
import gspread_formatting

# --- Logging setup ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
SOURCE_SPREADSHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
TARGET_SPREADSHEET_ID = "1JhIzAhi435loaUxBog2qeJzYAKWPdmlL1GVDBm0lWiQ"
CREDENTIALS_FILE = 'prun-profit-7e0c3bafd690.json'
DB_PATH = 'data/prosperous_universe.db'
CSV_DIR = 'data/historical_csv'
UNIFIED_REPORT_TAB = "Unified Analysis"
EXPECTED_EXCHANGES = {'AI1', 'IC1', 'NC1', 'NC2', 'CI1', 'CI2'}
DEFAULT_ROWS = 100
DEFAULT_COLS = 14
RETENTION_DAYS = 30
MAX_RETRIES = 5
INITIAL_BACKOFF = 10
API_DELAY = [0.5]  # Start at 0.5s, cap at 3.0s
MAX_WORKERS = 1
CHUNK_SIZE = 1000

# --- Data Types for Pandas ---
DTYPES = {
    'Timestamp': 'string',
    'Exchange': 'string',
    'Ticker': 'string',
    'Product': 'string',
    'Input_Cost': 'float64',
    'Ask_Price': 'float64',
    'Bid_Price': 'float64',
    'Supply': 'float64',
    'Demand': 'float64',
    'Traded': 'float64',
    'Saturation': 'float64',
    'Profit_Ask': 'float64',
    'Profit_Bid': 'float64',
    'ROI_Ask': 'float64',
    'ROI_Bid': 'float64',
    'Recommendation': 'string',
    'Source': 'string'
}

# --- Version Check ---
def check_gspread_version():
    """Check gspread and gspread-formatting versions for compatibility."""
    required_gspread_version = "5.7.0"
    recommended_gspread_version = "5.12.0"  # For batch_get support
    required_formatting_version = "0.4.0"  # Earliest version with __version__
    recommended_formatting_version = "1.2.0"  # For CellFormat.to_dict support
    gspread_version = gspread.__version__

    # Check gspread version
    if gspread_version < required_gspread_version:
        logger.warning(f"gspread version {gspread_version} is outdated. Upgrade to {required_gspread_version} or higher: pip install gspread>=5.12.0")
    elif gspread_version < recommended_gspread_version:
        logger.warning(f"gspread version {gspread_version} lacks batch_get. Upgrade to {recommended_gspread_version} for better performance: pip install gspread>=5.12.0")
    else:
        logger.info(f"gspread version {gspread_version} is compatible")

    # Check gspread-formatting version
    try:
        formatting_version = gspread_formatting.__version__
        if formatting_version < required_formatting_version:
            logger.warning(f"gspread-formatting version {formatting_version} is outdated. Upgrade to {required_formatting_version} or higher: pip install gspread-formatting>=1.2.0")
        elif formatting_version < recommended_formatting_version:
            logger.warning(f"gspread-formatting version {formatting_version} lacks CellFormat.to_dict. Upgrade to {recommended_formatting_version} for better performance: pip install gspread-formatting>=1.2.0")
        else:
            logger.info(f"gspread-formatting version {formatting_version} is compatible")
    except AttributeError:
        logger.warning(f"gspread-formatting version is unknown (likely <{required_formatting_version}). Upgrade to {recommended_formatting_version} for compatibility and performance: pip install gspread-formatting>=1.2.0")

# --- SQLite setup ---
def init_db():
    """Initialize SQLite database and migrate schema if needed."""
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data (
            Timestamp TEXT,
            Exchange TEXT,
            Ticker TEXT,
            Product TEXT,
            Input_Cost REAL,
            Ask_Price REAL,
            Bid_Price REAL,
            Supply REAL,
            Demand REAL,
            Traded REAL,
            Saturation REAL,
            Profit_Ask REAL,
            Profit_Bid REAL,
            ROI_Ask REAL,
            ROI_Bid REAL,
            Recommendation TEXT,
            Source TEXT,
            UNIQUE(Timestamp, Exchange, Ticker)
        )
    ''')
    cursor.execute("PRAGMA table_info(raw_data)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'Recommendation' not in columns:
        logger.info("Adding Recommendation column to raw_data table")
        cursor.execute("ALTER TABLE raw_data ADD COLUMN Recommendation TEXT")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS last_processed (
            key TEXT PRIMARY KEY,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_last_processed_timestamp():
    """Get the last processed timestamp from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp FROM last_processed WHERE key = 'last_run'")
    result = cursor.fetchone()
    conn.close()
    if result:
        return pd.to_datetime(result[0], format='%Y-%m-%d %H:%M:%S')
    return None

def set_last_processed_timestamp(timestamp):
    """Update the last processed timestamp in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO last_processed (key, timestamp) VALUES (?, ?)",
                  ('last_run', timestamp.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def authenticate_sheets():
    """Authenticate with Google Sheets and return the client with rate limit handling."""
    for attempt in range(MAX_RETRIES):
        try:
            scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
            client = gspread.authorize(creds)
            logger.info("✅ Authenticated with Google Sheets")
            return client
        except gspread.exceptions.APIError as e:
            error_message = str(e)
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            logger.debug(f"APIError in authenticate_sheets: {error_message}")
            if status_code == 429:
                backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                logger.warning(f"429 error in authenticate_sheets, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(backoff_time)
            else:
                logger.error(f"❌ Authentication error: {error_message}")
                raise
        except Exception as e:
            logger.error(f"❌ Unexpected authentication error: {e}")
            raise
    raise gspread.exceptions.APIError("Max retries reached for authentication")

def get_valid_sheet_name(name):
    """Ensure sheet name is valid (max 100 chars, no invalid chars)."""
    name = re.sub(r'[\\\/:*?"<>|]', '_', name)
    return name[:100]

def batch_get_sheets(spreadsheet, sheet_names):
    """Batch read multiple sheets from a spreadsheet."""
    batch_data = {}
    for attempt in range(MAX_RETRIES):
        try:
            # Check if batch_get is available (gspread >= 5.12.0)
            if hasattr(spreadsheet, 'batch_get'):
                ranges = [f"{sheet_name}!A1:Z" for sheet_name in sheet_names]
                response = spreadsheet.batch_get(ranges)
                for sheet_name, values in zip(sheet_names, response):
                    batch_data[sheet_name] = values
                    logger.debug(f"Fetched {sheet_name} with {len(values)} rows using batch_get")
            else:
                logger.warning("batch_get not available in gspread version. Falling back to individual sheet reads. Upgrade to gspread>=5.12.0 for better performance.")
                for sheet_name in sheet_names:
                    worksheet = spreadsheet.worksheet(sheet_name)
                    batch_data[sheet_name] = worksheet.get_all_values()
                    logger.debug(f"Fetched {sheet_name} with {len(batch_data[sheet_name])} rows")
                    time.sleep(API_DELAY[0])
            API_DELAY[0] = max(API_DELAY[0] / 1.5, 0.5)
            return batch_data
        except gspread.exceptions.APIError as e:
            error_message = str(e)
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            logger.debug(f"APIError in batch_get_sheets: {error_message}")
            if status_code == 429:
                backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                logger.warning(f"429 error in batch_get_sheets, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(backoff_time)
            else:
                logger.error(f"Error in batch_get_sheets: {error_message}")
                raise
    raise gspread.exceptions.APIError("Max retries reached for batch_get_sheets")

def cell_format_to_dict(cell_format):
    """Convert CellFormat to dictionary for Google Sheets API, with fallback for older gspread-formatting versions."""
    if hasattr(cell_format, 'to_dict'):
        return cell_format.to_dict()
    else:
        logger.warning("CellFormat.to_dict not available in gspread-formatting version. Using manual conversion. Upgrade to gspread-formatting>=1.2.0 for better performance.")
        format_dict = {}
        if cell_format.numberFormat:
            format_dict['numberFormat'] = {
                'type': cell_format.numberFormat.type,
                'pattern': cell_format.numberFormat.pattern
            }
        return format_dict

def batch_update_sheets(spreadsheet, updates):
    """Batch update multiple worksheets with data and formatting."""
    for attempt in range(MAX_RETRIES):
        try:
            batch_requests = []
            for sheet_name, (data_df, headers, formatting_ranges) in updates.items():
                worksheet = spreadsheet.worksheet(sheet_name)
                values = [headers] + data_df[headers].values.tolist()
                # Clear and update data in one batch request
                batch_requests.append({
                    "updateCells": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 0,
                            "startColumnIndex": 0
                        },
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {
                                            "stringValue": str(v)
                                        } if isinstance(v, str) else {
                                            "numberValue": float(v)
                                        } if isinstance(v, (int, float)) else {
                                            "stringValue": ""
                                        }
                                    } for v in row
                                ]
                            } for row in values
                        ],
                        "fields": "userEnteredValue"
                    }
                })
                if formatting_ranges:
                    for range_name, cell_format in formatting_ranges:
                        rowcol = gspread.utils.a1_to_rowcol(range_name)
                        logger.debug(f"Processing range {range_name}: rowcol={rowcol}")
                        # Handle single-column ranges (e.g., A2:A) with only start_row, start_col
                        end_row = rowcol[2] - 1 if len(rowcol) > 2 and rowcol[2] else None
                        end_col = rowcol[3] - 1 if len(rowcol) > 3 and rowcol[3] else None
                        batch_requests.append({
                            "repeatCell": {
                                "range": {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": rowcol[0] - 1,
                                    "startColumnIndex": rowcol[1] - 1,
                                    "endRowIndex": end_row,
                                    "endColumnIndex": end_col
                                },
                                "cell": {
                                    "userEnteredFormat": cell_format_to_dict(cell_format)
                                },
                                "fields": "userEnteredFormat"
                            }
                        })
            spreadsheet.batch_update({"requests": batch_requests})
            for sheet_name in updates:
                logger.info(f"Successfully updated {sheet_name}")
            API_DELAY[0] = max(API_DELAY[0] / 1.5, 0.5)
            return
        except gspread.exceptions.APIError as e:
            error_message = str(e)
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            logger.debug(f"APIError in batch_update_sheets: {error_message}")
            if status_code == 429:
                backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                logger.warning(f"429 error in batch_update_sheets, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(backoff_time)
            else:
                logger.error(f"Error in batch_update_sheets: {error_message}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error in batch_update_sheets: {e}")
            raise
    raise gspread.exceptions.APIError("Max retries reached for batch_update_sheets")

def get_or_create_worksheet(spreadsheet, sheet_name, headers=None, rows=DEFAULT_ROWS, cols=DEFAULT_COLS, existing_sheets=None):
    """Returns a worksheet with the given name. Creates it if it doesn't exist."""
    if existing_sheets is None:
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        logger.debug(f"Cached worksheet titles: {existing_sheets}")
    
    for attempt in range(MAX_RETRIES):
        try:
            if sheet_name in existing_sheets:
                worksheet = spreadsheet.worksheet(sheet_name)
                logger.info(f"Found worksheet: {sheet_name}")
                return worksheet
            else:
                logger.debug(f"Worksheet {sheet_name} not found in cached titles, attempting to create")
                try:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=rows, cols=cols)
                    logger.info(f"Created worksheet: {sheet_name}")
                    if headers:
                        worksheet.update(values=[headers], range_name='A1')
                    return worksheet
                except gspread.exceptions.APIError as e:
                    error_message = str(e)
                    status_code = getattr(getattr(e, 'response', None), 'status_code', None)
                    logger.debug(f"APIError in creating worksheet: {error_message}")
                    if status_code == 429:
                        backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                        API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                        logger.warning(f"429 error creating worksheet {sheet_name}, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"Failed to create worksheet {sheet_name}: {error_message}")
                        raise
        except gspread.exceptions.APIError as e:
            error_message = str(e)
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            logger.debug(f"APIError in accessing worksheet: {error_message}")
            if status_code == 429:
                backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                logger.warning(f"429 error accessing worksheet {sheet_name}, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(backoff_time)
            else:
                logger.error(f"Failed to access worksheet {sheet_name}: {error_message}")
                raise
    raise gspread.exceptions.APIError(f"Max retries reached for worksheet {sheet_name}")

def normalize_column_name(col):
    """Normalize column names: replace spaces/parentheses with underscore."""
    if not isinstance(col, str):
        col = str(col)
    normalized = re.sub(r'[\s()]+', '_', col.strip())
    normalized = re.sub(r'_+', '_', normalized).strip('_')
    return normalized if normalized else f'Column_{hash(str(col)) % 10000}'

def set_recommendation(row):
    """Assign Buy/Sell/Neutral recommendation based on ROI and market conditions."""
    if pd.notnull(row['ROI_Ask']) and row['ROI_Ask'] > 1000 and row['Supply'] > 0:
        return 'Buy'
    elif pd.notnull(row['ROI_Bid']) and row['ROI_Bid'] > 1000 and row['Demand'] > 0:
        return 'Sell'
    return 'Neutral'

def load_source_data(spreadsheet, last_timestamp=None):
    """Load data from Unified Analysis and DATA {cx} sheets."""
    dfs = []
    expected_cols = list(DTYPES.keys())
    current_timestamp = datetime.now(timezone.utc)
    timestamp_str = current_timestamp.strftime('%Y-%m-%d %H:%M:%S')

    # Batch read all relevant sheets
    sheet_names = [UNIFIED_REPORT_TAB] + [ws.title for ws in spreadsheet.worksheets() if ws.title.startswith("DATA ")]
    batch_data = batch_get_sheets(spreadsheet, sheet_names)

    # Process Unified Analysis tab
    source_type = 'Unified Analysis'
    raw_data = batch_data.get(UNIFIED_REPORT_TAB, [])
    if not raw_data:
        logger.warning(f"⚠️ Empty sheet: {UNIFIED_REPORT_TAB}")
    else:
        headers = [normalize_column_name(str(cell)) for cell in raw_data[0] if cell]
        seen = {}
        unique_headers = []
        for i, header in enumerate(headers):
            if header in seen:
                seen[header] += 1
                unique_headers.append(f"{header}_{seen[header]}")
            else:
                seen[header] = 0
                unique_headers.append(header)
        logger.info(f"Headers in {UNIFIED_REPORT_TAB}: {unique_headers}")

        column_mapping = {
            'Buy_->_Sell_Exchange': 'Buy_Sell_Exchange',
            'Buy_Sell_Exchange': 'Buy_Sell_Exchange',
            'Buy_→_Sell_Exchange': 'Buy_Sell_Exchange',
            'Buy → Sell Exchange': 'Buy_Sell_Exchange',
            'Buy -> Sell Exchange': 'Buy_Sell_Exchange',
            'Buy-Sell Exchange': 'Buy_Sell_Exchange',
            'Recommendation': 'Recommendation',
            'Input_Cost': 'Input_Cost',
            'Ask_Price': 'Ask_Price',
            'Buy_Price': 'Bid_Price',
            'Sell_Price': 'Ask_Price',
            'Profit': 'Profit_Ask',
            'ROI_Ask': 'ROI_Ask',
            'Saturation': 'Saturation'
        }
        headers_mapped = [column_mapping.get(h, h) for h in unique_headers]

        buy_vs_produce_cols = [
            'Exchange', 'Ticker', 'Product', 'Input_Cost', 'Ask_Price', 'Bid_Price',
            'Supply', 'Demand', 'Traded', 'Saturation', 'Profit_Ask', 'ROI_Ask',
            'Recommendation', 'Buy_Sell_Exchange'
        ]
        data_rows = []
        in_section = False
        header_len = len(unique_headers)
        for i, row in enumerate(raw_data[1:], start=2):
            if len(row) > 0 and row[0].strip().lower() == 'buy vs produce':
                in_section = True
                continue
            elif in_section:
                if len(row) == 0 or (len(row) > 0 and row[0].strip().lower() in ['arbitrage opportunities', 'material analysis']):
                    break
                if len(row) != header_len:
                    logger.debug(f"Invalid row length at row {i}: expected {header_len}, got {len(row)}")
                    row = row + [''] * (header_len - len(row)) if len(row) < header_len else row[:header_len]
                data_rows.append(row)

        if not data_rows:
            logger.warning(f"No Buy vs Produce data in {UNIFIED_REPORT_TAB}")
        else:
            try:
                df_unified = pd.DataFrame(data_rows, columns=headers_mapped, dtype='string')
                logger.info(f"Loaded {len(df_unified)} rows from {UNIFIED_REPORT_TAB}")
                logger.debug(f"Raw data for Unified Analysis (first 5 rows): {data_rows[:5]}")

                if len(unique_headers) > 19 and unique_headers[19] == 'Recommendation':
                    df_unified['Recommendation'] = df_unified.iloc[:, 19]
                else:
                    logger.warning("Recommendation column not found at index 19, checking headers")
                    for i, header in enumerate(unique_headers):
                        if header == 'Recommendation':
                            df_unified['Recommendation'] = df_unified.iloc[:, i]
                            logger.info(f"Found Recommendation at index {i}")
                            break
                    else:
                        df_unified['Recommendation'] = 'Neutral'
                        logger.warning("Recommendation column not found, defaulting to Neutral")

                selected_cols = [col for col in buy_vs_produce_cols if col in df_unified.columns]
                df_unified = df_unified[selected_cols]

                df_mapped = pd.DataFrame(index=df_unified.index, columns=expected_cols)
                for src_col, tgt_col in column_mapping.items():
                    if src_col in df_unified.columns:
                        df_mapped[tgt_col] = df_unified[src_col]
                for col in expected_cols:
                    if col not in df_mapped.columns:
                        df_mapped[col] = None
                df_mapped['Timestamp'] = timestamp_str
                df_mapped['Source'] = source_type

                invalid_timestamps = df_mapped[df_mapped['Timestamp'].isna()]
                if not invalid_timestamps.empty:
                    logger.warning(f"Rows with missing timestamps in Unified Analysis: {len(invalid_timestamps)}")
                    logger.debug(f"Invalid timestamp rows: {invalid_timestamps[['Ticker', 'Exchange']].to_dict('records')}")
                df_mapped['Timestamp'] = df_mapped['Timestamp'].fillna(timestamp_str)

                if 'Buy_Sell_Exchange' in df_mapped.columns:
                    df_mapped['Exchange'] = df_mapped['Buy_Sell_Exchange'].str.extract(r' -> (\w+)$')
                    df_mapped['Exchange'] = df_mapped['Exchange'].where(
                        df_mapped['Exchange'].isin(EXPECTED_EXCHANGES),
                        df_mapped['Exchange']
                    )

                invalid_rows = df_mapped[
                    (df_mapped['Exchange'].isna()) |
                    (~df_mapped['Exchange'].isin(EXPECTED_EXCHANGES)) |
                    df_mapped['Ticker'].isna() | (df_mapped['Ticker'] == '')
                ]
                if not invalid_rows.empty:
                    logger.debug(f"Invalid rows in Unified Analysis: {invalid_rows[['Ticker', 'Product', 'Exchange']].to_dict('records')}")
                
                df_mapped = df_mapped[
                    (df_mapped['Exchange'].isin(EXPECTED_EXCHANGES)) &
                    df_mapped['Ticker'].notna() & (df_mapped['Ticker'] != '')
                ]
                
                for col in ['Input_Cost', 'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded',
                           'Saturation', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid']:
                    if col in df_mapped.columns:
                        df_mapped[col] = pd.to_numeric(df_mapped[col].str.replace(',', '').str.replace('%', ''), errors='coerce').fillna(0.0)
                df_mapped['Recommendation'] = df_mapped['Recommendation'].fillna('Neutral')
                dfs.append(df_mapped)
                logger.info(f"Loaded {source_type} sheet with {len(df_mapped)} rows")
            except Exception as e:
                logger.error(f"Error processing Unified Analysis data: {e}")
                logger.debug(f"Problematic data rows: {data_rows[:5]}")

    # Process DATA {cx} sheets
    for sheet_name in [s for s in batch_data if s.startswith("DATA ")]:
        try:
            source_type = 'DATA'
            exchange = sheet_name.replace("DATA ", "")
            if exchange not in EXPECTED_EXCHANGES:
                logger.warning(f"Skipping invalid exchange sheet: {sheet_name}")
                continue
            raw_data = batch_data[sheet_name]
            if not raw_data:
                logger.warning(f"⚠️ Empty sheet: {sheet_name}")
                continue

            headers = [normalize_column_name(str(cell)) for cell in raw_data[0] if cell]
            seen = {}
            unique_headers = []
            for i, header in enumerate(headers):
                if header in seen:
                    seen[header] += 1
                    unique_headers.append(f"{header}_{seen[header]}")
                else:
                    seen[header] = 0
                    unique_headers.append(header)

            data_cols = ['Ticker', 'Product', 'Input_Cost', 'Ask_Price', 'Bid_Price', 'Supply',
                         'Demand', 'Traded', 'Saturation', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid']
            col_mapping = {
                'Ticker': 'Ticker',
                'Product': 'Product',
                'Input_Cost': 'Input_Cost',
                'Ask_Price': 'Ask_Price',
                'Buy_Price': 'Bid_Price',
                'Sell_Price': 'Ask_Price',
                'Supply': 'Supply',
                'Demand': 'Demand',
                'Traded': 'Traded',
                'Saturation': 'Saturation',
                'Profit': 'Profit_Ask',
                'Profit_Ask': 'Profit_Ask',
                'Profit_Bid': 'Profit_Bid',
                'ROI_Ask': 'ROI_Ask',
                'ROI_Bid': 'ROI_Bid'
            }
            data_rows = []
            header_len = len(unique_headers)
            for row in raw_data[1:]:
                if len(row) < header_len:
                    row = row + [''] * (header_len - len(row))
                elif len(row) > header_len:
                    row = row[:header_len]
                data_rows.append(row)

            df_data = pd.DataFrame(data_rows, columns=unique_headers, dtype='string')
            logger.debug(f"Raw data for {sheet_name} (first 5 rows): {data_rows[:5]}")
            selected_cols = [col for col in data_cols if col in df_data.columns]
            df_data = df_data[selected_cols]

            df_mapped = pd.DataFrame(index=df_data.index, columns=expected_cols)
            for src_col, tgt_col in col_mapping.items():
                if src_col in df_data.columns:
                    df_mapped[tgt_col] = df_data[src_col]
            for col in expected_cols:
                if col not in df_mapped.columns:
                    df_mapped[col] = None
            df_mapped['Timestamp'] = timestamp_str
            df_mapped['Exchange'] = exchange
            df_mapped['Source'] = source_type
            df_mapped['Recommendation'] = df_mapped.get('Recommendation', 'Neutral')

            invalid_timestamps = df_mapped[df_mapped['Timestamp'].isna()]
            if not invalid_timestamps.empty:
                logger.warning(f"Rows with missing timestamps in {sheet_name}: {len(invalid_timestamps)}")
                logger.debug(f"Invalid timestamp rows: {invalid_timestamps[['Ticker', 'Exchange']].to_dict('records')}")
            df_mapped['Timestamp'] = df_mapped['Timestamp'].fillna(timestamp_str)

            df_mapped = df_mapped[
                df_mapped['Ticker'].notna() & (df_mapped['Ticker'] != '')
            ]
            if df_mapped.empty:
                logger.warning(f"No valid data in {sheet_name}")
                continue

            for col in ['Input_Cost', 'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded',
                       'Saturation', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid']:
                if col in df_mapped.columns:
                    df_mapped[col] = pd.to_numeric(df_mapped[col].str.replace(',', '').str.replace('%', ''), errors='coerce').fillna(0.0)
            dfs.append(df_mapped)
            logger.info(f"Loaded {source_type} sheet {sheet_name} with {len(df_mapped)} rows")
        except Exception as e:
            logger.error(f"Error loading {sheet_name}: {e}")

    if not dfs:
        logger.warning("⚠️ No new data loaded")
        return pd.DataFrame()

    all_df = pd.concat(dfs, ignore_index=True)
    logger.info(f"Combined {len(dfs)} DataFrames with {len(all_df)} rows")

    # Merge data
    unified_cols = ['Exchange', 'Ticker', 'Product', 'Input_Cost', 'Ask_Price', 'Bid_Price',
                    'Supply', 'Demand', 'Traded', 'Saturation', 'Profit_Ask', 'ROI_Ask',
                    'Recommendation']
    data_cols = ['Exchange', 'Ticker', 'Product', 'Input_Cost', 'Ask_Price', 'Bid_Price',
                 'Supply', 'Demand', 'Traded', 'Saturation', 'Profit_Ask', 'Profit_Bid',
                 'ROI_Ask', 'ROI_Bid']
    unified_df = all_df[all_df['Source'] == 'Unified Analysis'][unified_cols]
    data_df = all_df[all_df['Source'] == 'DATA'][data_cols]

    if unified_df.empty:
        merged_df = data_df
    else:
        merged_df = data_df.merge(
            unified_df,
            on=['Exchange', 'Ticker', 'Product'],
            how='left',
            suffixes=('_data', '_unified')
        )
        for col in ['Input_Cost', 'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded',
                    'Saturation', 'Profit_Ask', 'ROI_Ask']:
            if f'{col}_unified' in merged_df.columns:
                merged_df[col] = merged_df[f'{col}_unified'].where(merged_df[f'{col}_unified'].notna(), merged_df[f'{col}_data'])
            else:
                merged_df[col] = merged_df[f'{col}_data']
        for col in ['Profit_Bid', 'ROI_Bid']:
            if f'{col}_data' in merged_df.columns:
                merged_df[col] = merged_df[f'{col}_data']
        merged_df['Recommendation'] = merged_df.get('Recommendation_unified', merged_df.get('Recommendation_data', 'Neutral'))
        merged_df['Timestamp'] = merged_df['Timestamp'].fillna(timestamp_str)
        merged_df['Source'] = 'Merged'

    for col in expected_cols:
        if col not in merged_df.columns:
            merged_df[col] = None
        elif col in ['Input_Cost', 'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded',
                    'Saturation', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid']:
            merged_df[col] = pd.to_numeric(merged_df[col], errors='coerce').fillna(0.0)
            if col in ['ROI_Ask', 'ROI_Bid']:
                merged_df[col] = merged_df[col].clip(upper=100000, lower=-100000)
            if col == 'Saturation':
                merged_df[col] = merged_df[col].clip(upper=1000000)
        elif col == 'Recommendation':
            merged_df[col] = merged_df[col].fillna('Neutral')

    merged_df['Recommendation'] = merged_df.apply(set_recommendation, axis=1)

    invalid_timestamps = merged_df[merged_df['Timestamp'].isna()]
    if not invalid_timestamps.empty:
        logger.warning(f"Rows with missing timestamps in merged data: {len(invalid_timestamps)}")
        logger.debug(f"Invalid timestamp rows: {invalid_timestamps[['Ticker', 'Exchange']].to_dict('records')}")
    merged_df['Timestamp'] = merged_df['Timestamp'].fillna(timestamp_str)

    merged_df = merged_df.sort_values(['Exchange', 'Ticker']).drop_duplicates(subset=['Exchange', 'Ticker'])
    logger.info(f"Deduplicated data, total rows: {len(merged_df)}")
    logger.debug(f"Available tickers: {sorted(merged_df['Ticker'].unique())}")
    logger.debug(f"Available exchanges: {sorted(merged_df['Exchange'].unique())}")

    # Save to SQLite and CSV
    conn = sqlite3.connect(DB_PATH)
    for i in range(0, len(merged_df), CHUNK_SIZE):
        chunk = merged_df[i:i + CHUNK_SIZE]
        chunk.to_sql('raw_data', conn, if_exists='append', index=False, method=None)
        logger.info(f"Saved chunk {i // CHUNK_SIZE + 1} with {len(chunk)} rows to SQLite")
    conn.close()

    os.makedirs(CSV_DIR, exist_ok=True)
    csv_file = os.path.join(CSV_DIR, f'market_data_{current_timestamp.strftime("%Y%m%d_%H%M%S")}.csv.gz')
    merged_df.to_csv(csv_file, index=False, compression='gzip')
    logger.info(f"Saved compressed CSV: {csv_file}")

    return merged_df

def update_ticker_arbitrage_tab(spreadsheet, ticker, ticker_data, headers, formatting_ranges, current_timestamp, existing_sheets):
    """Update a single ticker tab (for parallel execution)."""
    try:
        if ticker_data.empty:
            logger.warning(f"No data for ticker {ticker} after filtering, skipping")
            logger.debug(f"Available data for {ticker} before filtering: {ticker_data.to_dict('records')}")
            return None

        logger.debug(f"Ticker {ticker} row count: {len(ticker_data)}")
        logger.debug(f"Ticker {ticker} data head: {ticker_data.head().to_dict('records')}")

        for col in ['Input_Cost', 'Ask_Price', 'Bid_Price', 'Supply', 'Demand', 'Traded',
                    'Saturation', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid']:
            if col in ticker_data.columns:
                ticker_data[col] = pd.to_numeric(ticker_data[col], errors='coerce').fillna(0.0)
        ticker_data['Recommendation'] = ticker_data['Recommendation'].fillna('Neutral')
        ticker_data['Exchange'] = ticker_data['Exchange'].fillna('Unknown')
        ticker_data['Timestamp'] = ticker_data['Timestamp'].apply(
            lambda x: pd.to_datetime(x, errors='coerce').strftime('%Y-%m-%d %H:%M:%S') 
            if pd.notnull(x) else current_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        )

        invalid_rows = ticker_data[ticker_data['Timestamp'].isna() | ticker_data['Exchange'].isna()]
        if not invalid_rows.empty:
            logger.warning(f"Invalid rows for ticker {ticker}: {len(invalid_rows)}")
            logger.debug(f"Invalid rows: {invalid_rows.to_dict('records')}")

        ticker_data = ticker_data.sort_values(['Timestamp', 'Exchange'], ascending=[False, True])
        sheet_name = get_valid_sheet_name(ticker)
        get_or_create_worksheet(spreadsheet, sheet_name, headers=headers, existing_sheets=existing_sheets)
        return sheet_name, (ticker_data, headers, formatting_ranges)
    except Exception as e:
        logger.error(f"Error preparing ticker {ticker}: {e}")
        return None

def update_ticker_arbitrage_tabs(spreadsheet, data_df, current_timestamp, retention_days=RETENTION_DAYS):
    """Update per-ticker arbitrage tabs in parallel."""
    if data_df.empty:
        logger.warning("Empty DataFrame provided for ticker arbitrage tabs")
        return

    headers = [
        'Timestamp', 'Exchange', 'Input_Cost', 'Ask_Price', 'Bid_Price', 'Supply',
        'Demand', 'Traded', 'Saturation', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask',
        'ROI_Bid', 'Recommendation'
    ]
    format_configs = [
        ('A2:A', CellFormat(numberFormat=NumberFormat(type='DATE_TIME', pattern='yyyy-mm-dd hh:mm:ss'))),
        ('C2:C', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0.00'))),
        ('D2:D', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0.00'))),
        ('E2:E', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0.00'))),
        ('F2:F', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0'))),
        ('G2:G', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0'))),
        ('H2:H', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0'))),
        ('I2:I', CellFormat(numberFormat=NumberFormat(type='PERCENT', pattern='0.00%'))),
        ('J2:J', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0.00'))),
        ('K2:K', CellFormat(numberFormat=NumberFormat(type='NUMBER', pattern='#,##0.00'))),
        ('L2:L', CellFormat(numberFormat=NumberFormat(type='PERCENT', pattern='0.00%'))),
        ('M2:M', CellFormat(numberFormat=NumberFormat(type='PERCENT', pattern='0.00%'))),
    ]

    # Cache existing worksheets
    for attempt in range(MAX_RETRIES):
        try:
            existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
            logger.debug(f"Cached worksheet titles for target spreadsheet: {existing_sheets}")
            break
        except gspread.exceptions.APIError as e:
            error_message = str(e)
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            logger.debug(f"APIError in fetching worksheets: {error_message}")
            if status_code == 429:
                backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                logger.warning(f"429 error fetching worksheets, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(backoff_time)
            else:
                logger.error(f"Error fetching worksheets: {error_message}")
                raise
    else:
        raise gspread.exceptions.APIError("Max retries reached for fetching worksheets")

    updates = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_ticker = {
            executor.submit(update_ticker_arbitrage_tab, spreadsheet, ticker, data_df[data_df['Ticker'] == ticker][headers], headers, format_configs, current_timestamp, existing_sheets): ticker
            for ticker in data_df['Ticker'].unique()
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                if result:
                    sheet_name, update_data = result
                    updates[sheet_name] = update_data
                    logger.info(f"✅ Prepared update for ticker {ticker}")
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")

    if updates:
        batch_update_sheets(spreadsheet, updates)
    else:
        logger.warning("No valid ticker updates to process")

def clean_old_tabs(spreadsheet, retention_days=RETENTION_DAYS):
    """Delete old report tabs and trim old data in ticker tabs."""
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).date()
        cutoff_timestamp = (datetime.now(timezone.utc) - timedelta(days=retention_days)).strftime('%Y-%m-%d %H:%M:%S')
        
        for attempt in range(MAX_RETRIES):
            try:
                worksheets = spreadsheet.worksheets()
                break
            except gspread.exceptions.APIError as e:
                error_message = str(e)
                status_code = getattr(getattr(e, 'response', None), 'status_code', None)
                logger.debug(f"APIError in clean_old_tabs: {error_message}")
                if status_code == 429:
                    backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                    API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                    logger.warning(f"429 error fetching worksheets, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Error fetching worksheets: {error_message}")
                    raise
        else:
            raise gspread.exceptions.APIError("Max retries reached for fetching worksheets")

        tabs_to_delete = [ws for ws in worksheets if re.match(r'\d{4}-\d{2}-\d{2}', ws.title) and
                          datetime.strptime(ws.title, '%Y-%m-%d').date() < cutoff]
        for ws in tabs_to_delete:
            for attempt in range(MAX_RETRIES):
                try:
                    spreadsheet.del_worksheet(ws)
                    logger.info(f"Deleted old daily report: {ws.title}")
                    break
                except gspread.exceptions.APIError as e:
                    error_message = str(e)
                    status_code = getattr(getattr(e, 'response', None), 'status_code', None)
                    logger.debug(f"APIError in clean_old_tabs: {error_message}")
                    if status_code == 429:
                        backoff_time = INITIAL_BACKOFF * (2 ** attempt) + random.uniform(-0.5, 0.5)
                        API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                        logger.warning(f"429 error deleting {ws.title}, retrying in {backoff_time:.2f}s (attempt {attempt+1}/{MAX_RETRIES})")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"Error deleting {ws.title}: {error_message}")
                        raise

        ticker_sheets = [ws for ws in worksheets if ws.title not in [UNIFIED_REPORT_TAB] and not re.match(r'\d{4}-\d{2}-\d{2}', ws.title)]
        for worksheet in ticker_sheets:
            try:
                data = batch_get_sheets(spreadsheet, [worksheet.title]).get(worksheet.title, [])
                if not data or len(data) <= 1:
                    logger.debug(f"Skipping {worksheet.title}: no data")
                    continue
                headers = data[0]
                if 'Timestamp' not in headers:
                    logger.debug(f"Skipping {worksheet.title}: no Timestamp column")
                    continue
                timestamp_idx = headers.index('Timestamp')
                rows_to_keep = [row for row in data[1:] if row[timestamp_idx] >= cutoff_timestamp]
                if len(rows_to_keep) == len(data) - 1:
                    logger.debug(f"Skipping {worksheet.title}: all data is recent")
                    continue
                new_data = [headers] + rows_to_keep
                worksheet.clear()
                worksheet.update(values=new_data, range_name='A1', value_input_option='RAW')
                logger.info(f"Trimmed old data in {worksheet.title}, kept {len(rows_to_keep)} rows")
            except Exception as e:
                logger.error(f"Error trimming {worksheet.title}: {e}")
                continue
    except Exception as e:
        logger.error(f"❌ Error cleaning old tabs: {e}")
        raise

def process_data(max_retries=3):
    """Process data from PrUn Tracker and update per-ticker arbitrage tabs."""
    check_gspread_version()
    for attempt in range(max_retries):
        try:
            init_db()
            last_timestamp = get_last_processed_timestamp()
            logger.info(f"Last processed timestamp: {last_timestamp}")

            client = authenticate_sheets()
            if not client:
                logger.error("❌ Authentication failed")
                return

            # Open spreadsheets with rate limit handling
            for open_attempt in range(MAX_RETRIES):
                try:
                    source = client.open_by_key(SOURCE_SPREADSHEET_ID)
                    target = client.open_by_key(TARGET_SPREADSHEET_ID)
                    break
                except gspread.exceptions.APIError as e:
                    error_message = str(e)
                    status_code = getattr(getattr(e, 'response', None), 'status_code', None)
                    logger.debug(f"APIError in opening spreadsheets: {error_message}")
                    if status_code == 429:
                        backoff_time = INITIAL_BACKOFF * (2 ** open_attempt) + random.uniform(-0.5, 0.5)
                        API_DELAY[0] = min(API_DELAY[0] * 1.5, 3.0)
                        logger.warning(f"429 error opening spreadsheets, retrying in {backoff_time:.2f}s (attempt {open_attempt+1}/{MAX_RETRIES})")
                        time.sleep(backoff_time)
                    else:
                        logger.error(f"Error opening spreadsheets: {error_message}")
                        raise
            else:
                raise gspread.exceptions.APIError("Max retries reached for opening spreadsheets")

            df = load_source_data(source, last_timestamp)
            if df.empty:
                logger.warning("⚠️ No new data loaded, aborting")
                return

            if 'Timestamp' in df.columns:
                latest_timestamp = pd.to_datetime(df['Timestamp'], errors='coerce').max()
                if pd.notnull(latest_timestamp):
                    set_last_processed_timestamp(latest_timestamp)

            update_ticker_arbitrage_tabs(target, df, datetime.now(timezone.utc))
            clean_old_tabs(target)
            logger.info("🎯 Process complete")
            return
        except Exception as e:
            logger.error(f"Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error("❌ Max retries reached, exiting")
                raise

if __name__ == "__main__":
    process_data()