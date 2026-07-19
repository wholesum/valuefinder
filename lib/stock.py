"""
Stock-level filters: cost, debt, dilution, value.
"""
import pandas as pd
from . import data_fetcher, db

def get_aisc_proxy(ticker):
    """AISC not directly available; use gross margin as a proxy (higher = better cost control)."""
    fund = db.get_fundamentals(ticker)
    if fund and fund.get("gross_margin") is not None:
        return fund["gross_margin"]
    return None

def cost_filter(ticker, commodity_spot_price, margin_threshold=0.2):
    """
    Accept if gross margin > threshold (i.e., company can produce profitably).
    """
    gm = get_aisc_proxy(ticker)
    if gm is None:
        return False, None
    # assume cost = price * (1 - margin); require margin > 20% (adjust)
    return gm > margin_threshold, gm

def debt_filter(ticker, max_debt_ebitda=2.5):
    fund = db.get_fundamentals(ticker)
    if fund is None or fund.get("debt_ebitda") is None:
        return False, None
    return fund["debt_ebitda"] <= max_debt_ebitda, fund["debt_ebitda"]

def dilution_filter(ticker, max_yoy=0.05, years=3):
    """Compute YoY share growth; reject if > max_yoy."""
    shares_hist = db.get_shares_history(ticker, years)
    if len(shares_hist) < 2:
        return False, None
    # use latest vs oldest to compute annualised growth
    oldest = shares_hist[-1][1]  # last entry is oldest because order is DESC
    newest = shares_hist[0][1]
    if oldest <= 0:
        return False, None
    annual_growth = (newest / oldest) ** (1 / (len(shares_hist)/252)) - 1  # rough
    return annual_growth <= max_yoy, annual_growth

def value_ranking(ticker):
    """Return a composite value score (lower is cheaper)."""
    fund = db.get_fundamentals(ticker)
    if not fund:
        return None
    pb = fund.get("price_book")
    ev = fund.get("ev_ebitda")
    # combine into a z-score; use default if missing
    if pb is None or ev is None:
        return None
    return pb * 0.5 + ev * 0.5   # simple average; can be improved

def screen_stock(ticker, sector, commodity_spot_price):
    """
    Run all filters on a single stock. Returns a dict with pass/fail and scores.
    """
    # cost filter (using gross margin)
    cost_pass, cost_val = cost_filter(ticker, commodity_spot_price)
    # debt
    debt_pass, debt_val = debt_filter(ticker)
    # dilution
    dil_pass, dil_val = dilution_filter(ticker)
    # value score
    value_score = value_ranking(ticker)
    # overall fundamental pass
    fundamental_pass = cost_pass and debt_pass and dil_pass
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
