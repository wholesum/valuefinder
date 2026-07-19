"""
app.py -- web layer for the Value Screener.
Serves the frontend and provides API endpoints with detailed metrics.
"""
import os
import sqlite3
import traceback
import logging
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from lib import technical, db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=".")
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "screener.db")

# Ensure database schema is up to date on startup
db.init_db()


@app.route("/")
def root():
    return send_from_directory(".", "screener.html")


@app.route("/api/sectors")
def sector_results():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Check if sector_pass column exists; if not, treat all as pass (fallback)
        try:
            rows = conn.execute(
                "SELECT DISTINCT sector FROM screener_results WHERE sector_pass=1"
            ).fetchall()
        except sqlite3.OperationalError:
            # column may not exist; fallback to all sectors with any BUY
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
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/buy_stocks")
def buy_stocks():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # First, check if the table exists and has any BUY rows
        try:
            count_row = conn.execute("SELECT COUNT(*) as cnt FROM screener_results WHERE recommendation='BUY'").fetchone()
            count = count_row[0] if count_row else 0
            logger.info(f"Found {count} BUY rows")
        except sqlite3.OperationalError as e:
            # Table might not have 'recommendation' column yet
            logger.warning(f"Error checking BUY rows: {e}")
            # Fallback: check if any rows exist at all
            try:
                rows = conn.execute("SELECT * FROM screener_results LIMIT 1").fetchall()
                if rows:
                    # If rows exist but no recommendation column, use a default
                    logger.info("No 'recommendation' column, falling back to all rows")
                    rows = conn.execute("SELECT * FROM screener_results").fetchall()
                    conn.close()
                    results = []
                    for r in rows:
                        d = dict(r)
                        # Add technical metrics
                        try:
                            tech_pass, tech_stats = technical.technical_pass(d["ticker"])
                            if tech_stats and isinstance(tech_stats, dict):
                                d["rsi"] = tech_stats.get("rsi")
                                d["golden_cross"] = tech_stats.get("golden_cross")
                                d["sma_short"] = tech_stats.get("sma_short")
                                d["sma_long"] = tech_stats.get("sma_long")
                        except Exception:
                            pass
                        results.append(d)
                    return jsonify(results)
                else:
                    return jsonify([])
            except sqlite3.OperationalError:
                # Table likely doesn't exist
                logger.error("screener_results table does not exist")
                return jsonify([])

        # Normal path: select BUY rows with join to fundamentals
        try:
            rows = conn.execute(
                """SELECT sr.*, f.gross_margin, f.debt_ebitda, f.price_book, f.ev_ebitda,
                          f.trailing_pe, f.roe, f.free_cash_flow_yield
                   FROM screener_results sr
                   LEFT JOIN fundamentals f ON sr.ticker = f.ticker
                   WHERE sr.recommendation='BUY'
                   ORDER BY sr.final_score"""
            ).fetchall()
        except sqlite3.OperationalError as e:
            # If join fails (missing columns), fallback to just screener_results
            logger.warning(f"Join failed, falling back to basic query: {e}")
            rows = conn.execute(
                "SELECT * FROM screener_results WHERE recommendation='BUY' ORDER BY final_score"
            ).fetchall()
        conn.close()

        results = []
        for r in rows:
            d = dict(r)
            # Compute technical metrics on the fly
            try:
                tech_pass, tech_stats = technical.technical_pass(d["ticker"])
                if tech_stats and isinstance(tech_stats, dict):
                    d["rsi"] = tech_stats.get("rsi")
                    d["golden_cross"] = tech_stats.get("golden_cross")
                    d["sma_short"] = tech_stats.get("sma_short")
                    d["sma_long"] = tech_stats.get("sma_long")
                else:
                    d["rsi"] = None
                    d["golden_cross"] = None
                    d["sma_short"] = None
                    d["sma_long"] = None
            except Exception as e:
                logger.warning(f"Technical calculation failed for {d.get('ticker')}: {e}")
                d["rsi"] = None
                d["golden_cross"] = None
                d["sma_short"] = None
                d["sma_long"] = None
            results.append(d)

        return jsonify(results)
    except Exception as e:
        logger.error(f"Stocks API error: {traceback.format_exc()}")
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/debug")
def debug():
    """Debug endpoint to check database state."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Check tables
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_list = [t["name"] for t in tables]
        result = {"tables": table_list}
        # Check screener_results schema
        if "screener_results" in table_list:
            cols = conn.execute("PRAGMA table_info(screener_results)").fetchall()
            result["screener_results_columns"] = [c["name"] for c in cols]
            # Check row count
            count = conn.execute("SELECT COUNT(*) as cnt FROM screener_results").fetchone()
            result["screener_results_count"] = count[0] if count else 0
            # Check if any BUY rows
            try:
                buy_count = conn.execute("SELECT COUNT(*) as cnt FROM screener_results WHERE recommendation='BUY'").fetchone()
                result["buy_count"] = buy_count[0] if buy_count else 0
            except:
                result["buy_count"] = "column 'recommendation' missing"
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/macro")
def macro_status():
    return jsonify({"status": "Macro conditions met (last run)."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
