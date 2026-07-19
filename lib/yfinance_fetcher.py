"""
yfinance -- unofficial Yahoo Finance client.
Used for all data fetching (Stooq is blocked on PythonAnywhere free tier).
"""
import time
import pandas as pd
import yfinance as yf

def fetch_history(ticker: str, start_date: str = None, retries: int = 3, pause: float = 2.0):
    """
    Fetch historical daily closes. start_date: "YYYY-MM-DD".
    Returns list of (date_str, close) or None on failure.
    """
    for attempt in range(retries):
        try:
            # Use Ticker.history() – more reliable than yf.download()
            t = yf.Ticker(ticker)
            data = t.history(period="max", interval="1d", auto_adjust=False)
            if data.empty:
                raise ValueError("empty response")

            # Use 'Close' column
            close = data.get("Close")
            if close is None:
                close = data.get("Adj Close")
            if close is None:
                raise ValueError("no close column")

            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]

            close = close.dropna()
            if close.empty:
                raise ValueError("no closes")

            # Filter by start_date if provided
            if start_date:
                close = close[close.index >= pd.to_datetime(start_date)]

            if close.empty:
                return []

            return list(zip(close.index.strftime("%Y-%m-%d"), close.values.tolist()))

        except Exception as e:
            print(f"  yfinance attempt {attempt+1}/{retries} failed for {ticker}: {e}")
            if attempt < retries - 1:
                time.sleep(pause * (attempt + 1))
                continue
            return None
    return None
