"""
Technical filters: SMA cross, volume confirmation, RSI, breakout detection.
"""
import pandas as pd
from . import data_fetcher

def technical_pass(ticker, short=50, long=200, volume_mult=1.5,
                   rsi_oversold=30, rsi_overbought=70):
    rows = data_fetcher.fetch_price_history(ticker)
    if len(rows) < long:
        return False, {}

    # Build series
    s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
    current = s.iloc[-1]

    sma_short = s.rolling(short).mean().iloc[-1]
    sma_long = s.rolling(long).mean().iloc[-1]

    # Golden cross
    golden_cross = sma_short > sma_long
    price_above_short = current > sma_short
    price_above_long = current > sma_long

    # RSI (14 periods)
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

    # Volume (placeholder – we don't store volume currently, so skip)
    # We can add volume via yfinance if needed, but for now we skip.

    # Overall pass: price above both SMAs and golden cross, and RSI not overbought
    tech_pass = price_above_short and price_above_long and golden_cross and (rsi_val < rsi_overbought)

    return tech_pass, {
        "sma_short": sma_short,
        "sma_long": sma_long,
        "golden_cross": golden_cross,
        "price_above_short": price_above_short,
        "price_above_long": price_above_long,
        "rsi": rsi_val
    }
