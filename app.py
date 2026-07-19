"""
Simple web UI for the screener. Reads results from screener.db.
"""
import sqlite3
from flask import Flask, jsonify, send_from_directory
import os

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "screener.db")

def get_results():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM screener_results ORDER BY final_score"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except:
        return []

@app.route('/')
def index():
    # Simple HTML table
    results = get_results()
    if not results:
        return "<h1>No BUY signals currently.</h1><p>Run scripts/run_screener.py to refresh.</p>"
    html = "<h1>Value Screener – BUY Signals</h1><table border='1'><tr><th>Ticker</th><th>Sector</th><th>Final Score</th><th>Recommendation</th></tr>"
    for r in results:
        html += f"<tr><td>{r['ticker']}</td><td>{r['sector']}</td><td>{r['final_score']:.2f}</td><td>{r['recommendation']}</td></tr>"
    html += "</table>"
    return html

@app.route('/api/results')
def api_results():
    return jsonify(get_results())

if __name__ == '__main__':
    app.run(debug=True)
