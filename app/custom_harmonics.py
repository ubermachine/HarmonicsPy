import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import plotly.graph_objects as go
from ta.trend import MACD

# ---------------------------------------------------------------------------
# Extrema Detection
# ---------------------------------------------------------------------------


def get_extrema(df, order=5):
    """
    Detect alternating swing highs (type=1) and lows (type=-1).
    Returns list of (bar_index, price, type) tuples in chronological order.
    """
    high_vals = df["High"].values
    low_vals = df["Low"].values

    highs = argrelextrema(high_vals, np.greater, order=order)[0]
    lows = argrelextrema(low_vals, np.less, order=order)[0]

    raw = [(h, float(high_vals[h]), 1) for h in highs]
    raw += [(l, float(low_vals[l]), -1) for l in lows]
    raw.sort(key=lambda x: x[0])

    # Enforce strictly alternating H/L; always keep the more extreme one
    filtered = []
    for pt in raw:
        if not filtered:
            filtered.append(pt)
        elif filtered[-1][2] == pt[2]:  # same type → replace if more extreme
            if pt[2] == 1 and pt[1] > filtered[-1][1]:
                filtered[-1] = pt
            elif pt[2] == -1 and pt[1] < filtered[-1][1]:
                filtered[-1] = pt
        else:
            filtered.append(pt)
    return filtered


# ---------------------------------------------------------------------------
# Fibonacci helpers
# ---------------------------------------------------------------------------

# Function in_range removed in favor of inline comparisons.


# ---------------------------------------------------------------------------
# Harmonic Pattern Definitions
# ---------------------------------------------------------------------------
#
# All ratios use the STANDARD definitions:
#
#   AB_XA  = |AB| / |XA|          (how far B retraces XA from A)
#   BC_AB  = |BC| / |AB|          (how far C retraces / extends AB from B)
#   CD_BC  = |CD| / |BC|          (how far D extends / retraces BC from C)
#   AD_XA  = |A - D| / |XA|       ← measured from A back to D  (NOT D-X)
#
# For Cypher only, D is validated against XC not XA:
#   DC_XC  = |C - D| / |X - C|    (D retraces the XC swing from C)
#
# Sources: Scott Carney "Harmonic Trading Vol.1 & 2", widely used ranges.
# ---------------------------------------------------------------------------

HARMONIC_RULES = {
    # name: (AB_lo, AB_hi, BC_lo, BC_hi, CD_lo, CD_hi, AD_lo, AD_hi, use_cypher_d)
    "Gartley": (0.566, 0.670, 0.382, 0.886, 1.130, 1.618, 0.750, 0.820, False),
    "Bat": (0.382, 0.501, 0.382, 0.886, 1.618, 2.618, 0.850, 0.910, False),
    "Butterfly": (0.750, 0.820, 0.382, 0.886, 1.618, 2.618, 1.240, 1.360, False),
    "Crab": (0.382, 0.618, 0.382, 0.886, 2.240, 3.618, 1.570, 1.660, False),
    "Deep Crab": (0.882, 0.900, 0.382, 0.886, 2.000, 3.618, 1.570, 1.660, False),
    "Shark": (0.447, 0.618, 1.130, 1.618, 0.886, 1.130, 0.882, 1.130, False),
    # Cypher: D is validated as 0.786 retrace of XC (not XA)
    "Cypher": (0.382, 0.618, 1.130, 1.414, 0.000, 9.999, 0.750, 0.820, True),
}


def find_harmonic_patterns(df, extrema):
    """
    Scan all 5-point XABCD sequences and classify harmonic patterns
    using correct Fibonacci ratio definitions.
    """
    patterns = []
    n = len(extrema)
    if n < 5:
        return patterns

    for i in range(n - 4):
        X, A, B, C, D = extrema[i : i + 5]

        # Compute signed leg moves
        XA = A[1] - X[1]
        AB = B[1] - A[1]
        BC = C[1] - B[1]
        CD = D[1] - C[1]

        if abs(XA) < 1e-9 or abs(AB) < 1e-9 or abs(BC) < 1e-9:
            continue

        # Structural check: legs must alternate direction
        if not (
            np.sign(XA) != np.sign(AB)
            and np.sign(AB) != np.sign(BC)
            and np.sign(BC) != np.sign(CD)
        ):
            continue

        # Ratio calculations — all using correct definitions
        AB_XA = abs(AB / XA)
        BC_AB = abs(BC / AB)
        CD_BC = abs(CD / BC)
        AD_XA = abs((A[1] - D[1]) / XA)  # ← correct: |A-D| / |XA|

        XC = C[1] - X[1]
        DC_XC = abs((C[1] - D[1]) / XC) if abs(XC) > 1e-9 else 0.0  # for Cypher

        matched = None
        for name, (
            ab_lo,
            ab_hi,
            bc_lo,
            bc_hi,
            cd_lo,
            cd_hi,
            ad_lo,
            ad_hi,
            cypher,
        ) in HARMONIC_RULES.items():
            if not (ab_lo <= AB_XA <= ab_hi):
                continue
            if not (bc_lo <= BC_AB <= bc_hi):
                continue
            if not (cd_lo <= CD_BC <= cd_hi):
                continue

            if cypher:
                # Cypher: D validated against 0.786 retracement of XC
                if 0.750 <= DC_XC <= 0.820:
                    matched = name
                    break
            else:
                if ad_lo <= AD_XA <= ad_hi:
                    matched = name
                    break

        if matched:
            direction = "Bullish" if D[2] == -1 else "Bearish"
            d_price = D[1]
            patterns.append(
                {
                    "name": f"{direction} {matched}",
                    "points": [X, A, B, C, D],
                    "completion_price": round(d_price, 2),
                    "date": df.index[D[0]].strftime("%Y-%m-%d"),
                    "prz_lo": round(d_price * 0.988, 2),
                    "prz_hi": round(d_price * 1.012, 2),
                    "ratios": {
                        "AB/XA": round(AB_XA, 3),
                        "BC/AB": round(BC_AB, 3),
                        "CD/BC": round(CD_BC, 3),
                        "AD/XA": round(AD_XA, 3),
                    },
                }
            )

    return patterns


# ---------------------------------------------------------------------------
# MACD Divergence Detection
# ---------------------------------------------------------------------------


def find_divergences(df, extrema):
    """Detect classic Regular MACD Divergences on swing highs and lows."""
    divergences = []

    macd_line = MACD(close=df["Close"]).macd()
    macd_vals = macd_line.values

    for i in range(len(extrema) - 2):
        A, B = extrema[i], extrema[i + 2]

        if A[2] != B[2]:
            continue

        macd_A = macd_vals[A[0]]
        macd_B = macd_vals[B[0]]
        if pd.isna(macd_A) or pd.isna(macd_B):
            continue

        price_diff = B[1] - A[1]
        macd_diff = float(macd_B) - float(macd_A)

        if (
            A[2] == 1 and price_diff > 0 and macd_diff < 0
        ):  # Bearish: higher high, lower MACD
            divergences.append(
                {
                    "type": "Bearish Divergence",
                    "points": [A, B],
                    "date": df.index[B[0]].strftime("%Y-%m-%d"),
                }
            )
        elif (
            A[2] == -1 and price_diff < 0 and macd_diff > 0
        ):  # Bullish: lower low, higher MACD
            divergences.append(
                {
                    "type": "Bullish Divergence",
                    "points": [A, B],
                    "date": df.index[B[0]].strftime("%Y-%m-%d"),
                }
            )

    return divergences


# ---------------------------------------------------------------------------
# Chart Plotting
# ---------------------------------------------------------------------------

PATTERN_COLOR = {"Bullish": "#00e676", "Bearish": "#ff1744"}


def plot_chart(df, patterns, divergences, symbol):
    """
    Interactive Plotly candlestick chart with annotated XABCD harmonic patterns
    and MACD divergence lines.
    """
    fig = go.Figure()

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Price",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        )
    )

    # XABCD Harmonic Patterns
    for idx, p in enumerate(patterns):
        pts = p["points"]
        direction = "Bullish" if "Bullish" in p["name"] else "Bearish"
        color = PATTERN_COLOR[direction]
        labels = ["X", "A", "B", "C", "D"]

        x_vals = [df.index[pt[0]] for pt in pts]
        y_vals = [pt[1] for pt in pts]

        # Pattern line with XABCD labels
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines+markers+text",
                name=p["name"],
                text=labels,
                textposition="top center",
                textfont=dict(size=11, color=color),
                line=dict(color=color, width=2, dash="dot"),
                marker=dict(
                    size=9, color=color, symbol="circle-open", line=dict(width=2)
                ),
                legendgroup=f"pattern_{idx}",
            )
        )

        # PRZ shaded box at the D completion zone
        prz_lo = p.get("prz_lo", y_vals[-1] * 0.988)
        prz_hi = p.get("prz_hi", y_vals[-1] * 1.012)
        ratios = p.get("ratios", {})
        ratio_text = "  |  ".join([f"{k}={v}" for k, v in ratios.items()])
        fig.add_hrect(
            y0=prz_lo,
            y1=prz_hi,
            fillcolor=color,
            opacity=0.15,
            line_width=0,
            annotation_text=f"PRZ {p['name']}<br>{ratio_text}",
            annotation_position="right",
            annotation_font=dict(color=color, size=9),
        )

    # Divergence lines
    for idx, d in enumerate(divergences):
        pts = d["points"]
        color = "#ff1744" if "Bearish" in d["type"] else "#00e676"
        x_vals = [df.index[pt[0]] for pt in pts]
        y_vals = [pt[1] for pt in pts]

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines+markers",
                name=d["type"],
                line=dict(color=color, width=2, dash="dash"),
                marker=dict(size=8, color=color, symbol="diamond"),
                showlegend=(idx == 0),
                legendgroup=d["type"],
            )
        )

    fig.update_layout(
        title=dict(
            text=f"<b>{symbol}</b> — Harmonic Patterns & Divergences",
            font=dict(size=18),
        ),
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        plot_bgcolor="#1a1a2e",
        paper_bgcolor="#1a1a2e",
        height=600,
    )

    return fig
