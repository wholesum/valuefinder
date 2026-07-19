"""
Sector screening: compare current price to 5y and 10y highs.
"""
import pandas as pd
from . import data_fetcher

def sector_screen(etf_ticker, min_years=5):
    """
    Return True if current price is below 70% of the 5-year high
    and below 80% of the 10-year high (i.e., "hated").
    """
    # fetch daily data as far back as possible
    rows = data_fetcher.fetch_price_history(etf_ticker)
    if len(rows) < 252 * 2:  # at least 2 years
        return False, {}
    s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
    current = s.iloc[-1]
    # 5y high
    cutoff_5y = s.index[-1] - pd.DateOffset(years=5)
    s_5y = s[s.index >= cutoff_5y]
    high_5y = s_5y.max()
    # 10y high
    cutoff_10y = s.index[-1] - pd.DateOffset(years=10)
    s_10y = s[s.index >= cutoff_10y]
    high_10y = s_10y.max()
    # thresholds: current < 70% of 5y high, and < 80% of 10y high
    pass_5y = (current / high_5y) < 0.70 if not pd.isna(high_5y) else False
    pass_10y = (current / high_10y) < 0.80 if not pd.isna(high_10y) else False
    return pass_5y and pass_10y, {
        "current": current,
        "high_5y": high_5y,
        "high_10y": high_10y,
        "pct_of_5y_high": current/high_5y,
        "pct_of_10y_high": current/high_10y
    }
