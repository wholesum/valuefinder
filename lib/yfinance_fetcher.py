"""
yfinance -- unofficial Yahoo Finance client.
Uses curl_cffi session to mimic a real browser and avoid proxy blocks.
"""
import time
import pandas as pd
import yfinance as yf

try:
    from curl_cffi import requests as curl_requests
    _SESSION = curl_requests.Session(impersonate="chrome")
    print("  Using curl_cffi session for yfinance")
except Exception as e:
    print(f"  curl_cffi not available, using default: {e}")
    _SESSION = None

def fetch_history(ticker: str, start_date: str = None, retries: int = 3, pause: float = 2.0):
    """
    Fetch historical daily closes. start_date: "YYYY-MM-DD".
    Returns list of (date_str, close) or None on failure.
    """
    for attempt in range(retries):
        try:
            kwargs = {
                "period": "max",
                "interval": "1d",
                "progress": False,
                "auto_adjust": True,
                "threads": False,
            }
            if _SESSION:
                kwargs["session"] = _SESSION

            data = yf.download(ticker, **kwargs)
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
            print(f"  yfinance attempt {attempt+1}/{retries} failed for {ticker}: {e}")
            if attempt < retries - 1:
                time.sleep(pause * (attempt + 1))
                continue
            return None
    return None
