"""
Centralised data fetcher using Stooq (primary) and yfinance (fallback).
Also caches results in SQLite.
"""
from datetime import datetime
from . import db
from . import stooq_fetcher, yfinance_fetcher

def fetch_price_history(ticker, start_date=None, end_date=None, force_refresh=False):
    """
    Fetch price history for a ticker. Uses Stooq for equities/ETFs (with '.us' suffix),
    falls back to yfinance. Caches in SQLite unless force_refresh=True.
    """
    # If we have cached data and not forcing refresh, return it
    if not force_refresh:
        cached = db.get_prices(ticker, start_date, end_date)
        if cached:
            return cached

    # Determine source: try Stooq first for equities (ticker like 'XLE', 'OIH')
    # We'll use 'equity' kind for all our ETFs, but if it fails we fall back to yfinance
    rows = None
    used_source = None

    # Try Stooq (works for US stocks/ETFs)
    symbol = stooq_fetcher.to_stooq_symbol(ticker, "equity")
    rows = stooq_fetcher.fetch(symbol, start_date=start_date)
    if rows is not None:
        used_source = "stooq"
    else:
        # Fallback to yfinance
        rows = yfinance_fetcher.fetch_history(ticker, start_date=start_date)
        if rows is not None:
            used_source = "yfinance"

    if rows is None:
        return []

    # Cache the data
    db.upsert_prices(ticker, rows, used_source)
    return rows

def fetch_fundamentals(ticker):
    """Get key fundamental metrics from yfinance Ticker.info()"""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            return None
        return {
            "shares": info.get("sharesOutstanding"),
            "debt_ebitda": info.get("debtToEquity"),
            "pb": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "gross_margin": info.get("grossMargins"),
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception:
        return None

def fetch_shares_history(ticker, years=5):
    """Pull historical shares outstanding from quarterly/annual filings."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        bs = t.quarterly_balance_sheet
        if bs is not None and "Ordinary Shares Number" in bs.index:
            shares_series = bs.loc["Ordinary Shares Number"].dropna()
            if isinstance(shares_series.index, pd.DatetimeIndex):
                dates = shares_series.index.strftime("%Y-%m-%d").tolist()
            else:
                dates = shares_series.index.astype(str).tolist()
            rows = list(zip(dates, shares_series.tolist()))
            db.upsert_shares_history(ticker, rows)
            return rows
        return []
    except Exception:
        return []
