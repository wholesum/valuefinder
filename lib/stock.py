"""
Stock-level filters: cost, debt, dilution, value.
Now more lenient with missing data.
"""
from . import data_fetcher, db

def get_fund(ticker):
    return db.get_fundamentals(ticker)

def cost_filter(ticker, commodity_spot_price, margin_threshold=0.0):
    """
    Accept if gross margin > threshold (default 0).
    Missing data -> pass (True)
    """
    fund = get_fund(ticker)
    if fund is None:
        return True, None
    gm = fund.get("gross_margin")
    if gm is None:
        return True, None
    return gm > margin_threshold, gm

def debt_filter(ticker, max_debt_equity=3.0):
    """
    Accept if debt-to-equity <= max_debt_equity.
    Missing data -> pass (True)
    """
    fund = get_fund(ticker)
    if fund is None:
        return True, None
    debt_eq = fund.get("debt_ebitda")   # actually debt-to-equity
    if debt_eq is None:
        return True, None
    # Also handle extreme values (negative debt means negative equity, treat as fail)
    if debt_eq < 0:
        return False, debt_eq
    return debt_eq <= max_debt_equity, debt_eq

def dilution_filter(ticker, max_yoy=0.05):
    """
    Accept if share growth <= max_yoy.
    Insufficient data -> pass (True)
    """
    shares_hist = db.get_shares_history(ticker, years=3)
    if len(shares_hist) < 2:
        return True, None
    oldest = shares_hist[-1][1]
    newest = shares_hist[0][1]
    if oldest <= 0 or newest <= 0:
        return True, None
    annual_growth = (newest / oldest) ** (1 / (len(shares_hist)/252)) - 1
    # If growth is extremely negative (massive buybacks) it's fine
    return annual_growth <= max_yoy, annual_growth

def value_filter(ticker, pb_max=3.0, ev_ebitda_max=15.0, pe_max=25.0, pfcf_max=30.0,
                 roe_min=0.10, fcf_yield_min=0.04):
    """
    Accept if metrics are within thresholds, missing -> pass.
    Only fail if we have a clear violation.
    """
    fund = get_fund(ticker)
    if not fund:
        return True, {}
    
    pb = fund.get("price_book")
    ev = fund.get("ev_ebitda")
    pe = fund.get("trailing_pe")
    pfcf = fund.get("price_to_free_cash_flow")
    roe = fund.get("roe")
    fcf_yield = fund.get("free_cash_flow_yield")

    # Check each metric if present; missing -> pass
    pass_pb = pb is None or pb <= pb_max
    pass_ev = ev is None or ev <= ev_ebitda_max
    pass_pe = pe is None or pe <= pe_max
    pass_pfcf = pfcf is None or pfcf <= pfcf_max
    pass_roe = roe is None or roe >= roe_min
    pass_fcf_yield = fcf_yield is None or fcf_yield >= fcf_yield_min

    overall = pass_pb and pass_ev and pass_pe and pass_pfcf and pass_roe and pass_fcf_yield
    
    return overall, {
        "pb": pb,
        "ev": ev,
        "pe": pe,
        "pfcf": pfcf,
        "roe": roe,
        "fcf_yield": fcf_yield
    }

def screen_stock(ticker, sector, commodity_spot_price):
    cost_pass, cost_val = cost_filter(ticker, commodity_spot_price)
    debt_pass, debt_val = debt_filter(ticker)
    dil_pass, dil_val = dilution_filter(ticker)
    value_pass, value_metrics = value_filter(ticker)

    # Composite value score (only if we have both pb and ev)
    score = None
    pb = value_metrics.get("pb")
    ev = value_metrics.get("ev")
    if pb is not None and ev is not None:
        # Normalise: pb/3.0 + ev/15.0, average
        score = (pb/3.0 + ev/15.0) / 2

    fundamental_pass = cost_pass and debt_pass and dil_pass and value_pass

    # Debug: print reasons for failure
    if not fundamental_pass:
        reasons = []
        if not cost_pass:
            reasons.append(f"cost (gm={cost_val:.2f})" if cost_val is not None else "cost (gm missing)")
        if not debt_pass:
            reasons.append(f"debt (de={debt_val:.2f})" if debt_val is not None else "debt (missing)")
        if not dil_pass:
            reasons.append(f"dilution (growth={dil_val:.2%})" if dil_val is not None else "dilution (missing)")
        if not value_pass:
            reasons.append("value")
        print(f"  STOCK FAIL (fundamental): {ticker} – {', '.join(reasons)}")

    return {
        "ticker": ticker,
        "sector": sector,
        "cost_pass": cost_pass,
        "debt_pass": debt_pass,
        "dilution_pass": dil_pass,
        "value_pass": value_pass,
        "cost_value": cost_val,
        "debt_value": debt_val,
        "dilution_value": dil_val,
        "value_metrics": value_metrics,
        "value_score": score,
        "fundamental_pass": fundamental_pass
    }
