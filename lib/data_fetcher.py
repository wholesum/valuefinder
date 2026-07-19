"""
Centralised data fetcher – now uses yfinance only (Stooq is blocked on PythonAnywhere).
"""
import pandas as pd
from datetime import datetime
from . import db, yfinance_fetcher

def fetch_price_history(ticker, start_date=None, end_date=None, force_refresh=False):
    """Return list of (date, close). Uses cache unless force_refresh."""
    if not force_refresh:
        cached = db.get_prices(ticker, start_date, end_date)
        if cached:
            return cached

    # Use yfinance only (Stooq is blocked on PythonAnywhere free tier)
    rows = yfinance_fetcher.fetch_history(ticker, start_date=start_date)
    if rows is not None and len(rows) > 0:
        db.upsert_prices(ticker, rows, "yfinance")
        return rows

    print(f"  WARNING: No data found for {ticker}")
    return []
