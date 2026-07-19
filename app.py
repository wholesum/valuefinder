"""
app.py -- the web layer for the Value Screener.
Serves the frontend and provides API endpoints for sector and stock results.
"""
import os
import sqlite3
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "screener.db")


@app.route("/")
def root():
    return send_from_directory(".", "screener.html")


@app.route("/api/sectors")
def sector_results():
    """Return sectors that passed the sector screen with stock count."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT sector, COUNT(*) as stock_count FROM screener_results WHERE sector_pass=1 GROUP BY sector ORDER BY sector"
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/buy_stocks")
def buy_stocks():
    """Return all BUY signals."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM screener_results WHERE recommendation='BUY' ORDER BY final_score"
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/macro")
def macro_status():
    """Return the latest macro status (from the database or a separate table)."""
    # You can store macro results in a separate table or just return a placeholder.
    # For now, we'll return a static message since macro is run offline.
    return jsonify({"status": "Macro conditions met (last run)."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
