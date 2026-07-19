"""
Centralised data fetcher. Uses yfinance and caches in SQLite.
"""
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from . import db

def fetch_price_history(ticker, start_date=None, end_date=None, force_refresh=False):
    """Return list of (date, close). Uses cache unless force_refresh."""
    if not force_refresh:
        cached = db.get_prices(ticker, start_date, end_date)
        if cached:
            return cached
    # fetch from yfinance with auto_adjust=True to avoid warning
    data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
    if data.empty:
        return []
    # Handle index as DatetimeIndex or string
    if isinstance(data.index, pd.DatetimeIndex):
        date_strs = data.index.strftime("%Y-%m-%d").tolist()
    else:
        date_strs = data.index.astype(str).tolist()
    # Get Close values, handling possible multi-column returns
    close_series = data["Close"]
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]  # take first column
    close_values = close_series.values.tolist()
    rows = list(zip(date_strs, close_values))
    db.upsert_prices(ticker, rows, "yfinance")
    return rows

def fetch_fundamentals(ticker):
    """Get key fundamental metrics from yfinance Ticker.info()"""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            return None
        return {
            "shares": info.get("sharesOutstanding"),
            "debt_ebitda": info.get("debtToEquity"),  # proxy; actual debt/EBITDA not always available
            "pb": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "gross_margin": info.get("grossMargins"),
            "last_updated": datetime.utcnow().isoformat()
        }
    except:
        return None

def fetch_shares_history(ticker, years=5):
    """Pull historical shares outstanding from quarterly/annual filings (approximated)."""
    try:
        t = yf.Ticker(ticker)
        bs = t.quarterly_balance_sheet
        if bs is not None and "Ordinary Shares Number" in bs.index:
            shares_series = bs.loc["Ordinary Shares Number"].dropna()
            if isinstance(shares_series.index, pd.DatetimeIndex):
                dates = shares_series.index.strftime("%Y-%m-%d").tolist()
            else:
                dates = shares_series.index.astype(str).tolist()
            rows = list(zip(dates, shares_series.values.tolist()))
            db.upsert_shares_history(ticker, rows)
            return rows
        return []
    except:
        return []
