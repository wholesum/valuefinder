"""
Sector screening: compare current price to 5y and 10y highs, with detailed debug.
"""
import pandas as pd
from . import data_fetcher

def sector_screen(etf_ticker, min_years=3, verbose=True):
    """
    Return True if current price is below 70% of the 5-year high
    and below 80% of the 10-year high (i.e., "hated").
    If verbose, print detailed stats.
    """
    # fetch daily data as far back as possible
    rows = data_fetcher.fetch_price_history(etf_ticker)
    if len(rows) < 252 * 2:  # at least 2 years
        if verbose:
            print(f"    {etf_ticker}: insufficient data ({len(rows)} rows)")
        return False, {}

    s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
    current = s.iloc[-1]
    
    # 5y high
    cutoff_5y = s.index[-1] - pd.DateOffset(years=5)
    s_5y = s[s.index >= cutoff_5y]
    if len(s_5y) < 252:  # less than a year of data in the 5y window
        if verbose:
            print(f"    {etf_ticker}: not enough 5y data ({len(s_5y)} days)")
        high_5y = None
    else:
        high_5y = s_5y.max()
    
    # 10y high
    cutoff_10y = s.index[-1] - pd.DateOffset(years=10)
    s_10y = s[s.index >= cutoff_10y]
    if len(s_10y) < 252:
        if verbose:
            print(f"    {etf_ticker}: not enough 10y data ({len(s_10y)} days)")
        high_10y = None
    else:
        high_10y = s_10y.max()
    
    # thresholds
    pass_5y = False
    pass_10y = False
    
    if high_5y is not None and high_5y > 0:
        ratio_5y = current / high_5y
        pass_5y = ratio_5y < 0.70
    else:
        ratio_5y = None
    
    if high_10y is not None and high_10y > 0:
        ratio_10y = current / high_10y
        pass_10y = ratio_10y < 0.80
    else:
        ratio_10y = None
    
    overall = pass_5y and pass_10y
    
    if verbose:
        print(f"    {etf_ticker}: current=${current:.2f}, 5y high=${high_5y:.2f} ({ratio_5y*100:.1f}%) -> {'PASS' if pass_5y else 'FAIL'}, 10y high=${high_10y:.2f} ({ratio_10y*100:.1f}%) -> {'PASS' if pass_10y else 'FAIL'}, overall={'PASS' if overall else 'FAIL'}")
    
    stats = {
        "current": current,
        "high_5y": high_5y,
        "high_10y": high_10y,
        "pct_of_5y_high": ratio_5y,
        "pct_of_10y_high": ratio_10y,
        "pass_5y": pass_5y,
        "pass_10y": pass_10y,
        "overall": overall
    }
    return overall, stats
