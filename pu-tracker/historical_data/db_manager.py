import sqlite3
import os
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# Get the logger
logger = logging.getLogger(__name__)

# Database configuration
DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DB_PATH = os.path.join(DB_DIR, 'prosperous_universe.db')

def get_db_connection():
    """Get a connection to the SQLite database."""
    # Ensure the data directory exists
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    """Initialize the database with required tables."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create prices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                exchange TEXT NOT NULL,
                ask_price REAL,
                bid_price REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ticker, exchange, timestamp)
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prices_ticker_exchange 
            ON prices (ticker, exchange)
        ''')
        
        # Create index for timestamp queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prices_timestamp 
            ON prices (timestamp)
        ''')
        
        conn.commit()
        logger.info(f"Initialized database at {DB_PATH}")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def insert_price_data(prices_df):
    """Insert price data into the database with proper error handling."""
    try:
        conn = get_db_connection()
        
        # Check if required columns exist
        required_columns = ['Exchange', 'Ask_Price', 'Bid_Price']
        missing_columns = [col for col in required_columns if col not in prices_df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns in prices_df: {missing_columns}")
            return False
        
        # Prepare data for insertion
        df_copy = prices_df.copy()
        
        # Add timestamp if it doesn't exist
        if 'Timestamp' not in df_copy.columns:
            df_copy['Timestamp'] = datetime.now()
        
        # Ensure Timestamp is properly formatted
        if 'Timestamp' in df_copy.columns:
            # Convert timestamp to string if it's not already
            if hasattr(df_copy['Timestamp'].iloc[0], 'strftime'):
                df_copy['Timestamp'] = df_copy['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            elif not isinstance(df_copy['Timestamp'].iloc[0], str):
                df_copy['Timestamp'] = str(df_copy['Timestamp'].iloc[0])
        
        # Select only the columns we need for the database
        db_columns = ['Ticker', 'Exchange', 'Ask_Price', 'Bid_Price', 'Timestamp']
        available_columns = [col for col in db_columns if col in df_copy.columns]
        
        if 'Ticker' not in available_columns:
            logger.error("No Ticker column found in processed data")
            return False
        
        # Prepare the data for database insertion
        df_to_insert = df_copy[available_columns].copy()
        
        # Rename columns to match database schema
        column_mapping = {
            'Ticker': 'ticker',
            'Exchange': 'exchange', 
            'Ask_Price': 'ask_price',
            'Bid_Price': 'bid_price',
            'Timestamp': 'timestamp'
        }
        
        df_to_insert = df_to_insert.rename(columns=column_mapping)
        
        # Insert data
        df_to_insert.to_sql('prices', conn, if_exists='append', index=False)
        
        logger.info(f"Successfully inserted {len(df_to_insert)} price records")
        return True
        
    except Exception as e:
        logger.error(f"Error inserting price data: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def get_latest_prices(exchange=None, limit=1000):
    """Get the latest price data from the database."""
    try:
        conn = get_db_connection()
        
        if exchange:
            query = """
                SELECT ticker, exchange, ask_price, bid_price, timestamp
                FROM prices 
                WHERE exchange = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(exchange, limit))
        else:
            query = """
                SELECT ticker, exchange, ask_price, bid_price, timestamp
                FROM prices 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(limit,))
        
        return df
        
    except Exception as e:
        logger.error(f"Error retrieving price data: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals():
            conn.close()

def cleanup_old_data(days_to_keep=30):
    """Clean up old price data to keep database size manageable."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete records older than specified days
        cursor.execute("""
            DELETE FROM prices 
            WHERE timestamp < datetime('now', '-{} days')
        """.format(days_to_keep))
        
        deleted_rows = cursor.rowcount
        conn.commit()
        
        logger.info(f"Cleaned up {deleted_rows} old price records")
        return deleted_rows
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def load_historical_data(exchange=None):
    """Load historical data for a specific exchange or all exchanges."""
    try:
        conn = get_db_connection()
        
        if exchange:
            query = """
                SELECT ticker, exchange, ask_price, bid_price, timestamp
                FROM prices 
                WHERE exchange = ?
                ORDER BY timestamp DESC
            """
            df = pd.read_sql_query(query, conn, params=(exchange,))
        else:
            query = """
                SELECT ticker, exchange, ask_price, bid_price, timestamp
                FROM prices 
                ORDER BY timestamp DESC
            """
            df = pd.read_sql_query(query, conn)
        
        logger.info(f"Loaded {len(df)} historical records{' for exchange ' + exchange if exchange else ''}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error
    finally:
        if 'conn' in locals():
            conn.close()