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
    # fetch from yfinance
    data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    if data.empty:
        return []
    rows = [(d.strftime("%Y-%m-%d"), float(c)) for d, c in data["Close"].items()]
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
    # yfinance doesn't provide historical shares easily; we use balance sheet history from Ticker.quarterly_balance_sheet
    try:
        t = yf.Ticker(ticker)
        bs = t.quarterly_balance_sheet
        if bs is not None and "Ordinary Shares Number" in bs.index:
            shares_series = bs.loc["Ordinary Shares Number"].dropna()
            rows = [(d.strftime("%Y-%m-%d"), float(v)) for d, v in shares_series.items()]
            db.upsert_shares_history(ticker, rows)
            return rows
        return []
    except:
        return []
