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

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(symbol: str, interval: str, candles: int = 1000,
                   force_update: bool = False) -> CachedCandleData:
    """
    Fetches Yahoo Finance data for a single symbol.
    Caches to Parquet on disk; queries via DuckDB.
    @st.cache_data provides a 1-hour in-memory layer on top.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    safe    = _safe_filename(symbol)
    parquet = os.path.join(DATA_DIR, f"{safe}_{interval}.parquet")
    yfi     = _yf_interval(interval)

    file_exists = os.path.exists(parquet)

    if not file_exists or force_update:
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                if file_exists and force_update:
                    df_old   = pd.read_parquet(parquet)
                    time_col = df_old.columns[0]
                    max_date = df_old[time_col].max()
                    logging.info(f"{symbol}: updating from {max_date}")

                    df_new = yf.download(symbol, interval=yfi,
                                         start=max_date, progress=False)
                    if not df_new.empty:
                        if isinstance(df_new.columns, pd.MultiIndex):
                            df_new.columns = df_new.columns.get_level_values(0)
                        df_new.reset_index(inplace=True)
                        df_new.rename(columns={df_new.columns[0]: time_col},
                                      inplace=True)
                        combined = (pd.concat([df_old, df_new])
                                    .drop_duplicates(subset=[time_col], keep='last'))
                        combined.to_parquet(parquet, engine='pyarrow')
                else:
                    period = "60d" if (yfi.endswith('m') or yfi.endswith('h')) else "max"
                    df = yf.download(symbol, interval=yfi, period=period,
                                     progress=False)
                    if df.empty:
                        raise ValueError(f"No data returned for {symbol}")
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df.reset_index(inplace=True)
                    df.to_parquet(parquet, engine='pyarrow')
                    logging.info(f"{symbol}: cached to {parquet}")
        except Exception as e:
            logging.error(f"{symbol}: download failed — {e}")
            if not file_exists:
                raise Exception("No cached data available.")

    # Read via DuckDB (fast columnar query, returns N most recent candles)
    query = f"""
        SELECT * FROM (
            SELECT * FROM '{parquet}'
            ORDER BY 1 DESC
            LIMIT {candles}
        )
        ORDER BY 1 ASC
    """
    df = duckdb.query(query).df()
    df.set_index(df.columns[0], inplace=True)
    df.index = pd.to_datetime(df.index)

    cd    = CachedCandleData(symbol, interval)
    cd.df = df
    return cd


# ---------------------------------------------------------------------------
# Bulk fetch (used by mass scanner)
#
# Design: Parquet files on disk ARE the persistent cache.
# NO @st.cache_data wrapper here — it would create a redundant in-memory
# copy of 500 DataFrames (hundreds of MB) and shadow the disk cache,
# making delta-sync invisible to the app until TTL expires.
#
# Instead, the SCAN RESULTS (patterns list) are cached in session_state
# by main.py, which is the correct granularity.
# ---------------------------------------------------------------------------

def get_bulk_yahoo_data_v2(symbols: list, interval: str,
                           period: str = "1y",
                           force_update: bool = False) -> dict:
    """
    Loads OHLCV data for a list of symbols from the Parquet cache.
    Only fetches from Yahoo Finance for:
      - Symbols with no local Parquet file (first run)
      - Symbols where force_update=True (delta: fetches only NEW candles
        per-symbol based on that symbol's own max_date)
    """
    yfi = _yf_interval(interval)
    os.makedirs(DATA_DIR, exist_ok=True)

    data_dict      = {}   # symbol → DataFrame (DatetimeIndex)
    missing        = []   # no parquet file at all
    per_sym_maxdate = {}  # symbol → its own last date (for precise delta fetch)

    # 1. Load what we already have from disk
    for sym in symbols:
        parquet = os.path.join(DATA_DIR, f"{_safe_filename(sym)}_{interval}.parquet")
        if os.path.exists(parquet):
            try:
                df = pd.read_parquet(parquet)
                df.set_index(df.columns[0], inplace=True)
                df.index = pd.to_datetime(df.index)
                if not df.empty:
                    data_dict[sym]       = df
                    per_sym_maxdate[sym] = df.index.max()
            except Exception as e:
                logging.warning(f"{sym}: corrupt parquet — will re-download. ({e})")
                missing.append(sym)
        else:
            missing.append(sym)

    # 2. Decide what to fetch
    if force_update:
        # Delta fetch: only new candles per symbol, using EACH symbol's own max_date
        # Group symbols by their max_date to minimise API calls
        date_groups: dict = {}
        for sym in symbols:
            md = per_sym_maxdate.get(sym)
            key = str(md.date()) if md is not None else "full"
            date_groups.setdefault(key, []).append(sym)

        for date_key, group_syms in date_groups.items():
            logging.info(f"Delta fetch for {len(group_syms)} symbols since {date_key}")
            start = date_key if date_key != "full" else None
            with contextlib.redirect_stderr(io.StringIO()):
                if start:
                    df_new = yf.download(group_syms, interval=yfi,
                                         start=start, group_by='ticker',
                                         threads=True, progress=False)
                else:
                    df_new = yf.download(group_syms, interval=yfi,
                                         period=period, group_by='ticker',
                                         threads=True, progress=False)
            _merge_and_save(df_new, group_syms, interval, data_dict)

    elif missing:
        # First-time download for symbols with no local file
        logging.info(f"First download for {len(missing)} new symbols...")
        with contextlib.redirect_stderr(io.StringIO()):
            df_new = yf.download(missing, interval=yfi, period=period,
                                 group_by='ticker', threads=True, progress=False)
        _merge_and_save(df_new, missing, interval, data_dict)

    logging.info(f"Bulk load complete: {len(data_dict)} symbols ready.")
    return data_dict


def _merge_and_save(df_new: pd.DataFrame, symbols: list,
                    interval: str, data_dict: dict):
    """Extract per-symbol DataFrames from a bulk download, merge with existing, save."""
    if df_new is None or df_new.empty:
        return

    for sym in symbols:
        try:
            if isinstance(df_new.columns, pd.MultiIndex):
                if sym not in df_new.columns.get_level_values(0):
                    continue
                sym_df = df_new[sym].copy()
            else:
                sym_df = df_new.copy()

            sym_df.dropna(subset=['Close'], inplace=True)
            if sym_df.empty:
                continue

            sym_df.index = pd.to_datetime(sym_df.index)

            # Merge with existing cached data (for delta appends)
            if sym in data_dict:
                sym_df = pd.concat([data_dict[sym], sym_df])
                sym_df = sym_df[~sym_df.index.duplicated(keep='last')]
                sym_df.sort_index(inplace=True)

            parquet = os.path.join(DATA_DIR,
                                   f"{_safe_filename(sym)}_{interval}.parquet")
            sym_df.reset_index().to_parquet(parquet, engine='pyarrow')
            data_dict[sym] = sym_df

        except Exception as e:
            logging.warning(f"{sym}: failed to process — {e}")
