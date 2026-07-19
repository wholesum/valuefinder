"""
Stock-level filters: cost, debt, dilution, value.
Added debug output to show why each stock fails.
"""
import pandas as pd
from . import data_fetcher, db

def get_aisc_proxy(ticker):
    """AISC not directly available; use gross margin as a proxy."""
    fund = db.get_fundamentals(ticker)
    if fund and fund.get("gross_margin") is not None:
        return fund["gross_margin"]
    return None

def cost_filter(ticker, commodity_spot_price, margin_threshold=0.0):
    """
    Accept if gross margin > threshold (default 0, i.e., any positive margin).
    """
    gm = get_aisc_proxy(ticker)
    if gm is None:
        return False, None
    return gm > margin_threshold, gm

def debt_filter(ticker, max_debt_equity=3.0):
    """
    Accept if debt-to-equity <= max_debt_equity.
    If data missing, treat as pass (None means pass).
    """
    fund = db.get_fundamentals(ticker)
    if fund is None:
        return True, None
    debt_eq = fund.get("debt_ebitda")  # actually debtToEquity
    if debt_eq is None:
        return True, None
    return debt_eq <= max_debt_equity, debt_eq

def dilution_filter(ticker, max_yoy=0.05, years=3):
    """Accept if share growth <= max_yoy; if no data, pass."""
    shares_hist = db.get_shares_history(ticker, years)
    if len(shares_hist) < 2:
        return True, None  # not enough data, skip check
    oldest = shares_hist[-1][1]
    newest = shares_hist[0][1]
    if oldest <= 0:
        return True, None
    annual_growth = (newest / oldest) ** (1 / (len(shares_hist)/252)) - 1
    return annual_growth <= max_yoy, annual_growth

def value_ranking(ticker):
    """Return a composite value score (lower is cheaper)."""
    fund = db.get_fundamentals(ticker)
    if not fund:
        return None
    pb = fund.get("price_book")
    ev = fund.get("ev_ebitda")
    if pb is None or ev is None:
        return None
    return pb * 0.5 + ev * 0.5

def screen_stock(ticker, sector, commodity_spot_price):
    """
    Run all filters on a single stock. Returns a dict with pass/fail and scores.
    """
    cost_pass, cost_val = cost_filter(ticker, commodity_spot_price)
    debt_pass, debt_val = debt_filter(ticker)
    dil_pass, dil_val = dilution_filter(ticker)
    value_score = value_ranking(ticker)
    
    fundamental_pass = cost_pass and debt_pass and dil_pass
    
    # Debug: print why it failed
    if not fundamental_pass:
        reasons = []
        if not cost_pass:
            reasons.append(f"cost (gm={cost_val})")
        if not debt_pass:
            reasons.append(f"debt (de={debt_val})")
        if not dil_pass:
            reasons.append(f"dilution (growth={dil_val})")
        print(f"  STOCK FAIL (fundamental): {ticker} – {', '.join(reasons)}")
    
    return {
        "ticker": ticker,
        "sector": sector,
        "cost_pass": cost_pass,
        "debt_pass": debt_pass,
        "dilution_pass": dil_pass,
        "cost_value": cost_val,
        "debt_value": debt_val,
        "dilution_value": dil_val,
        "value_score": value_score,
        "fundamental_pass": fundamental_pass
    }
