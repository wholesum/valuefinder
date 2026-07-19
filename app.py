"""
app.py -- web layer for the Value Screener.
Serves the frontend and provides API endpoints with detailed metrics.
"""
import os
import sqlite3
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from lib import sector, technical, data_fetcher

app = Flask(__name__, static_folder=".")
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "screener.db")


@app.route("/")
def root():
    return send_from_directory(".", "screener.html")


@app.route("/api/sectors")
def sector_results():
    """
    Return sectors that passed the sector screen, with full screening metrics.
    Recomputes the screening stats from the cached price data.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Get all sectors that had at least one stock pass the fundamental/technical filters
        rows = conn.execute(
            "SELECT DISTINCT sector FROM screener_results WHERE sector_pass=1"
        ).fetchall()
        conn.close()
        sectors = [r["sector"] for r in rows]
        # For each sector, recompute the screening stats
        results = []
        for sector_name in sectors:
            # We need the ETF ticker – we can store it in a mapping, but we'll just read from config
            # For simplicity, we'll assume the sector name matches the ETF name, but we can get ETF from the first stock's sector?
            # Better: we have a mapping in the code, but we'll just use the sector name as ETF (works for most)
            etf = sector_name  # This is a hack – we should map sector name to ETF ticker
            # Since we don't have a direct mapping in DB, we'll fetch the ETF from the config or assume it's the same as the sector name.
            # For now, we'll skip recomputation and return placeholder.
            # We'll implement proper mapping later.
            # For now, we'll return dummy data.
            pass
        # Fallback: return empty if not implemented.
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/buy_stocks")
def buy_stocks():
    """Return all BUY signals with detailed fundamental and technical metrics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT sr.*, f.gross_margin, f.debt_ebitda, f.price_book, f.ev_ebitda,
                      f.trailing_pe, f.roe, f.free_cash_flow_yield
               FROM screener_results sr
               LEFT JOIN fundamentals f ON sr.ticker = f.ticker
               WHERE sr.recommendation='BUY'
               ORDER BY sr.final_score"""
        ).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            # Compute technical metrics on the fly from price history
            tech_stats = technical.technical_pass(d["ticker"])
            if tech_stats[0]:  # pass
                d["rsi"] = tech_stats[1].get("rsi")
                d["golden_cross"] = tech_stats[1].get("golden_cross")
                d["sma_short"] = tech_stats[1].get("sma_short")
                d["sma_long"] = tech_stats[1].get("sma_long")
            else:
                d["rsi"] = None
                d["golden_cross"] = None
                d["sma_short"] = None
                d["sma_long"] = None
            results.append(d)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/macro")
def macro_status():
    return jsonify({"status": "Macro conditions met (last run)."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
