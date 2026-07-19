"""
Stooq (stooq.com) -- free, unauthenticated, no API key, no login.
This is the PRIMARY source for bulk historical daily closes on US equities/ETFs.
"""
import io
import time
import requests
import pandas as pd

STOOQ_URL = "https://stooq.com/q/d/l/"

def fetch(symbol: str, start_date: str = None, retries: int = 2, pause: float = 1.0):
    """Return list[(date_str, close_float)] sorted ascending, or None on failure."""
    params = {"s": symbol, "i": "d"}
    if start_date:
        params["d1"] = start_date.replace("-", "")
        params["d2"] = ""  # empty = up to today
    for attempt in range(retries + 1):
        try:
            resp = requests.get(STOOQ_URL, params=params, timeout=30)
            resp.raise_for_status()
            text = resp.text
            if "Exceeded" in text or len(text) < 40:
                print(f"  Stooq: response too short or exceeded for {symbol}")
                return None
            df = pd.read_csv(io.StringIO(text))
            if df.empty or "Close" not in df.columns or "Date" not in df.columns:
                print(f"  Stooq: invalid CSV for {symbol}")
                return None
            df = df[["Date", "Close"]].dropna()
            if df.empty:
                return []
            return list(df.itertuples(index=False, name=None))
        except Exception as e:
            print(f"  Stooq attempt {attempt+1} failed for {symbol}: {e}")
            if attempt < retries:
                time.sleep(pause)
                continue
            return None
    return None

def to_stooq_symbol(ticker: str, kind: str) -> str:
    """Translate our internal ticker convention into a Stooq symbol.
    kind: 'equity' | 'fx' | 'index'
    """
    if kind == "fx":
        return ticker.replace("=X", "").lower()
    if kind == "index":
        return "^" + ticker.lower().lstrip("^")
    return ticker.lower() + ".us"
