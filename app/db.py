"""
Database access layer — deliberately uses raw sqlite3 + hand-written
SQL (no ORM) so joins, aggregates, and query design are explicit and
reviewable, per the "SQL & Database Concepts" requirement.
"""

import sqlite3
from contextlib import contextmanager
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    reorder_threshold INTEGER NOT NULL DEFAULT 5,
    unit_price REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    order_type TEXT NOT NULL CHECK (order_type IN ('sale', 'restock')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    priority INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in-progress', 'closed')),
    related_item_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (related_item_id) REFERENCES items(id)
);

CREATE INDEX IF NOT EXISTS idx_orders_item_id ON orders(item_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_items_sku ON items(sku);
"""


def get_db_path_default() -> str:
    return current_app.config["DATABASE"]


def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_conn(db_path: str | None = None) -> sqlite3.Connection:
    """Return a request-scoped connection (cached on flask.g)."""
    if "db_conn" not in g:
        path = db_path or get_db_path_default()
        g.db_conn = sqlite3.connect(path)
        g.db_conn.row_factory = sqlite3.Row
        g.db_conn.execute("PRAGMA foreign_keys = ON")
    return g.db_conn


def close_conn(e=None) -> None:
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Simple transaction context manager for multi-statement writes."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Reporting queries — raw SQL joins/aggregates, the parts an ORM usually hides
# ---------------------------------------------------------------------------

LOW_STOCK_QUERY = """
SELECT id, sku, name, category, quantity, reorder_threshold
FROM items
WHERE quantity <= reorder_threshold
ORDER BY (reorder_threshold - quantity) DESC;
"""

SALES_TREND_QUERY = """
SELECT
    i.category,
    strftime('%Y-%m-%d', o.created_at) AS order_date,
    SUM(o.quantity) AS units_sold,
    SUM(o.quantity * i.unit_price) AS revenue
FROM orders o
JOIN items i ON i.id = o.item_id
WHERE o.order_type = 'sale'
GROUP BY i.category, order_date
ORDER BY order_date DESC;
"""

ITEM_USAGE_HISTORY_QUERY = """
SELECT
    strftime('%Y-%m-%d', created_at) AS order_date,
    SUM(quantity) AS units
FROM orders
WHERE item_id = ? AND order_type = 'sale'
GROUP BY order_date
ORDER BY order_date ASC;
"""

TASK_LOAD_BY_STATUS_QUERY = """
SELECT status, COUNT(*) AS count
FROM tasks
GROUP BY status;
"""
