# 📈 HarmonicsPy — Nifty 500 Harmonic Pattern Scanner

A high-performance, open-source scanner for detecting **Harmonic Patterns** (Gartley, Bat, Butterfly, Crab, Deep Crab, Shark, Cypher) and **MACD Divergences** across all **500 stocks** in the Nifty 500 index — built with Python, Streamlit, and Parquet-based incremental caching.

![Scanner Preview](https://raw.githubusercontent.com/ubermachine/HarmonicsPy/main/docs/preview.png)

---

## ✨ Features

- 🔍 **Full Nifty 500 scan** on Daily (`1d`) or Weekly (`1wk`) timeframes
- 🔶 **7 Harmonic Patterns** with mathematically correct Fibonacci ratio checks:
  - Gartley, Bat, Butterfly, Crab, Deep Crab, Shark, Cypher
- 📉 **MACD Regular Divergence** detection (Bullish & Bearish)
- 🟩 **PRZ (Potential Reversal Zone)** calculated and highlighted on charts
- ⚡ **Lightning-fast repeated scans** — data is cached as Parquet files; Yahoo Finance is only called for missing candles
- 🔄 **One-click delta sync** — fetches only new candles since the last cache date
- 📊 **Interactive Plotly charts** — click any row in the results table to instantly render the annotated XABCD chart
- 🔎 **Flexible filtering** — filter by pattern type, signal age, and pattern name

---

## 🏗️ Architecture

```
HarmonicsPy/
│
├── app/
│   ├── main.py                  # Streamlit UI — scanner, filters, row-click charts
│   ├── custom_harmonics.py      # Core math engine: extrema, Fibonacci ratios, patterns
│   ├── scanner.py               # Mass scan orchestrator (500 symbols)
│   ├── data_manager_v2.py       # Parquet cache + incremental Yahoo Finance fetch
│   ├── nifty_scraper.py         # Fetches Nifty 500 symbol list from NSE live
│   └── pyharmonics_handler.py   # Per-symbol chart generation wrapper
│
├── data_cache/                  # Auto-created: individual .parquet files per symbol
├── requirements.txt
└── README.md
```

---

## 🧮 Harmonic Pattern Logic

All patterns are detected using the industry-standard **5-point XABCD** structure with correct Fibonacci ratio definitions:

| Ratio | Formula | Description |
|-------|---------|-------------|
| `AB/XA` | `\|AB\| / \|XA\|` | How far B retraces XA from A |
| `BC/AB` | `\|BC\| / \|AB\|` | How far C retraces/extends AB from B |
| `CD/BC` | `\|CD\| / \|BC\|` | How far D extends/retraces BC from C |
| `AD/XA` | `\|A − D\| / \|XA\|` | **Correct**: D's retracement from A (NOT \|D−X\|/\|XA\|) |

> **Note for Cypher**: D is validated as `\|C − D\| / \|X − C\|` ≈ 0.786 (retracement of XC, not XA)

### Pattern Fibonacci Ranges

| Pattern | AB/XA | BC/AB | CD/BC | AD/XA |
|---------|-------|-------|-------|-------|
| Gartley | 0.566–0.670 | 0.382–0.886 | 1.130–1.618 | 0.750–0.820 |
| Bat | 0.382–0.501 | 0.382–0.886 | 1.618–2.618 | 0.850–0.910 |
| Butterfly | 0.750–0.820 | 0.382–0.886 | 1.618–2.618 | 1.240–1.360 |
| Crab | 0.382–0.618 | 0.382–0.886 | 2.240–3.618 | 1.570–1.660 |
| Deep Crab | 0.882–0.900 | 0.382–0.886 | 2.000–3.618 | 1.570–1.660 |
| Shark | 0.447–0.618 | 1.130–1.618 | 0.886–1.130 | 0.882–1.130 |
| Cypher | 0.382–0.618 | 1.130–1.414 | — | DC/XC: 0.750–0.820 |

---

## ⚡ Data & Caching

```
First Run   → Download 1 year of daily history for all 500 stocks → Save as Parquet
Next Runs   → Load from local Parquet (milliseconds, no network)
Resync      → Read max_date from each Parquet → Fetch ONLY new candles → Append
```

- Each symbol stored as `data_cache/<SYMBOL>_<INTERVAL>.parquet`
- DuckDB is used for analytical queries within the single-symbol charting flow
- `@st.cache_data` wraps the bulk loader for Streamlit-level in-memory caching on top

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/ubermachine/HarmonicsPy.git
cd HarmonicsPy
pip install -r requirements.txt
```

### Run the App

```bash
streamlit run app/main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### First Scan

1. Select **Timeframe** in the sidebar (Daily or Weekly)
2. Click **🚀 Run Nifty 500 Scan**
3. Wait for the initial download (~1–2 minutes for 500 stocks)
4. Use the **filter bar** to narrow results by type, pattern name, or date range
5. **Click any row** in the results table to instantly open its annotated chart

### Updating Data

- Click **🔄 Resync Market Data** in the sidebar — only fetches new candles since your last cache date

---

## 📦 Requirements

```
streamlit>=1.35
yfinance>=0.2.40
pandas>=2.0
pyarrow>=14.0
duckdb>=0.9
scipy>=1.11
plotly>=5.18
ta>=0.11
requests>=2.31
```

---

## 📂 Key Files

| File | Purpose |
|------|---------|
| [`app/custom_harmonics.py`](app/custom_harmonics.py) | Extrema detection, Fibonacci pattern matching, MACD divergence, Plotly charting |
| [`app/scanner.py`](app/scanner.py) | Mass scan orchestrator; calls data layer and math engine for all 500 symbols |
| [`app/data_manager_v2.py`](app/data_manager_v2.py) | Parquet read/write, incremental Yahoo Finance fetch, Streamlit caching |
| [`app/nifty_scraper.py`](app/nifty_scraper.py) | Fetches live Nifty 500 constituents from NSE |
| [`app/main.py`](app/main.py) | Streamlit UI: scan, filter, row-click chart |

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first for major changes.

---

## ⚠️ Disclaimer

This tool is for educational and research purposes only. It is **not financial advice**. Always do your own due diligence before trading.

---

## 📄 License

MIT License
