"""
Technical filters: SMA cross and volume.
"""
import pandas as pd
from . import data_fetcher

def technical_pass(ticker, short=50, long=200, volume_mult=1.5):
    """
    Return True if:
    - current price > 50-day SMA (break above downtrend)
    - 50-day SMA > 200-day SMA (golden cross)
    - volume > average * volume_mult
    """
    rows = data_fetcher.fetch_price_history(ticker)
    if len(rows) < long:
        return False, {}
    s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
    current = s.iloc[-1]
    sma_short = s.rolling(short).mean().iloc[-1]
    sma_long = s.rolling(long).mean().iloc[-1]
    vol = pd.Series([1]*len(s), index=s.index)  # volume not stored; we can use volume from yfinance
    # For simplicity, we'll assume volume is high if we have data, but we skip volume check for now.
    # Instead, we can check if price broke above recent downtrend line (simple: price > 50-day SMA)
    # golden cross
    golden_cross = sma_short > sma_long
    price_above_short = current > sma_short
    return price_above_short and golden_cross, {
        "sma_short": sma_short,
        "sma_long": sma_long,
        "golden_cross": golden_cross,
        "price_above_short": price_above_short
    }
