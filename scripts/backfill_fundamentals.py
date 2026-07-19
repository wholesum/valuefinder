#!/usr/bin/env python
"""
Backfill fundamentals for all BUY stocks.
Run this once after run_screener.py to fetch missing data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from lib import data_fetcher, db

def backfill():
    db.init_db()
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT ticker FROM screener_results WHERE recommendation='BUY'").fetchall()
    conn.close()
    if not rows:
        print("No BUY stocks found.")
        return
    tickers = [r["ticker"] for r in rows]
    print(f"Backfilling fundamentals for {len(tickers)} tickers...")
    for ticker in tickers:
        print(f"Fetching {ticker}...")
        fund = data_fetcher.fetch_fundamentals(ticker)
        if fund:
            db.upsert_fundamentals(ticker, fund)
            print(f"  -> saved")
        else:
            print(f"  -> no data")

if __name__ == "__main__":
    backfill()
