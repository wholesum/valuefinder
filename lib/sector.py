"""
Sector screening: current price vs 5y/10y highs, or percentile-based.
"""
import pandas as pd
from . import data_fetcher

def sector_screen(etf_ticker, use_percentile=True, percentile_threshold=30,
                  pct_of_5y_high=0.70, pct_of_10y_high=0.80, debug=True):
    start_date = "2000-01-01"
    rows = data_fetcher.fetch_price_history(etf_ticker, start_date=start_date, force_refresh=True)

    if len(rows) < 252:
        if debug:
            print(f"  DEBUG: {etf_ticker} – insufficient data: {len(rows)} rows")
        return False, {}

    s = pd.Series([v for _, v in rows], index=pd.to_datetime([d for d, _ in rows]))
    current = s.iloc[-1]

    # 5y window
    cutoff_5y = s.index[-1] - pd.DateOffset(years=5)
    s_5y = s[s.index >= cutoff_5y]
    if len(s_5y) < 252:
        if debug:
            print(f"  DEBUG: {etf_ticker} – insufficient 5y data: {len(s_5y)} rows")
        return False, {}
    high_5y = s_5y.max()

    # 10y window
    cutoff_10y = s.index[-1] - pd.DateOffset(years=10)
    s_10y = s[s.index >= cutoff_10y]
    if len(s_10y) < 252:
        if debug:
            print(f"  DEBUG: {etf_ticker} – insufficient 10y data: {len(s_10y)} rows")
        high_10y = s_10y.max() if not s_10y.empty else None
    else:
        high_10y = s_10y.max()

    # Percentile method
    if use_percentile and len(s_5y) >= 252:
        pct_current = (s_5y < current).sum() / len(s_5y) * 100
        pass_pct = pct_current <= percentile_threshold
    else:
        pass_pct = False
        pct_current = None

    # High-based method (fallback)
    pass_5y = (current / high_5y) < pct_of_5y_high if not pd.isna(high_5y) else False
    pass_10y = (current / high_10y) < pct_of_10y_high if (high_10y is not None and not pd.isna(high_10y)) else False
    pass_high = pass_5y and pass_10y

    # Combined: pass if either percentile or high method passes (or both)
    final_pass = pass_pct or pass_high

    stats = {
        "current": current,
        "high_5y": high_5y,
        "high_10y": high_10y,
        "pct_of_5y_high": current/high_5y if not pd.isna(high_5y) else None,
        "pct_of_10y_high": current/high_10y if (high_10y is not None and not pd.isna(high_10y)) else None,
        "percentile_5y": pct_current,
        "pass_pct": pass_pct,
        "pass_5y": pass_5y,
        "pass_10y": pass_10y,
        "final_pass": final_pass
    }

    if debug:
        pct5 = stats['pct_of_5y_high'] * 100 if stats['pct_of_5y_high'] is not None else 'N/A'
        pct10 = stats['pct_of_10y_high'] * 100 if stats['pct_of_10y_high'] is not None else 'N/A'
        pctl = stats['percentile_5y'] if stats['percentile_5y'] is not None else 'N/A'
        print(f"  DEBUG: {etf_ticker} – Current: {current:.2f}, 5y high: {high_5y:.2f} ({pct5}%), 10y high: {high_10y if high_10y else 'N/A'} ({pct10}%), 5y percentile: {pctl}%, pass: {final_pass}")

    return final_pass, stats
