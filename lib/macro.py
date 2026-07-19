def get_macro_data(commodity_ticker="GSG", stock_ticker="^GSPC", gold_ticker="GC=F", lookback_years=25):
    end = pd.Timestamp.today()
    start = end - pd.DateOffset(years=lookback_years)
    start_str = start.strftime("%Y-%m-%d")
    # fetch monthly data (resample)
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
    if len(common) < 60:
        return None, None, None
    bcom = bcom[common]
    spx = spx[common]
    gold = gold[common]
    ratio1 = bcom / spx
    ratio2 = bcom / gold
    return ratio1, ratio2, common
