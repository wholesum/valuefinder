def fetch_fundamentals(ticker):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            return None
        return {
            "shares": info.get("sharesOutstanding"),
            "debt_ebitda": info.get("debtToEquity"),
            "pb": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "gross_margin": info.get("grossMargins"),
            "trailing_pe": info.get("trailingPE"),
            "price_to_free_cash_flow": info.get("priceToFreeCashFlow"),
            "roe": info.get("returnOnEquity"),
            "free_cash_flow_yield": info.get("freeCashflowYield"),
            "current_ratio": info.get("currentRatio"),
            "interest_coverage": info.get("interestCoverage"),
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        # Silent fail for delisted/invalid tickers
        return None
