"""
Macro check: compare BCOM/SP500, BCOM/Gold, and Gold/SP500.
"""
import pandas as pd
from . import data_fetcher

def get_macro_data(commodity_ticker="^BCOM", stock_ticker="^GSPC", gold_ticker="GC=F", lookback_years=25):
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
        return None, None, None, None

    common = bcom.index.intersection(spx.index).intersection(gold.index)
    if len(common) < 60:
        return None, None, None, None

    bcom = bcom[common]
    spx = spx[common]
    gold = gold[common]

    ratio_bcom_sp = bcom / spx
    ratio_bcom_gold = bcom / gold
    ratio_gold_sp = gold / spx

    return ratio_bcom_sp, ratio_bcom_gold, ratio_gold_sp, common


def macro_status(lookback_years=25, cheap_threshold=25, gold_sp_threshold=20):
    r1, r2, r3, _ = get_macro_data(lookback_years=lookback_years)
    if r1 is None:
        return {"pass": False, "error": "Insufficient data"}

    pct_bcom_sp = r1.rank(pct=True).iloc[-1] * 100
    pct_bcom_gold = r2.rank(pct=True).iloc[-1] * 100
    pct_gold_sp = r3.rank(pct=True).iloc[-1] * 100

    # Conditions: commodities cheap vs stocks AND vs gold, AND gold not too expensive vs stocks
    macro_pass = (pct_bcom_sp <= cheap_threshold and
                  pct_bcom_gold <= cheap_threshold and
                  pct_gold_sp >= gold_sp_threshold)   # gold cheap vs stocks?

    return {
        "pass": macro_pass,
        "bcom_sp_pct": float(pct_bcom_sp),
        "bcom_gold_pct": float(pct_bcom_gold),
        "gold_sp_pct": float(pct_gold_sp)
    }
