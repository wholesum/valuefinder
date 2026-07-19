"""
yfinance -- unofficial Yahoo Finance client.
Used as fallback for commodities, futures, and any tickers Stooq can't handle.
"""
import time
import pandas as pd
import yfinance as yf

try:
    from curl_cffi import requests as curl_requests
    _SESSION = curl_requests.Session(impersonate="chrome")
except Exception:
    _SESSION = None

def fetch_history(ticker: str, period: str = "max", start_date: str = None, retries: int = 2, pause: float = 2.0):
    """
    start_date: "YYYY-MM-DD" -- fetches from that date forward.
    """
    for attempt in range(retries + 1):
        try:
            if start_date:
                kwargs = dict(start=start_date, interval="1d", progress=False, timeout=30)
            else:
                kwargs = dict(period=period, interval="1d", progress=False, timeout=30)
            if _SESSION:
                kwargs["session"] = _SESSION
            data = yf.download(ticker, **kwargs)
            if data is None or data.empty:
                raise ValueError("empty response")
            # Use 'Adj Close' if available (auto_adjust=True), else fallback to 'Close'
            close = data.get("Adj Close")
            if close is None:
                close = data.get("Close")
            if close is None:
                raise ValueError("no close column")
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = close.dropna()
            if close.empty:
                raise ValueError("no closes")
            return list(zip(close.index.strftime("%Y-%m-%d"), close.values.tolist()))
        except Exception as e:
            if attempt < retries:
                time.sleep(pause)
                continue
            return None
    return None
