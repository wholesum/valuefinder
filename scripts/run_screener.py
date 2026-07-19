#!/usr/bin/env python
"""
Main screener script – enhanced with all new metrics.
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

    # Debug: print the top-level keys
    print("Config keys:", list(cfg.keys()))
    # Debug: print the raw sectors value
    print("Raw sectors value:", cfg.get("sectors"))

    # Macro params
    macro_cfg = cfg.get("macro", {})
    macro_lookback = macro_cfg.get("lookback_years", 25)
    macro_threshold = macro_cfg.get("cheap_percentile", 20)
    gold_sp_threshold = macro_cfg.get("gold_sp_percentile", 20)

    # 1. Macro check
    macro_status = macro.macro_status(lookback_years=macro_lookback,
                                      cheap_threshold=macro_threshold,
                                      gold_sp_threshold=gold_sp_threshold)
    if force_macro:
        macro_status["pass"] = True
        print("MACRO OVERRIDE: Forcing macro pass for testing.")
    elif not macro_status["pass"]:
        print("MACRO: Conditions not met. Holding cash.")
        print(f"BCOM/SP500 percentile: {macro_status['bcom_sp_pct']:.1f}%")
        print(f"BCOM/Gold percentile: {macro_status['bcom_gold_pct']:.1f}%")
        print(f"Gold/SP500 percentile: {macro_status['gold_sp_pct']:.1f}%")
        return

    print("MACRO PASS: Conditions met.")

    # 2. Sector screening
    sectors_cfg = cfg.get("sectors")
    if sectors_cfg is None:
        print("ERROR: 'sectors' key exists but value is None. Check your YAML formatting.")
        print("Make sure 'sectors:' is followed by a list of items, e.g.:")
        print("  sectors:")
        print("    - name: 'Oil & Gas'")
        print("      etf: 'XLE'")
        print("      ...")
        return

    # If sectors_cfg is a dict (old format), convert to list
    if isinstance(sectors_cfg, dict):
        print("Converting sectors from dict to list...")
        sectors_cfg = [{"name": k, **v} for k, v in sectors_cfg.items()]

    # Ensure we have a list
    if not isinstance(sectors_cfg, list):
        print(f"ERROR: 'sectors' should be a list. Got: {type(sectors_cfg)}")
        return

    if not sectors_cfg:
        print("WARNING: 'sectors' is an empty list. No sectors to scan.")
        return

    sector_params = cfg.get("screening", {}).get("sector", {})
    use_percentile = sector_params.get("use_percentile", True)
    percentile_threshold = sector_params.get("percentile_threshold", 30)
    pct_5y = sector_params.get("pct_of_5y_high", 0.70)
    pct_10y = sector_params.get("pct_of_10y_high", 0.80)

    qualifying_sectors = []
    for s in sectors_cfg:
        etf = s.get("etf")
        if not etf:
            print(f"WARNING: Sector entry missing 'etf': {s}")
            continue
        pass_sector, stats = sector.sector_screen(
            etf,
            use_percentile=use_percentile,
            percentile_threshold=percentile_threshold,
            pct_of_5y_high=pct_5y,
            pct_of_10y_high=pct_10y,
            debug=True
        )
        if pass_sector:
            print(f"SECTOR PASS: {s.get('name', etf)} ({etf})")
            qualifying_sectors.append(s)
        else:
            print(f"SECTOR FAIL: {s.get('name', etf)} ({etf})")

    if not qualifying_sectors:
        print("No qualifying sectors. Exiting.")
        return

    # 3. Stock screening
    screening_cfg = cfg.get("screening", {})
    results = []
    for sector_cfg in qualifying_sectors:
        sector_name = sector_cfg.get("name", sector_cfg.get("etf", "Unknown"))
        commodity_ticker = sector_cfg.get("commodity_ticker")
        if commodity_ticker:
            rows = data_fetcher.fetch_price_history(commodity_ticker)
            current_spot = rows[-1][1] if rows else 1.0
        else:
            current_spot = 1.0

        stocks = sector_cfg.get("stocks", [])
        if not stocks:
            print(f"WARNING: No stocks defined for sector {sector_name}")
            continue

        for ticker in stocks:
            # Fetch fundamentals (cached)
            fund = data_fetcher.fetch_fundamentals(ticker)
            if fund:
                db.upsert_fundamentals(ticker, fund)
            data_fetcher.fetch_shares_history(ticker)

            # Run stock filters
            stock_result = stock.screen_stock(ticker, sector_name, current_spot)
            if not stock_result["fundamental_pass"]:
                continue

            # Technical check
            tech_params = screening_cfg.get("technical", {})
            tech_pass, tech_stats = technical.technical_pass(
                ticker,
                short=tech_params.get("short_sma", 50),
                long=tech_params.get("long_sma", 200),
                volume_mult=tech_params.get("volume_multiplier", 1.5),
                rsi_oversold=tech_params.get("rsi_oversold", 30),
                rsi_overbought=tech_params.get("rsi_overbought", 70)
            )
            if not tech_pass:
                rsi_val = tech_stats.get('rsi')
                rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
                print(f"STOCK FAIL (technical): {ticker} ({sector_name}) – RSI: {rsi_str}, golden_cross: {tech_stats.get('golden_cross')}")
                continue

            print(f"STOCK BUY: {ticker} ({sector_name})")
            results.append({
                "ticker": ticker,
                "sector": sector_name,
                "macro_pass": True,
                "sector_pass": True,
                "cost_pass": stock_result["cost_pass"],
                "debt_pass": stock_result["debt_pass"],
                "dilution_pass": stock_result["dilution_pass"],
                "value_pass": stock_result["value_pass"],
                "technical_pass": True,
                "final_score": stock_result["value_score"] or 0,
                "recommendation": "BUY",
                "last_updated": datetime.now(timezone.utc).isoformat()
            })
            db.save_result(results[-1])

    print(f"Screener completed. {len(results)} stocks flagged as BUY.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-macro", action="store_true", help="Ignore macro condition for testing")
    args = parser.parse_args()
    run(force_macro=args.force_macro)
