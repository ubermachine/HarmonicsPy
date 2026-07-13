import yfinance as yf
import duckdb
import os
import re
import pandas as pd
import logging
import streamlit as st
import contextlib
import io

logging.basicConfig(level=logging.INFO)

DATA_DIR = "data_cache"


def _safe_filename(symbol: str) -> str:
    """Sanitise symbol name for use as a filename (removes &, /, etc.)."""
    return re.sub(r'[^\w\-.]', '_', symbol)


class CachedCandleData:
    def __init__(self, symbol, interval):
        self.symbol   = symbol
        self.interval = interval
        self.df       = None


def _yf_interval(interval: str) -> str:
    if interval == '1w':  return '1wk'
    if interval == '1m':  return '1m'
    return interval


# ---------------------------------------------------------------------------
# Single-symbol fetch (used for per-stock chart rendering)
# ---------------------------------------------------------------------------

def _get_data_path(symbol: str, interval: str = "1d") -> str:
    """Resolves Parquet file path from local data lake or remote GitHub URL."""
    symbol = symbol.upper().strip()
    is_sector = symbol in [
        "^NSEI", "^NSEBANK", "^CNXAUTO", "^CNXIT", "^CNXPHARMA", 
        "^CNXMETAL", "^CNXENERGY", "^CNXFMCG", "^CNXMEDIA", "^CNXREALTY", 
        "^CNXPSUBANK", "^CNXINFRA", "NIFTY_FIN_SERVICE.NS", 
        "NIFTY_OIL_AND_GAS.NS", "^CNXCONSUM"
    ]
    filename = "SectorDailyBars.parquet" if is_sector else "DailyBars.parquet"
    
    # Check local paths first
    local_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "market-data-lake", "data", filename)),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "market-data-lake", "data", filename)),
        os.path.join("D:\\antigravity_sandbox\\market-data-lake\\data", filename)
    ]
    for path in local_paths:
        if os.path.exists(path):
            return path.replace("\\", "/")
            
    # Default to raw GitHub URL
    github_user = os.getenv("GITHUB_USER", "HP")
    github_repo = os.getenv("GITHUB_REPO", "market-data-lake")
    return f"https://raw.githubusercontent.com/{github_user}/{github_repo}/main/data/{filename}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol: str, interval: str, candles: int = 1000,
                   force_update: bool = False) -> CachedCandleData:
    """
    Loads OHLCV data for a single symbol from the central Parquet data lake.
    Queries the file (local path or remote URL) and filters by Ticker.
    """
    data_path = _get_data_path(symbol, interval)
    
    try:
        if data_path.startswith("http"):
            # Use pandas read_parquet directly for remote files (prevents DuckDB httpfs segfaults on Streamlit Cloud)
            df_all = pd.read_parquet(data_path)
            df = df_all[df_all['Ticker'] == symbol][['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].sort_values('Date').tail(candles).reset_index(drop=True)
        else:
            con = duckdb.connect()
            try:
                # DuckDB streams the candles directly from the Parquet file
                query = f"""
                    SELECT * FROM (
                        SELECT Date, Open, High, Low, Close, Volume FROM read_parquet('{data_path}')
                        WHERE Ticker = '{symbol}'
                        ORDER BY Date DESC
                        LIMIT {candles}
                    )
                    ORDER BY Date ASC
                """
                df = con.execute(query).df()
            finally:
                con.close()
                
        if df.empty:
            raise ValueError(f"No data returned for symbol: {symbol} inside the file")
    except Exception as e:
        logging.warning(f"Failed to load '{symbol}' from data lake: {e}. Falling back to dynamic yfinance download...")
        try:
            import yfinance as yf
            yfi = interval
            if interval == '1w':
                yfi = '1wk'
            elif interval == '1m':
                yfi = '1mo'
            period = "60d" if (yfi.endswith('m') or yfi.endswith('h')) else "max"
            
            df_yf = yf.download(symbol, interval=yfi, period=period, progress=False)
            if df_yf.empty:
                raise ValueError(f"yfinance returned empty data for {symbol}")
                
            if isinstance(df_yf.columns, pd.MultiIndex):
                df_yf.columns = df_yf.columns.get_level_values(0)
                
            df = df_yf.reset_index()
            
            # Format and select columns
            rename_map = {}
            for col in df.columns:
                col_lower = str(col).lower()
                if col_lower in ['date', 'datetime']:
                    rename_map[col] = 'Date'
                elif col_lower in ['open', 'high', 'low', 'close', 'volume']:
                    rename_map[col] = col_lower.capitalize()
            df = df.rename(columns=rename_map)
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as yf_err:
            raise ValueError(f"Failed to load data for '{symbol}' from data lake AND yfinance: {yf_err}")

    df.set_index(df.columns[0], inplace=True)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    cd = CachedCandleData(symbol, interval)
    cd.df = df
    return cd


def get_bulk_yahoo_data_v2(symbols: list, interval: str,
                           period: str = "1y",
                           force_update: bool = False) -> dict:
    """
    Loads OHLCV data for a list of symbols from the central data lake.
    """
    data_dict = {}
    for sym in symbols:
        try:
            cd = get_yahoo_data(sym, interval)
            data_dict[sym] = cd.df
        except Exception as e:
            logging.warning(f"Failed to load bulk data for {sym}: {e}")
    return data_dict

