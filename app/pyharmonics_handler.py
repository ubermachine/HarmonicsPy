from data_manager_v2 import get_yahoo_data
from custom_harmonics import (
    get_extrema,
    find_harmonic_patterns,
    find_divergences,
    plot_chart,
)
import logging

logging.basicConfig(level=logging.INFO)


def analyze_data(cd, limit_to=-1):
    df = cd.df
    symbol = cd.symbol

    extrema = get_extrema(df, order=5)

    patterns = find_harmonic_patterns(df, extrema)
    divergences = find_divergences(df, extrema)

    if limit_to != -1:
        patterns = patterns[-limit_to:]
        divergences = divergences[-limit_to:]

    fig = plot_chart(df, patterns, divergences, symbol)

    # We return a dict with the Plotly figure object, patterns, and divergences.
    # The main.py app will handle the Plotly figure rendering.

    return {
        "patterns": [
            p["name"]
            + " completed at "
            + str(p["completion_price"])
            + " on "
            + p["date"]
            for p in patterns
        ],
        "divergences": [d["type"] + " on " + d["date"] for d in divergences],
        "plotly_fig": fig,
    }


def whats_new_yahoo(symbol, interval, limit_to=-1, candles=1000, force_update=False):
    yc = get_yahoo_data(symbol, interval, candles, force_update=force_update)
    return analyze_data(yc, limit_to=limit_to)


def whats_forming_yahoo(
    symbol,
    interval,
    limit_to=10,
    percent_complete=0.8,
    candles=1000,
    force_update=False,
):
    # For custom logic, we can just return whats_new_yahoo since we don't have separate "forming" vs "formed" logic yet.
    # "Forming" would mean the D leg hasn't fully completed, but our simple logic just looks for 5 points.
    return whats_new_yahoo(symbol, interval, limit_to, candles, force_update)


if __name__ == "__main__":
    pass
