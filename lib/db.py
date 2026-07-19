"""
SQLite persistence for the screener. Caches price data and fundamental metrics
to reduce disk I/O and API calls.
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "screener.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    close  REAL NOT NULL,
    source TEXT,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS fundamentals (
    ticker         TEXT PRIMARY KEY,
    shares_outstanding REAL,           -- most recent
    debt_ebitda    REAL,
    price_book     REAL,
    ev_ebitda      REAL,
    gross_margin   REAL,               -- proxy for production cost advantage
    last_updated   TEXT
);

CREATE TABLE IF NOT EXISTS shares_history (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    shares REAL NOT NULL,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS screener_results (
    ticker      TEXT PRIMARY KEY,
    sector      TEXT,
    macro_pass  INTEGER,
    sector_pass INTEGER,
    cost_pass   INTEGER,
    debt_pass   INTEGER,
    dilution_pass INTEGER,
    technical_pass INTEGER,
    final_score REAL,
    recommendation TEXT,
    last_updated TEXT
);
"""

@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)

def upsert_prices(ticker, rows, source):
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO prices (ticker, date, close, source) VALUES (?,?,?,?)",
            [(ticker, d, float(c), source) for d, c in rows]
        )

def get_prices(ticker, start_date=None, end_date=None):
    with get_conn() as conn:
        q = "SELECT date, close FROM prices WHERE ticker = ?"
        params = [ticker]
        if start_date:
            q += " AND date >= ?"
            params.append(start_date)
        if end_date:
            q += " AND date <= ?"
            params.append(end_date)
        q += " ORDER BY date"
        rows = conn.execute(q, params).fetchall()
    return [(r["date"], r["close"]) for r in rows]

def upsert_fundamentals(ticker, data):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO fundamentals
               (ticker, shares_outstanding, debt_ebitda, price_book, ev_ebitda, gross_margin, last_updated)
               VALUES (?,?,?,?,?,?,?)""",
            (ticker, data.get("shares"), data.get("debt_ebitda"), data.get("pb"),
             data.get("ev_ebitda"), data.get("gross_margin"), data.get("last_updated"))
        )

def get_fundamentals(ticker):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fundamentals WHERE ticker = ?", (ticker,)).fetchone()
    return dict(row) if row else None

def upsert_shares_history(ticker, rows):
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO shares_history (ticker, date, shares) VALUES (?,?,?)",
            [(ticker, d, float(s)) for d, s in rows]
        )

def get_shares_history(ticker, years=5):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, shares FROM shares_history WHERE ticker = ? ORDER BY date DESC LIMIT ?",
            (ticker, 252*years)
        ).fetchall()
    return [(r["date"], r["shares"]) for r in rows]

def save_result(result):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO screener_results
               (ticker, sector, macro_pass, sector_pass, cost_pass, debt_pass, dilution_pass,
                technical_pass, final_score, recommendation, last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (result["ticker"], result["sector"], int(result["macro_pass"]),
             int(result["sector_pass"]), int(result["cost_pass"]), int(result["debt_pass"]),
             int(result["dilution_pass"]), int(result["technical_pass"]),
             result["final_score"], result["recommendation"], result["last_updated"])
        )
