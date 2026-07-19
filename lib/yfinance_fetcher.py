"""
yfinance -- unofficial Yahoo Finance client.
Uses yf.download with explicit headers and fallbacks.
"""
import time
import pandas as pd
import yfinance as yf
import requests

def fetch_history(ticker: str, start_date: str = None, retries: int = 3, pause: float = 2.0):
    """
    Fetch historical daily closes. start_date: "YYYY-MM-DD".
    Returns list of (date_str, close) or None on failure.
    """
    # Try different strategies
    strategies = [
        {"period": "max", "auto_adjust": True},
        {"period": "10y", "auto_adjust": True},
        {"period": "max", "auto_adjust": False},
    ]
    for attempt in range(retries):
        for strategy in strategies:
            try:
                # Use session with custom headers to avoid blocks
                session = requests.Session()
                session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                })
                data = yf.download(
                    ticker,
                    period=strategy["period"],
                    interval="1d",
                    progress=False,
                    auto_adjust=strategy["auto_adjust"],
                    session=session,
                    timeout=30
                )
                if data.empty:
                    raise ValueError("empty response")

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

                if start_date:
                    close = close[close.index >= pd.to_datetime(start_date)]

                if close.empty:
                    return []

                return list(zip(close.index.strftime("%Y-%m-%d"), close.values.tolist()))

            except Exception as e:
                print(f"  yfinance strategy {strategy} attempt {attempt+1} failed for {ticker}: {e}")
                if attempt < retries - 1:
                    time.sleep(pause * (attempt + 1))
                    continue
                # If all strategies fail, return None
                return None
    return None
