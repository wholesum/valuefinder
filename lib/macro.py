"""
Macro check: compare BCOM/SP500 and BCOM/Gold percentiles.
"""
import pandas as pd
import numpy as np
from . import data_fetcher, db

def get_macro_data(commodity_ticker="GSG", stock_ticker="^GSPC", gold_ticker="GC=F", lookback_years=20):
    end = pd.Timestamp.today()
    start = end - pd.DateOffset(years=lookback_years)
    start_str = start.strftime("%Y-%m-%d")
    # fetch monthly data (resample)
    def get_monthly(ticker):
        rows = data_fetcher.fetch_price_history(ticker, start_str)
        if not rows:
            return pd.Series()
        s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
        return s.resample("ME").last().dropna()
    
    bcom = get_monthly(commodity_ticker)
    spx = get_monthly(stock_ticker)
    gold = get_monthly(gold_ticker)
    if bcom.empty or spx.empty or gold.empty:
        return None, None, None
    # align dates
    common = bcom.index.intersection(spx.index).intersection(gold.index)
    if len(common) < 60:
        return None, None, None
    bcom = bcom[common]
    spx = spx[common]
    gold = gold[common]
    ratio1 = bcom / spx
    ratio2 = bcom / gold
    return ratio1, ratio2, common

def macro_pass(percentile_threshold=20):
    r1, r2, dates = get_macro_data()
    if r1 is None:
        return False
    # compute percentiles over the whole period
    pct1 = (r1.rank(pct=True).iloc[-1] * 100)
    pct2 = (r2.rank(pct=True).iloc[-1] * 100)
    # both must be below threshold
    if pct1 <= percentile_threshold and pct2 <= percentile_threshold:
        return True
    return False

def macro_status():
    """Return dict with current percentiles and boolean."""
    r1, r2, _ = get_macro_data()
    if r1 is None:
        return {"pass": False, "error": "insufficient data"}
    pct1 = r1.rank(pct=True).iloc[-1] * 100
    pct2 = r2.rank(pct=True).iloc[-1] * 100
    return {
        "pass": (pct1 <= 20 and pct2 <= 20),
        "bcom_sp_pct": float(pct1),
        "bcom_gold_pct": float(pct2)
    }
