#!/usr/bin/env python
"""
Diagnostic script to test yfinance on PythonAnywhere.
"""
import yfinance as yf
import sys

def test_ticker(ticker):
    print(f"Testing {ticker}...")
    try:
        data = yf.download(ticker, period="1d", progress=False, auto_adjust=True)
        if data.empty:
            print(f"  ERROR: No data for {ticker}")
        else:
            print(f"  SUCCESS: {data['Close'].iloc[-1]}")
    except Exception as e:
        print(f"  EXCEPTION: {e}")

if __name__ == "__main__":
    tickers = ["XLE", "XOP", "OIH", "SPY", "AAPL"]
    for t in tickers:
        test_ticker(t)
