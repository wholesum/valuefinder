"""
app.py -- web layer for the Value Screener.
Serves the frontend and provides API endpoints with detailed metrics.
"""
import os
import sqlite3
import traceback
import logging
import json
import numpy as np
import pandas as pd
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=".")
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "screener.db")


# Custom JSON encoder to handle numpy/pandas types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return str(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Series):
            return obj.tolist()
        if obj is None:
            return None
        return super().default(obj)


# Set custom encoder on the app
app.json_encoder = CustomJSONEncoder


@app.route("/")
def root():
    return send_from_directory(".", "screener.html")


@app.route("/api/sectors")
def sector_results():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Get distinct sectors with BUY stocks
        rows = conn.execute(
            "SELECT DISTINCT sector FROM screener_results WHERE recommendation='BUY'"
        ).fetchall()
        conn.close()
        sectors = []
        for r in rows:
            sector = r["sector"]
            conn2 = sqlite3.connect(DB_PATH)
            count = conn2.execute(
                "SELECT COUNT(*) as cnt FROM screener_results WHERE sector=? AND recommendation='BUY'",
                (sector,)
            ).fetchone()[0]
            conn2.close()
            sectors.append({"sector": sector, "stock_count": count})
        return jsonify(sectors)
    except Exception as e:
        logger.error(f"Sectors API error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/buy_stocks")
def buy_stocks():
    """
    Return all BUY signals with basic info (no joins, no technical to avoid errors).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM screener_results WHERE recommendation='BUY' ORDER BY final_score"
        ).fetchall()
        conn.close()
        results = [dict(r) for r in rows]
        return jsonify(results)
    except Exception as e:
        logger.error(f"Stocks API error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/buy_stocks_detailed")
def buy_stocks_detailed():
    """
    Return BUY signals with fundamentals and technicals (with safe fallbacks).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM screener_results WHERE recommendation='BUY' ORDER BY final_score"
        ).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            # Try to get fundamentals
            try:
                conn2 = sqlite3.connect(DB_PATH)
                fund = conn2.execute(
                    "SELECT gross_margin, debt_ebitda, price_book, ev_ebitda, "
                    "trailing_pe, roe, free_cash_flow_yield "
                    "FROM fundamentals WHERE ticker=?", (d["ticker"],)
                ).fetchone()
                conn2.close()
                if fund:
                    d["gross_margin"] = fund[0]
                    d["debt_ebitda"] = fund[1]
                    d["price_book"] = fund[2]
                    d["ev_ebitda"] = fund[3]
                    d["trailing_pe"] = fund[4]
                    d["roe"] = fund[5]
                    d["free_cash_flow_yield"] = fund[6]
            except Exception as e:
                logger.warning(f"Fundamentals fetch failed for {d['ticker']}: {e}")
            
            # Try technical
            try:
                from lib import technical
                tech_pass, tech_stats = technical.technical_pass(d["ticker"])
                # Convert tech_stats to native Python types
                if tech_stats:
                    d["rsi"] = float(tech_stats.get("rsi")) if tech_stats.get("rsi") is not None else None
                    d["golden_cross"] = bool(tech_stats.get("golden_cross")) if tech_stats.get("golden_cross") is not None else None
                    d["sma_short"] = float(tech_stats.get("sma_short")) if tech_stats.get("sma_short") is not None else None
                    d["sma_long"] = float(tech_stats.get("sma_long")) if tech_stats.get("sma_long") is not None else None
                else:
                    d["rsi"] = None
                    d["golden_cross"] = None
                    d["sma_short"] = None
                    d["sma_long"] = None
            except Exception as e:
                logger.warning(f"Technical failed for {d['ticker']}: {e}")
                d["rsi"] = None
                d["golden_cross"] = None
                d["sma_short"] = None
                d["sma_long"] = None
            
            # Ensure all values are JSON-serializable (convert numpy/pandas types)
            for key, value in list(d.items()):
                if isinstance(value, (np.integer, np.int64, np.int32)):
                    d[key] = int(value)
                elif isinstance(value, (np.floating, np.float64, np.float32)):
                    d[key] = float(value)
                elif isinstance(value, (np.bool_, bool)):
                    d[key] = bool(value)
                elif isinstance(value, (pd.Timestamp, np.datetime64)):
                    d[key] = str(value)
                elif isinstance(value, np.ndarray):
                    d[key] = value.tolist()
                elif isinstance(value, pd.Series):
                    d[key] = value.tolist()
                elif isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                    d[key] = None
            
            results.append(d)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Detailed stocks API error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/debug")
def debug():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_list = [t["name"] for t in tables]
        result = {"tables": table_list}
        if "screener_results" in table_list:
            cols = conn.execute("PRAGMA table_info(screener_results)").fetchall()
            result["screener_results_columns"] = [c["name"] for c in cols]
            count = conn.execute("SELECT COUNT(*) as cnt FROM screener_results").fetchone()
            result["screener_results_count"] = count[0] if count else 0
            buy_count = conn.execute("SELECT COUNT(*) as cnt FROM screener_results WHERE recommendation='BUY'").fetchone()
            result["buy_count"] = buy_count[0] if buy_count else 0
            # Sample row
            sample = conn.execute("SELECT * FROM screener_results LIMIT 1").fetchone()
            if sample:
                result["sample_row"] = dict(sample)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/macro")
def macro_status():
    return jsonify({"status": "Macro conditions met (last run)."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
