"""
SQLite persistence layer with column migration support.
"""
import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "screener.db")

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
    shares_outstanding REAL,
    debt_ebitda    REAL,
    price_book     REAL,
    ev_ebitda      REAL,
    gross_margin   REAL,
    trailing_pe    REAL,
    price_to_free_cash_flow REAL,
    roe            REAL,
    free_cash_flow_yield REAL,
    current_ratio  REAL,
    interest_coverage REAL,
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
    dilution_value REAL,           -- store the actual dilution %
    value_pass  INTEGER,
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

def _add_column_if_not_exists(conn, table, column, coltype):
    """Add a column to a table if it doesn't already exist."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Ensure all expected columns exist (migration for existing DB)
        # For screener_results
        for col in ['sector_pass', 'value_pass', 'cost_pass', 'debt_pass', 'dilution_pass', 'technical_pass', 'recommendation']:
            _add_column_if_not_exists(conn, "screener_results", col, "INTEGER" if col != 'recommendation' else "TEXT")
        # Add dilution_value column if missing
        _add_column_if_not_exists(conn, "screener_results", "dilution_value", "REAL")

# ---------------------------------------------------------------- prices ---
def delete_prices_before(cutoff_date: str):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM prices WHERE date < ?", (cutoff_date,))
        return cur.rowcount

def last_price_date(ticker: str):
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(date) AS d FROM prices WHERE ticker = ?", (ticker,)).fetchone()
    return row["d"] if row and row["d"] else None

def upsert_prices(ticker: str, rows, source: str):
    if not rows:
        return 0
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO prices (ticker, date, close, source) VALUES (?,?,?,?)",
            [(ticker, d, float(c), source) for d, c in rows],
        )
    return len(rows)

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

# ------------------------------------------------------------ fundamentals ---
def upsert_fundamentals(ticker: str, data):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO fundamentals
               (ticker, shares_outstanding, debt_ebitda, price_book, ev_ebitda,
                gross_margin, trailing_pe, price_to_free_cash_flow, roe,
                free_cash_flow_yield, current_ratio, interest_coverage, last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ticker,
             data.get("shares"),
             data.get("debt_ebitda"),
             data.get("pb"),
             data.get("ev_ebitda"),
             data.get("gross_margin"),
             data.get("trailing_pe"),
             data.get("price_to_free_cash_flow"),
             data.get("roe"),
             data.get("free_cash_flow_yield"),
             data.get("current_ratio"),
             data.get("interest_coverage"),
             data.get("last_updated"))
        )

def get_fundamentals(ticker: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fundamentals WHERE ticker = ?", (ticker,)).fetchone()
    return dict(row) if row else None

# ------------------------------------------------------------ shares history ---
def upsert_shares_history(ticker, rows):
    if not rows:
        return 0
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO shares_history (ticker, date, shares) VALUES (?,?,?)",
            [(ticker, d, float(s)) for d, s in rows]
        )
    return len(rows)

def get_shares_history(ticker, years=5):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, shares FROM shares_history WHERE ticker = ? ORDER BY date DESC LIMIT ?",
            (ticker, 252*years)
        ).fetchall()
    return [(r["date"], r["shares"]) for r in rows]

# ------------------------------------------------------------ screener results ---
def save_result(result):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO screener_results
               (ticker, sector, macro_pass, sector_pass, cost_pass, debt_pass,
                dilution_pass, dilution_value, value_pass, technical_pass, final_score,
                recommendation, last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (result["ticker"], result["sector"],
             int(result["macro_pass"]), int(result["sector_pass"]),
             int(result["cost_pass"]), int(result["debt_pass"]),
             int(result["dilution_pass"]), result.get("dilution_value"),
             int(result["value_pass"]), int(result["technical_pass"]),
             result["final_score"], result["recommendation"],
             result["last_updated"])
        )

def get_results():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM screener_results ORDER BY final_score").fetchall()
    return [dict(r) for r in rows]
