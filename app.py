"""
app.py -- web layer for the Value Screener.
Serves the frontend and provides API endpoints with detailed metrics.
"""
import os
import sqlite3
import traceback
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from lib import technical, data_fetcher

app = Flask(__name__, static_folder=".")
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "screener.db")


@app.route("/")
def root():
    return send_from_directory(".", "screener.html")


@app.route("/api/sectors")
def sector_results():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT DISTINCT sector FROM screener_results WHERE sector_pass=1"
        ).fetchall()
        conn.close()
        # For now, return sectors with count of stocks passing
        sectors = []
        for r in rows:
            sector = r["sector"]
            conn = sqlite3.connect(DB_PATH)
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM screener_results WHERE sector=? AND recommendation='BUY'",
                (sector,)
            ).fetchone()[0]
            conn.close()
            sectors.append({"sector": sector, "stock_count": count})
        return jsonify(sectors)
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/buy_stocks")
def buy_stocks():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Select from screener_results and join with fundamentals
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
            # Compute technical metrics
            try:
                tech_pass, tech_stats = technical.technical_pass(d["ticker"])
                d["rsi"] = tech_stats.get("rsi") if tech_stats else None
                d["golden_cross"] = tech_stats.get("golden_cross") if tech_stats else None
                d["sma_short"] = tech_stats.get("sma_short") if tech_stats else None
                d["sma_long"] = tech_stats.get("sma_long") if tech_stats else None
            except Exception as e:
                # Fallback if technical calculation fails
                d["rsi"] = None
                d["golden_cross"] = None
                d["sma_short"] = None
                d["sma_long"] = None
            results.append(d)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/macro")
def macro_status():
    return jsonify({"status": "Macro conditions met (last run)."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
