"""
SQLite persistence layer.
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
        # Add any missing columns to fundamentals (in case they were added later)
        for col in ['trailing_pe', 'price_to_free_cash_flow', 'roe', 'free_cash_flow_yield',
                    'current_ratio', 'interest_coverage']:
            _add_column_if_not_exists(conn, "fundamentals", col, "REAL")

# ---------------------------------------------------------------- prices ---
# ... (all other functions from the original db.py, but keep them unchanged)

# We'll keep all existing functions: delete_prices_before, last_price_date, upsert_prices, get_price_series, etc.
# And also upsert_fundamentals, get_fundamentals, upsert_shares_history, get_shares_history, save_result, get_results, etc.
