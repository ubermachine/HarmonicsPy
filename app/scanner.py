from data_manager_v2 import get_bulk_yahoo_data_v2
from custom_harmonics import get_extrema, find_harmonic_patterns, find_divergences
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)


def run_mass_scan(symbols, interval, period="1y", force_update=False):
    """
    Scans a list of symbols for harmonic patterns and MACD divergences.
    Returns ALL signals found in the dataset, sorted: Patterns first (newest to oldest),
    then Divergences (newest to oldest).
    """
    logging.info(
        f"Initiating mass scan for {len(symbols)} symbols on {interval} timeframe."
    )

    data_dict = get_bulk_yahoo_data_v2(
        symbols, interval, period, force_update=force_update
    )

    patterns_list = []
    divergences_list = []

    for symbol, df in data_dict.items():
        try:
            if len(df) < 50:
                continue

            extrema = get_extrema(df, order=5)
            patterns = find_harmonic_patterns(df, extrema)
            divergences = find_divergences(df, extrema)

            for p in patterns:
                patterns_list.append(
                    {
                        "Symbol": symbol,
                        "Type": "Pattern",
                        "Pattern": p["name"],
                        "Completion Price": p["completion_price"],
                        "PRZ Low": p.get("prz_lo", "-"),
                        "PRZ High": p.get("prz_hi", "-"),
                        "Date": p["date"],
                    }
                )

            close_vals = df["Close"].values
            for d in divergences:
                b_bar = d["points"][1][0]
                # Bolt Optimization: Replaced .iloc inside loop with .values for performance
                divergences_list.append(
                    {
                        "Symbol": symbol,
                        "Type": "Divergence",
                        "Pattern": d["type"],
                        "Completion Price": round(float(close_vals[b_bar]), 2),
                        "PRZ Low": "-",
                        "PRZ High": "-",
                        "Date": d["date"],
                    }
                )

        except Exception as e:
            logging.error(f"Error scanning {symbol}: {e}")

    # Sort each group newest first, then merge: patterns first
    def sort_list(lst):
        return sorted(lst, key=lambda x: x["Date"], reverse=True)

    results = sort_list(patterns_list) + sort_list(divergences_list)

    logging.info(
        f"Scan complete: {len(patterns_list)} patterns, "
        f"{len(divergences_list)} divergences found across {len(data_dict)} symbols."
    )
    return results


if __name__ == "__main__":
    pass
