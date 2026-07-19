"""
Macro check: compare BCOM/SP500 and BCOM/Gold percentiles.
"""
import pandas as pd
import numpy as np
from . import data_fetcher, db

def get_macro_data(commodity_ticker="GSG", stock_ticker="^GSPC", gold_ticker="GC=F", lookback_years=25):
    """
    Fetch monthly data for the three series and compute the two ratios.
    Returns (ratio1 Series, ratio2 Series, common_dates Index) or (None, None, None).
    """
    end = pd.Timestamp.today()
    start = end - pd.DateOffset(years=lookback_years)
    start_str = start.strftime("%Y-%m-%d")

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

    common = bcom.index.intersection(spx.index).intersection(gold.index)
    if len(common) < 60:  # at least 5 years of monthly data
        return None, None, None

    bcom = bcom[common]
    spx = spx[common]
    gold = gold[common]
    ratio1 = bcom / spx
    ratio2 = bcom / gold
    return ratio1, ratio2, common


def macro_status(lookback_years=25):
    """
    Evaluate the macro condition.
    Returns a dict with 'pass' (bool), 'bcom_sp_pct' (float),
    'bcom_gold_pct' (float), and optionally 'error'.
    """
    r1, r2, _ = get_macro_data(lookback_years=lookback_years)
    if r1 is None:
        return {"pass": False, "error": "Insufficient data for macro analysis"}
    # Compute current percentile (lower is cheaper)
    pct1 = r1.rank(pct=True).iloc[-1] * 100
    pct2 = r2.rank(pct=True).iloc[-1] * 100
    # Both must be below the cheap_percentile threshold (default 20)
    cheap_threshold = 25
    return {
        "pass": (pct1 <= cheap_threshold and pct2 <= cheap_threshold),
        "bcom_sp_pct": float(pct1),
        "bcom_gold_pct": float(pct2)
    }
