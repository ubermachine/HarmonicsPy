import requests
import pandas as pd
from io import StringIO
import logging

logging.basicConfig(level=logging.INFO)


def get_nifty500_symbols():
    """
    Fetches the latest Nifty500 list from NSE India and appends .NS for Yahoo Finance.
    Returns a list of ticker symbols.
    """
    url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        logging.info("Fetching Nifty 500 symbols from NSE...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text))

        # The column containing the symbol is typically 'Symbol'
        symbols = df["Symbol"].tolist()

        # Append .NS for Yahoo Finance
        yf_symbols = [f"{sym}.NS" for sym in symbols]

        logging.info(f"Successfully retrieved {len(yf_symbols)} symbols.")
        return yf_symbols
    except Exception as e:
        logging.error(f"Failed to fetch Nifty 500 symbols: {e}")
        # Fallback to a small list if NSE is blocking us
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]


if __name__ == "__main__":
    syms = get_nifty500_symbols()
    print(syms[:10])
