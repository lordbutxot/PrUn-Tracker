import sqlite3
import pandas as pd
import os
import logging
from historical_data.config import CACHE_DIR

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(CACHE_DIR, '..', 'data', 'prosperous_universe.db')

def init_db():
    """Initialize the SQLite database and create necessary tables."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                Ticker TEXT,
                Exchange TEXT,
                Ask_Price REAL,
                Bid_Price REAL,
                Timestamp TEXT,
                PRIMARY KEY (Ticker, Exchange, Timestamp)
            )
        ''')
        conn.commit()
        logger.info(f"Initialized database at {DB_PATH}")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        conn.close()

def insert_price_data(prices_df):
    """Insert price data into the SQLite database."""
    try:
        if prices_df.empty:
            logger.warning("Empty DataFrame provided for insertion, skipping")
            return
        
        required_columns = ['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price']
        missing_columns = [col for col in required_columns if col not in prices_df.columns]
        if missing_columns:
            logger.error(f"Missing required columns in prices_df: {missing_columns}")
            return
        
        prices_df = prices_df.copy()
        prices_df['Timestamp'] = pd.to_datetime(prices_df.get('Timestamp', pd.Timestamp.now(tz='UTC'))).astype(str)
        prices_df = prices_df[['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price', 'Timestamp']]
        
        conn = sqlite3.connect(DB_PATH)
        prices_df.to_sql('prices', conn, if_exists='append', index=False)
        conn.commit()
        logger.info(f"Inserted {len(prices_df)} rows into prices table")
    except Exception as e:
        logger.error(f"Error inserting price data: {e}")
    finally:
        conn.close()

def load_historical_data(exchange='ALL'):
    """Load historical price data from SQLite database for a given exchange or all exchanges."""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM prices" if exchange == 'ALL' else "SELECT * FROM prices WHERE Exchange = ?"
        params = () if exchange == 'ALL' else (exchange,)
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            logger.info(f"Loaded historical data for exchange {exchange}: {len(df)} rows")
        else:
            logger.warning(f"No historical data found for exchange {exchange}")
        return df
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return pd.DataFrame()
    finally:
        conn.close()