"""
Sector screening: compare current price to 5y and 10y highs. Includes debug output.
"""
import pandas as pd
from . import data_fetcher

def sector_screen(etf_ticker, min_years=5, debug=True):
    """
    Return True if current price is below 70% of the 5-year high and below 80%
    of the 10-year high (i.e., "hated").
    """
    # Force a fresh fetch to avoid stale/empty cache
    rows = data_fetcher.fetch_price_history(etf_ticker, force_refresh=True)
    if len(rows) < 252:  # at least 1 year of daily data
        if debug:
            print(f"  DEBUG: {etf_ticker} – insufficient data: {len(rows)} rows")
        return False, {}

    s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
    current = s.iloc[-1]

    # 5y high
    cutoff_5y = s.index[-1] - pd.DateOffset(years=5)
    s_5y = s[s.index >= cutoff_5y]
    if len(s_5y) < 252:
        if debug:
            print(f"  DEBUG: {etf_ticker} – insufficient data in 5y window: {len(s_5y)} rows")
        return False, {}
    high_5y = s_5y.max()

    # 10y high
    cutoff_10y = s.index[-1] - pd.DateOffset(years=10)
    s_10y = s[s.index >= cutoff_10y]
    if len(s_10y) < 252:
        if debug:
            print(f"  DEBUG: {etf_ticker} – insufficient data in 10y window: {len(s_10y)} rows")
        # still try to use what we have
        high_10y = s_10y.max() if not s_10y.empty else None
    else:
        high_10y = s_10y.max()

    # thresholds: current < 70% of 5y high, and < 80% of 10y high
    pass_5y = (current / high_5y) < 0.70 if not pd.isna(high_5y) else False
    pass_10y = (current / high_10y) < 0.80 if (high_10y is not None and not pd.isna(high_10y)) else False

    stats = {
        "current": current,
        "high_5y": high_5y,
        "high_10y": high_10y,
        "pct_of_5y_high": current/high_5y if not pd.isna(high_5y) else None,
        "pct_of_10y_high": current/high_10y if (high_10y is not None and not pd.isna(high_10y)) else None,
        "pass_5y": pass_5y,
        "pass_10y": pass_10y
    }

    if debug:
        pct5 = stats['pct_of_5y_high'] * 100 if stats['pct_of_5y_high'] is not None else 'N/A'
        pct10 = stats['pct_of_10y_high'] * 100 if stats['pct_of_10y_high'] is not None else 'N/A'
        print(f"  DEBUG: {etf_ticker} – Current: {current:.2f}, 5y high: {high_5y:.2f} ({pct5}%), 10y high: {high_10y if high_10y else 'N/A'} ({pct10}%), pass_5y: {pass_5y}, pass_10y: {pass_10y}")

    return pass_5y and pass_10y, stats
