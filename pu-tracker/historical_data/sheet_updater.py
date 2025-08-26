import aiohttp
import asyncio
import pandas as pd
import time
import logging
import json
import os
from datetime import datetime, timezone, timedelta
from gspread_formatting import (
    CellFormat, Color, TextFormat, NumberFormat, format_cell_range, ConditionalFormatRule, GridRange
)
from gspread_dataframe import set_with_dataframe
from historical_data.config import CACHE_DIR, REFRESH_INTERVAL_HOURS, TARGET_SPREADSHEET_ID, CREDENTIALS_FILE, EXPECTED_EXCHANGES, FORMAT_CONFIGS
from historical_data.sheets_api import authenticate_sheets, get_or_create_worksheet
from historical_data.data_collection import TIER_0_RESOURCES
from historical_data.db_manager import load_historical_data

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Expected headers to ensure consistency
EXPECTED_HEADERS = [
    'BuyingOrders', 'SellingOrders', 'CXDataModelId', 'MaterialName', 'Ticker',
    'MaterialId', 'ExchangeName', 'ExchangeCode', 'Currency', 'Previous', 'Price',
    'PriceTimeEpochMs', 'High', 'AllTimeHigh', 'Low', 'AllTimeLow', 'Ask_Price',
    'Ask_Avail', 'Bid_Price', 'Bid_Avail', 'Supply', 'Demand', 'Traded',
    'VolumeAmount', 'PriceAverage', 'NarrowPriceBandLow', 'NarrowPriceBandHigh',
    'WidePriceBandLow', 'WidePriceBandHigh', 'MMBuy', 'MMSell', 'UserNameSubmitted',
    'Timestamp', 'Exchange', 'Price_Spread', 'Saturation', 'Category', 'Product',
    'Tier', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid',
    'Risk', 'Viability', 'Investment_Score'
]

class MarketProcessor:
    def __init__(self, spreadsheet=None):
        self.client = authenticate_sheets()
        self.spreadsheet = spreadsheet or self.client.spreadsheets().get(spreadsheetId=TARGET_SPREADSHEET_ID).execute()
        self.price_cache = {}
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=2),
            timeout=aiohttp.ClientTimeout(total=60)
        )

    async def close(self):
        await self.session.close()

    def is_cache_fresh(self, file):
        """Check if cache file is fresh based on REFRESH_INTERVAL_HOURS."""
        if not os.path.exists(file):
            return False
        cache_time = datetime.fromtimestamp(os.path.getmtime(file), tz=timezone.utc)
        return (datetime.now(timezone.utc) - cache_time) < timedelta(hours=REFRESH_INTERVAL_HOURS)

    async def load_price_data(self, cx):
        """Load price data from cache or historical DB."""
        cache_file = os.path.join(CACHE_DIR, 'prices_all.csv')
        if self.is_cache_fresh(cache_file):
            try:
                df = pd.read_csv(cache_file)
                if 'Exchange' not in df.columns:
                    logger.error(f"Cached prices_all.csv missing 'Exchange' column, using fallback")
                    columns = EXPECTED_HEADERS
                    df = pd.DataFrame(columns=columns)
                    tickers = list(TIER_0_RESOURCES.keys())
                    for ticker in tickers:
                        for ex in EXPECTED_EXCHANGES:
                            row = ['' if col not in ['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price', 'Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid', 'Risk', 'Viability', 'Investment_Score'] else 0.0 if col in ['Ask_Price', 'Bid_Price', 'Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid', 'Risk', 'Viability', 'Investment_Score'] else ticker if col == 'Ticker' else ex if col == 'Exchange' else '' for col in columns]
                            df.loc[len(df)] = row
                logger.info(f"Using cached prices for {cx} from {cache_file} with columns: {list(df.columns)}")
                return df[df['Exchange'] == cx] if cx != 'ALL' else df
            except Exception as e:
                logger.error(f"Error loading cached prices for {cx}: {e}, falling back to DB")
        
        df = load_historical_data(cx)
        if df.empty:
            logger.warning(f"No historical data for {cx}, using fallback")
            columns = EXPECTED_HEADERS
            df = pd.DataFrame(columns=columns)
            tickers = list(TIER_0_RESOURCES.keys())
            for ticker in tickers:
                for ex in EXPECTED_EXCHANGES:
                    row = ['' if col not in ['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price', 'Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid', 'Risk', 'Viability', 'Investment_Score'] else 0.0 if col in ['Ask_Price', 'Bid_Price', 'Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid', 'Risk', 'Viability', 'Investment_Score'] else ticker if col == 'Ticker' else ex if col == 'Exchange' else '' for col in columns]
                    df.loc[len(df)] = row
        logger.info(f"Loaded prices for {cx} with columns: {list(df.columns)}")
        return df[df['Exchange'] == cx] if cx != 'ALL' else df

    async def process_exchange(self, cx, start_time):
        """Process and update sheet for a single exchange."""
        logger.info(f"Processing {cx}")
        df = await self.load_price_data(cx)
        if df.empty:
            logger.warning(f"No data for {cx}, using fallback")
            df = pd.DataFrame({
                'Ticker': list(TIER_0_RESOURCES.keys()),
                'Product': [TIER_0_RESOURCES[t]['name'] for t in TIER_0_RESOURCES],
                'Category': [TIER_0_RESOURCES[t]['category'] for t in TIER_0_RESOURCES],
                'Tier': [TIER_0_RESOURCES[t]['tier'] for t in TIER_0_RESOURCES],
                'Input_Cost': [0.0] * len(TIER_0_RESOURCES),
                'Ask_Price': [0.0] * len(TIER_0_RESOURCES),
                'Bid_Price': [0.0] * len(TIER_0_RESOURCES),
                'Price_Spread': [0.0] * len(TIER_0_RESOURCES),
                'Saturation': [0.0] * len(TIER_0_RESOURCES),
                'Profit_Ask': [0.0] * len(TIER_0_RESOURCES),
                'Profit_Bid': [0.0] * len(TIER_0_RESOURCES),
                'ROI_Ask': [0.0] * len(TIER_0_RESOURCES),
                'ROI_Bid': [0.0] * len(TIER_0_RESOURCES),
                'Risk': [7.5] * len(TIER_0_RESOURCES),
                'Viability': [2.5] * len(TIER_0_RESOURCES),
                'Investment_Score': [2.5] * len(TIER_0_RESOURCES),
                'Exchange': [cx] * len(TIER_0_RESOURCES)
            })
            # Ensure all expected columns
            for col in EXPECTED_HEADERS:
                if col not in df.columns:
                    df[col] = '' if col not in ['Ask_Price', 'Bid_Price', 'Saturation', 'Input_Cost', 'Profit_Ask', 'Profit_Bid', 'ROI_Ask', 'ROI_Bid', 'Risk', 'Viability', 'Investment_Score'] else 0.0
        
        # Ensure unique column names
        df.columns = [f"{col}_{i}" if list(df.columns).count(col) > 1 else col for i, col in enumerate(df.columns)]
        logger.info(f"Writing to sheet DATA {cx} with headers: {list(df.columns)}")
        
        worksheet, _ = get_or_create_worksheet(self.spreadsheet, f"DATA {cx}", headers=EXPECTED_HEADERS)
        worksheet.clear()
        set_with_dataframe(worksheet, df, include_index=False, include_column_header=True)
        
        for column, format_config in FORMAT_CONFIGS:
            format_cell_range(worksheet, column, CellFormat(**format_config))
        
        logger.info(f"Updated sheet DATA {cx} with {len(df)} rows")
        logger.info(f"Processing {cx} completed in {time.time() - start_time:.2f}s")

    async def process(self, analysis_results):
        """Process analysis results and update sheets."""
        start_time = time.time()
        for cx in EXPECTED_EXCHANGES:
            await self.process_exchange(cx, start_time)
            time.sleep(60)  # Increased delay to minimize API load

    def update_exchange_tabs(spreadsheet, report_df, analysis_results):
        worksheet_titles = [ws.title for ws in spreadsheet.worksheets()]
        exchange_tickers = [title.replace("DATA ", "") for title in worksheet_titles if title.startswith("DATA ")]
        for exchange in exchange_tickers:
            data_tab = f"DATA {exchange}"
            report_tab = f"Report {exchange}"

            # Filter for this exchange (assumes 'Exchange' column exists)
            data_for_exchange = report_df[report_df['Exchange'] == exchange]
            analysis_for_exchange = analysis_results[analysis_results['Exchange'] == exchange]

            # Update or create DATA tab
            if data_tab in worksheet_titles:
                ws_data = spreadsheet.worksheet(data_tab)
            else:
                ws_data = spreadsheet.add_worksheet(title=data_tab, rows=1000, cols=len(data_for_exchange.columns))
            ws_data.clear()
            ws_data.update([data_for_exchange.columns.values.tolist()] + data_for_exchange.values.tolist())

            # Update or create Report tab
            if report_tab in worksheet_titles:
                ws_report = spreadsheet.worksheet(report_tab)
            else:
                ws_report = spreadsheet.add_worksheet(title=report_tab, rows=1000, cols=len(analysis_for_exchange.columns))
            ws_report.clear()
            ws_report.update([analysis_for_exchange.columns.values.tolist()] + analysis_for_exchange.values.tolist())

async def main():
    """Main function that uploads processed data to Google Sheets."""
    start_time = time.time()
    
    # Load our processed data instead of historical database
    processed_data_path = os.path.join(CACHE_DIR, 'processed_data.csv')
    daily_report_path = os.path.join(CACHE_DIR, 'daily_report.csv')
    
    if not os.path.exists(daily_report_path):
        logger.error(f"Daily report not found at {daily_report_path}")
        logger.info("Please run process_data.py first to generate the daily report")
        return
    
    try:
        # Load the daily report with category and tier information
        logger.info(f"Loading daily report from {daily_report_path}")
        report_df = pd.read_csv(daily_report_path)
        logger.info(f"Loaded daily report with {len(report_df)} rows and columns: {list(report_df.columns)}")
        
        # Authenticate and get spreadsheet
        client = authenticate_sheets()
        spreadsheet = client.open_by_key(TARGET_SPREADSHEET_ID)
        
        # Upload data for each exchange
        for exchange in EXPECTED_EXCHANGES:
            exchange_data = report_df[report_df['exchange'] == exchange].copy()
            
            if not exchange_data.empty:
                logger.info(f"Uploading {len(exchange_data)} rows for exchange {exchange}")
                
                # Get or create worksheet for this exchange
                worksheet_name = f"DATA {exchange}"
                worksheet = get_or_create_worksheet(spreadsheet, worksheet_name)
                
                # Prepare data for upload - convert to the format expected by sheets
                upload_data = exchange_data.copy()
                
                # Rename columns to match expected format if needed
                column_mapping = {
                    'ticker': 'Ticker',
                    'exchange': 'Exchange', 
                    'category': 'Category',
                    'tier': 'Tier',
                    'ai1_ask_price': 'AI1_Ask_Price',
                    'ai1_bid_price': 'AI1_Bid_Price',
                    'ci1_ask_price': 'CI1_Ask_Price', 
                    'ci1_bid_price': 'CI1_Bid_Price',
                    'ci2_ask_price': 'CI2_Ask_Price',
                    'ci2_bid_price': 'CI2_Bid_Price',
                    'nc1_ask_price': 'NC1_Ask_Price',
                    'nc1_bid_price': 'NC1_Bid_Price',
                    'nc2_ask_price': 'NC2_Ask_Price', 
                    'nc2_bid_price': 'NC2_Bid_Price',
                    'ic1_ask_price': 'IC1_Ask_Price',
                    'ic1_bid_price': 'IC1_Bid_Price',
                    'input_cost': 'Input_Cost',
                    'profit_margin': 'Profit_Margin',
                    'roi_percentage': 'ROI_Percentage',
                    'investment_score': 'Investment_Score'
                }
                
                upload_data = upload_data.rename(columns=column_mapping)
                
                # Clear existing content and upload new data
                worksheet.clear()
                
                # Upload using gspread_dataframe for better formatting
                from gspread_dataframe import set_with_dataframe
                set_with_dataframe(worksheet, upload_data, include_index=False, include_column_header=True)
                
                logger.info(f"Successfully uploaded data to {worksheet_name}")
                
                # Add a small delay between uploads to avoid rate limits
                time.sleep(2)
            else:
                logger.warning(f"No data found for exchange {exchange}")
        
        logger.info(f"Sheet upload completed in {time.time() - start_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in sheet upload: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())