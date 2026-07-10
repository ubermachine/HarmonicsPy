import yfinance as yf
import duckdb
import os
import pandas as pd
import logging
import streamlit as st
import contextlib
import io

logging.basicConfig(level=logging.INFO)

DATA_DIR = "data_cache"

class CachedCandleData:
    def __init__(self, symbol, interval):
        self.symbol = symbol
        self.interval = interval
        self.df = None

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol: str, interval: str, candles: int = 1000, force_update: bool = False) -> CachedCandleData:
    """
    Fetches Yahoo Finance data, caches it to Parquet, and retrieves it via DuckDB.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    parquet_file = os.path.join(DATA_DIR, f"{symbol}_{interval}.parquet")
    
    # Period mapping for yfinance based on interval
    yf_interval = interval
    if interval == '1w':
        yf_interval = '1wk'
    elif interval == '1m':
        yf_interval = '1m'
    
    file_exists = os.path.exists(parquet_file)
    
    # Fetch data
    if not file_exists or force_update:
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                if file_exists and force_update:
                    df_old = pd.read_parquet(parquet_file)
                    time_col = df_old.columns[0]
                    max_date = df_old[time_col].max()
                    logging.info(f"Updating data for {symbol} from {max_date}")
                    
                    df_new = yf.download(symbol, interval=yf_interval, start=max_date, progress=False)
                    
                    if not df_new.empty:
                        if isinstance(df_new.columns, pd.MultiIndex):
                            df_new.columns = df_new.columns.get_level_values(0)
                        df_new.reset_index(inplace=True)
                        df_new.rename(columns={df_new.columns[0]: time_col}, inplace=True)
                        
                        df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=[time_col], keep='last')
                        df_combined.to_parquet(parquet_file, engine='pyarrow')
                        logging.info(f"Appended missing data to {parquet_file}")
                else:
                    logging.info(f"Downloading yfinance data for {symbol} at {yf_interval}")
                    if yf_interval.endswith('m') or yf_interval.endswith('h'):
                        df = yf.download(symbol, interval=yf_interval, period="60d", progress=False) 
                    else:
                        df = yf.download(symbol, interval=yf_interval, period="max", progress=False)
                        
                    if df.empty:
                        raise ValueError(f"No data returned for {symbol}")
                        
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)

                    df.reset_index(inplace=True)
                    df.to_parquet(parquet_file, engine='pyarrow')
                    logging.info(f"Data cached to {parquet_file}")
            
        except Exception as e:
            logging.error(f"Failed to download/update from yfinance: {e}")
            logging.info("Falling back to Parquet cache if available.")
            if not file_exists:
                raise Exception("No cached data available.")

    # Query with DuckDB
    # DuckDB will read the parquet file
    # We want the most recent 'candles' rows, sorted chronologically
    query = f"""
        SELECT * FROM (
            SELECT * FROM '{parquet_file}' 
            ORDER BY 1 DESC 
            LIMIT {candles}
        ) 
        ORDER BY 1 ASC
    """
    queried_df = duckdb.query(query).df()
    
    # Set index back to the time column for Pyharmonics
    time_col = queried_df.columns[0]
    queried_df.set_index(time_col, inplace=True)
    queried_df.index = pd.to_datetime(queried_df.index)
    
    cd = CachedCandleData(symbol, interval)
    cd.df = queried_df
    
    return cd

@st.cache_data(ttl=3600*24, show_spinner=False)
def get_bulk_yahoo_data_v2(symbols: list, interval: str, period: str = "1y", force_update: bool = False) -> dict:
    """
    Downloads bulk data for multiple symbols, persists them to individual Parquet files,
    and intelligently fetches ONLY new missing data if the cache already exists.
    """
    yf_interval = interval
    if interval == '1w': yf_interval = '1wk'
    elif interval == '1m': yf_interval = '1m'
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    data_dict = {}
    missing_symbols = []
    max_date = None
    
    # Check what we already have on disk
    for symbol in symbols:
        parquet_file = os.path.join(DATA_DIR, f"{symbol}_{interval}.parquet")
        if os.path.exists(parquet_file):
            try:
                df = pd.read_parquet(parquet_file)
                if not df.empty:
                    # Set the first column (Date) back as the datetime index
                    df.set_index(df.columns[0], inplace=True)
                    df.index = pd.to_datetime(df.index)
                    data_dict[symbol] = df
                    if max_date is None:
                        max_date = df.index.max()
            except:
                missing_symbols.append(symbol)
        else:
            missing_symbols.append(symbol)
            
    symbols_to_fetch = symbols if force_update else missing_symbols
    
    if symbols_to_fetch:
        # Redirect stderr to prevent the OSError caused by yfinance trying to draw the progress bar on Windows Streamlit
        with contextlib.redirect_stderr(io.StringIO()):
            if force_update and max_date is not None:
                logging.info(f"Force Update requested. Fetching ONLY NEW data since {max_date}...")
                df_new = yf.download(symbols_to_fetch, interval=yf_interval, start=max_date, group_by='ticker', threads=True, progress=False)
            else:
                logging.info(f"Fetching full history for {len(symbols_to_fetch)} symbols...")
                df_new = yf.download(symbols_to_fetch, interval=yf_interval, period=period, group_by='ticker', threads=True, progress=False)
            
        if not df_new.empty:
            for symbol in symbols_to_fetch:
                try:
                    if isinstance(df_new.columns, pd.MultiIndex):
                        if symbol in df_new.columns.levels[0]:
                            sym_df = df_new[symbol].copy()
                        else:
                            continue
                    else:
                        sym_df = df_new.copy()
                            
                    sym_df.dropna(subset=['Close'], inplace=True)
                    if not sym_df.empty:
                        parquet_file = os.path.join(DATA_DIR, f"{symbol}_{interval}.parquet")
                        
                        if symbol in data_dict and force_update:
                            # Append only new data to existing
                            df_old = data_dict[symbol]
                            sym_df = pd.concat([df_old, sym_df])
                            sym_df = sym_df[~sym_df.index.duplicated(keep='last')]
                            
                        # Save back to disk with index reset so Date is stored as a column
                        sym_df_to_save = sym_df.reset_index()
                        sym_df_to_save.to_parquet(parquet_file, engine='pyarrow')
                        data_dict[symbol] = sym_df
                except Exception as e:
                    logging.warning(f"Failed to process {symbol}: {e}")
                    
    logging.info(f"Successfully loaded {len(data_dict)} symbols from cache/download.")
    return data_dict

