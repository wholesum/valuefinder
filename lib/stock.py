"""
Stock-level filters with safe conversion for extreme values.
"""
from . import db

def get_fund(ticker):
    return db.get_fundamentals(ticker)

def safe_float(v):
    """
    Convert to float, return None if not possible or inf/nan.
    This prevents crashes from extreme or invalid data.
    """
    if v is None:
        return None
    try:
        f = float(v)
        # Check for infinity or NaN
        if not (f == float('inf') or f == float('-inf') or f != f):  # f != f is NaN check
            return f
        return None
    except (TypeError, ValueError):
        return None

def cost_filter(ticker, commodity_spot_price, margin_threshold=0.0):
    """
    Accept if gross margin > threshold (default 0, i.e., any positive margin).
    Returns (pass, value).
    """
    fund = get_fund(ticker)
    if fund is None:
        return True, None   # missing data -> pass
    gm = safe_float(fund.get("gross_margin"))
    if gm is None:
        return True, None
    return gm > margin_threshold, gm

def debt_filter(ticker, max_debt_equity=3.0):
    """
    Accept if debt-to-equity <= max_debt_equity.
    Missing data -> pass.
    """
    fund = get_fund(ticker)
    if fund is None:
        return True, None
    debt_eq = safe_float(fund.get("debt_ebitda"))  # this is actually debt-to-equity
    if debt_eq is None:
        return True, None
    return debt_eq <= max_debt_equity, debt_eq

def dilution_filter(ticker, max_yoy=0.05):
    """
    Accept if YoY share growth <= max_yoy (5% default).
    Missing data -> pass.
    """
    shares_hist = db.get_shares_history(ticker, years=3)
    if len(shares_hist) < 2:
        return True, None
    oldest = shares_hist[-1][1]  # oldest is last because order is DESC
    newest = shares_hist[0][1]
    if oldest <= 0:
        return True, None
    annual_growth = (newest / oldest) ** (1 / (len(shares_hist)/252)) - 1
    return annual_growth <= max_yoy, annual_growth

def value_filter(ticker, pb_max=3.0, ev_ebitda_max=15.0, pe_max=25.0,
                 pfcf_max=30.0, roe_min=0.10, fcf_yield_min=0.04):
    """
    Apply multiple valuation metrics.
    Missing data -> pass (we don't have enough info to reject).
    Returns (overall_pass, metrics_dict).
    """
    fund = get_fund(ticker)
    if not fund:
        return True, {}

    pb = safe_float(fund.get("price_book"))
    ev = safe_float(fund.get("ev_ebitda"))
    pe = safe_float(fund.get("trailing_pe"))
    pfcf = safe_float(fund.get("price_to_free_cash_flow"))
    roe = safe_float(fund.get("roe"))
    fcf_yield = safe_float(fund.get("free_cash_flow_yield"))

    # If any metric is None, we skip that check (treat as pass)
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
    """
    Run all filters on a single stock.
    Returns a dict with pass/fail and diagnostic info.
    """
    cost_pass, cost_val = cost_filter(ticker, commodity_spot_price)
    debt_pass, debt_val = debt_filter(ticker)
    dil_pass, dil_val = dilution_filter(ticker)
    value_pass, value_metrics = value_filter(ticker)

    # Composite value score (lower = cheaper)
    score = 0
    count = 0
    if value_metrics.get("pb") is not None:
        score += value_metrics["pb"] / 3.0
        count += 1
    if value_metrics.get("ev") is not None:
        score += value_metrics["ev"] / 15.0
        count += 1
    value_score = score / count if count > 0 else None

    fundamental_pass = cost_pass and debt_pass and dil_pass and value_pass

    # Debug output only if it fails
    if not fundamental_pass:
        reasons = []
        if not cost_pass:
            reasons.append(f"cost (gm={cost_val})")
        if not debt_pass:
            reasons.append(f"debt (de={debt_val})")
        if not dil_pass:
            reasons.append(f"dilution (growth={dil_val})")
        if not value_pass:
            reasons.append(f"value (pb={value_metrics.get('pb')}, ev={value_metrics.get('ev')}, pe={value_metrics.get('pe')})")
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
        "value_score": value_score,
        "fundamental_pass": fundamental_pass
    }
