import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta
from nifty_scraper import get_nifty500_symbols
from scanner import run_mass_scan
from pyharmonics_handler import whats_forming_yahoo

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="Nifty 500 Harmonic Scanner", page_icon="📈", layout="wide"
)

st.title("📈 Nifty 500 Harmonic Scanner")
st.markdown(
    "Scan all 500 stocks for **Harmonic Patterns** (Gartley, Bat, Butterfly, Crab, Shark, Cypher) and **MACD Divergences** on Daily or Weekly timeframes."
)

# --- Sidebar ---
st.sidebar.title("⚙️ Scanner Options")
scan_interval = st.sidebar.selectbox(
    "Timeframe",
    ["1d", "1wk"],
    index=0,
    format_func=lambda x: "Daily" if x == "1d" else "Weekly",
)
resync_clicked = st.sidebar.button(
    "🔄 Resync Market Data", help="Fetch only NEW candles and append to cache."
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Cache**: Parquet files on disk. Click Resync for fresh data only."
)

# --- Run Scan ---
run_scan = st.button("🚀 Run Nifty 500 Scan", type="primary", use_container_width=True)

if run_scan or resync_clicked:
    force_update = resync_clicked
    if force_update:
        st.toast("Fetching only new candles since last cache date...")

    with st.spinner("Fetching Nifty 500 symbol list from NSE..."):
        symbols = get_nifty500_symbols()

    with st.spinner(
        f"Scanning {len(symbols)} stocks ({('Daily' if scan_interval == '1d' else 'Weekly')})..."
    ):
        results = run_mass_scan(
            symbols, scan_interval, period="1y", force_update=force_update
        )

    if results:
        df_results = pd.DataFrame(results)
        st.session_state["scan_results"] = df_results
        st.session_state["scan_interval"] = scan_interval
    else:
        st.info("No signals found. Try Resync to download fresh data.")

# --- Results ---
if "scan_results" in st.session_state:
    df_results = st.session_state["scan_results"]
    scan_interval = st.session_state.get("scan_interval", "1d")

    pattern_df = df_results[df_results["Type"] == "Pattern"]
    divergence_df = df_results[df_results["Type"] == "Divergence"]

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Signals", len(df_results))
    m2.metric("🔶 Harmonic Patterns", len(pattern_df))
    m3.metric("📉 MACD Divergences", len(divergence_df))

    st.markdown("---")

    # Filter + date range
    f1, f2, f3 = st.columns([2, 2, 3])
    with f1:
        filter_choice = st.radio(
            "Show:", ["All", "Patterns Only", "Divergences Only"], horizontal=True
        )
    with f2:
        days_back = st.selectbox(
            "Signal Age",
            [30, 60, 90, 180, 365],
            index=2,
            format_func=lambda x: f"Last {x} days",
        )
    with f3:
        pattern_filter = st.multiselect(
            "Pattern type",
            options=[
                "Gartley",
                "Bat",
                "Butterfly",
                "Crab",
                "Shark",
                "Cypher",
                "Bullish Divergence",
                "Bearish Divergence",
            ],
            default=[],
        )

    cutoff_date = (datetime.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    df_display = df_results[df_results["Date"] >= cutoff_date]

    if filter_choice == "Patterns Only":
        df_display = df_display[df_display["Type"] == "Pattern"]
    elif filter_choice == "Divergences Only":
        df_display = df_display[df_display["Type"] == "Divergence"]

    if pattern_filter:
        df_display = df_display[
            df_display["Pattern"].apply(lambda x: any(f in x for f in pattern_filter))
        ]

    st.dataframe(
        df_display.reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="scan_table",
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Pattern": st.column_config.TextColumn("Pattern Name", width="medium"),
            "Completion Price": st.column_config.NumberColumn(
                "Entry Price", format="₹%.2f"
            ),
            "PRZ Low": st.column_config.NumberColumn("PRZ Low", format="₹%.2f"),
            "PRZ High": st.column_config.NumberColumn("PRZ High", format="₹%.2f"),
            "Date": st.column_config.TextColumn("Signal Date", width="small"),
        },
    )

    st.caption(
        f"Showing {len(df_display)} of {len(df_results)} total signals (filtered to last {days_back} days). **Click any row to open its chart.**"
    )

    # Auto-open chart when a row is selected
    selected_rows = (
        st.session_state.get("scan_table", {}).get("selection", {}).get("rows", [])
    )
    if selected_rows:
        row_idx = selected_rows[0]
        inspect_sym = df_display.reset_index(drop=True).iloc[row_idx]["Symbol"]
        inspect_row = df_display.reset_index(drop=True).iloc[row_idx]

        st.markdown("---")
        st.markdown(f"### 🔍 Chart: **{inspect_sym}**")

        # Signal badge
        if inspect_row["Type"] == "Pattern":
            st.success(
                f"🔶 **{inspect_row['Pattern']}** — Entry ₹{inspect_row['Completion Price']} | PRZ ₹{inspect_row['PRZ Low']} – ₹{inspect_row['PRZ High']} | {inspect_row['Date']}"
            )
        else:
            st.info(
                f"📉 **{inspect_row['Pattern']}** on {inspect_row['Date']} at ₹{inspect_row['Completion Price']}"
            )

        # Show all signals for this symbol
        other_signals = df_results[
            (df_results["Symbol"] == inspect_sym)
            & (df_results.index != df_display.reset_index(drop=True).index[row_idx])
        ]
        for _, row in other_signals.iterrows():
            if row["Type"] == "Pattern":
                st.success(
                    f"🔶 **{row['Pattern']}** — ₹{row['Completion Price']} | {row['Date']}"
                )
            else:
                st.info(
                    f"📉 **{row['Pattern']}** on {row['Date']} at ₹{row['Completion Price']}"
                )

        with st.spinner(f"Rendering chart for {inspect_sym}..."):
            inspect_data = whats_forming_yahoo(inspect_sym, scan_interval)

        if "plotly_fig" in inspect_data and inspect_data["plotly_fig"] is not None:
            st.plotly_chart(inspect_data["plotly_fig"], use_container_width=True)
        else:
            st.warning(f"Could not generate chart for {inspect_sym}.")
    else:
        st.caption("👆 Click a row above to view its interactive chart.")
