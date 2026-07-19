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

def fetch_fundamentals(ticker):
    """Fetch all fundamental metrics from yfinance."""
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
            "trailing_pe": info.get("trailingPE"),
            "price_to_free_cash_flow": info.get("priceToFreeCashFlow"),
            "roe": info.get("returnOnEquity"),
            "free_cash_flow_yield": info.get("freeCashflowYield"),
            "current_ratio": info.get("currentRatio"),
            "interest_coverage": info.get("interestCoverage"),
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"  WARNING: Failed to fetch fundamentals for {ticker}: {e}")
        return None

def fetch_shares_history(ticker, years=5):
    """Fetch historical shares outstanding from quarterly balance sheets."""
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
    except Exception as e:
        print(f"  WARNING: Failed to fetch shares history for {ticker}: {e}")
        return []
