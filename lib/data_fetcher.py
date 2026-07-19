"""
Centralised data fetcher with Stooq + yfinance fallback.
"""
import pandas as pd
from datetime import datetime
from . import db, stooq_fetcher, yfinance_fetcher

def fetch_price_history(ticker, start_date=None, end_date=None, force_refresh=False):
    """Return list of (date, close). Uses cache unless force_refresh."""
    if not force_refresh:
        cached = db.get_prices(ticker, start_date, end_date)
        if cached:
            return cached

    rows = None
    source = None

    # Try Stooq for equities/ETFs
    symbol = stooq_fetcher.to_stooq_symbol(ticker, "equity")
    print(f"  Trying Stooq for {ticker} with symbol {symbol}")
    rows = stooq_fetcher.fetch(symbol, start_date=start_date)
    if rows is not None and len(rows) > 0:
        source = "stooq"
        print(f"  Stooq returned {len(rows)} rows for {ticker}")
        db.upsert_prices(ticker, rows, source)
        return rows

    # Fallback to yfinance
    print(f"  Stooq failed for {ticker}, falling back to yfinance")
    rows = yfinance_fetcher.fetch_history(ticker, start_date=start_date)
    if rows is not None and len(rows) > 0:
        source = "yfinance"
        print(f"  yfinance returned {len(rows)} rows for {ticker}")
        db.upsert_prices(ticker, rows, source)
        return rows

    print(f"  WARNING: No data found for {ticker}")
    return []
