#!/usr/bin/env python
"""
Main screener script. Runs macro, sector, and stock screens, then saves results.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
import argparse
from datetime import datetime, timezone
from lib import db, macro, sector, stock, technical, data_fetcher

def load_config(path="config/screener.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)

def run(force_macro=False):
    db.init_db()
    cfg = load_config()
    macro_lookback = cfg["macro"].get("lookback_years", 25)
    macro_threshold = cfg["macro"].get("cheap_percentile", 20)

    # 1. Macro check
    macro_status = macro.macro_status(lookback_years=macro_lookback, cheap_threshold=macro_threshold)
    if force_macro:
        macro_status["pass"] = True
        print("MACRO OVERRIDE: Forcing macro pass for testing.")
    elif not macro_status["pass"]:
        print("MACRO: Commodities are not historically cheap. Holding cash.")
        print(f"BCOM/SP500 percentile: {macro_status['bcom_sp_pct']:.1f}%")
        print(f"BCOM/Gold percentile: {macro_status['bcom_gold_pct']:.1f}%")
        return

    print("MACRO PASS: Commodities are cheap relative to stocks and gold.")

    # 2. Sector scan
    sectors_cfg = cfg["sectors"]
    qualifying_sectors = []
    for s in sectors_cfg:
        etf = s["etf"]
        pass_sector, stats = sector.sector_screen(etf, debug=True)
        if pass_sector:
            print(f"SECTOR PASS: {s['name']} ({etf}) – trading below 70% of 5y high and 80% of 10y high.")
            qualifying_sectors.append(s)
        else:
            print(f"SECTOR FAIL: {s['name']} ({etf}) – not 'hated' enough.")

    if not qualifying_sectors:
        print("No qualifying sectors. Exiting.")
        return

    # 3. Stock-level screening
    results = []
    for sector_cfg in qualifying_sectors:
        sector_name = sector_cfg["name"]
        # get commodity spot price if available
        commodity_ticker = sector_cfg.get("commodity_ticker")
        if commodity_ticker:
            rows = data_fetcher.fetch_price_history(commodity_ticker)
            if rows:
                current_spot = rows[-1][1]
            else:
                current_spot = 1.0
        else:
            current_spot = 1.0

        for ticker in sector_cfg["stocks"]:
            # fetch fundamentals (will cache)
            fund = data_fetcher.fetch_fundamentals(ticker)
            if fund:
                db.upsert_fundamentals(ticker, fund)
            # fetch shares history
            shares = data_fetcher.fetch_shares_history(ticker)

            # screen stock
            stock_result = stock.screen_stock(ticker, sector_name, current_spot)
            if not stock_result["fundamental_pass"]:
                print(f"STOCK FAIL (fundamental): {ticker} ({sector_name})")
                continue

            # technical check
            tech_pass, tech_stats = technical.technical_pass(ticker)
            if not tech_pass:
                print(f"STOCK FAIL (technical): {ticker} ({sector_name})")
                continue

            # If both fundamental and technical pass, it's a buy signal
            print(f"STOCK BUY: {ticker} ({sector_name}) – all screens passed.")
            results.append({
                "ticker": ticker,
                "sector": sector_name,
                "macro_pass": True,
                "sector_pass": True,
                "cost_pass": stock_result["cost_pass"],
                "debt_pass": stock_result["debt_pass"],
                "dilution_pass": stock_result["dilution_pass"],
                "technical_pass": True,
                "final_score": stock_result["value_score"] or 0,
                "recommendation": "BUY",
                "last_updated": datetime.now(timezone.utc).isoformat()
            })
            # Save to DB
            db.save_result(results[-1])

    print(f"Screener completed. {len(results)} stocks flagged as BUY.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-macro", action="store_true", help="Ignore macro condition for testing")
    args = parser.parse_args()
    run(force_macro=args.force_macro)
