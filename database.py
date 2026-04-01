"""
database.py — SQLite database layer for the Instagram Account Marketplace Bot.
Tables: users · admins · accounts · orders
"""

import sqlite3
from datetime import datetime
from config import DB_PATH


# ─── Connection helper ───────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─── Schema initialisation ───────────────────────────────────────────────────

def init_db() -> None:
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT    DEFAULT '',
            added_at   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT    DEFAULT '',
            first_name TEXT    DEFAULT '',
            joined_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            creation_year  INTEGER NOT NULL,
            followers      INTEGER NOT NULL,
            following      INTEGER NOT NULL,
            posts          INTEGER NOT NULL,
            account_type   TEXT    NOT NULL CHECK(account_type IN ('Private','Public')),
            price          REAL    NOT NULL,
            is_sold        INTEGER NOT NULL DEFAULT 0,
            added_at       TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            username    TEXT    DEFAULT '',
            account_id  INTEGER NOT NULL,
            placed_at   TEXT    NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        );
    """)

    conn.commit()
    conn.close()


# ─── Admin helpers ───────────────────────────────────────────────────────────

def add_admin(user_id: int, username: str = "") -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO admins (user_id, username, added_at) VALUES (?,?,?)",
        (user_id, username, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def remove_admin(user_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def is_admin(user_id: int) -> bool:
    from config import SUPER_ADMIN_ID
    if user_id == SUPER_ADMIN_ID:
        return True
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row is not None


def get_all_admin_ids() -> list[int]:
    from config import SUPER_ADMIN_ID
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM admins").fetchall()
    conn.close()
    ids = [r["user_id"] for r in rows]
    if SUPER_ADMIN_ID and SUPER_ADMIN_ID not in ids:
        ids.append(SUPER_ADMIN_ID)
    return ids


# ─── User helpers ────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str, first_name: str) -> bool:
    """Returns True if the user is new (first time seeing them)."""
    conn = get_conn()
    existing = conn.execute(
        "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, joined_at) VALUES (?,?,?,?)",
            (user_id, username, first_name, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def get_all_user_ids() -> list[int]:
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


# ─── Account helpers ─────────────────────────────────────────────────────────

def add_account(creation_year: int, followers: int, following: int,
                posts: int, account_type: str, price: float) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO accounts
           (creation_year, followers, following, posts, account_type, price, added_at)
           VALUES (?,?,?,?,?,?,?)""",
        (creation_year, followers, following, posts, account_type, price,
         datetime.utcnow().isoformat())
    )
    conn.commit()
    acc_id = cur.lastrowid
    conn.close()
    return acc_id


def get_available_years() -> list[int]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT creation_year FROM accounts WHERE is_sold=0 ORDER BY creation_year DESC"
    ).fetchall()
    conn.close()
    return [r["creation_year"] for r in rows]


def get_accounts_by_year(year: int, page: int = 0,
                         per_page: int = 5) -> list[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM accounts WHERE creation_year=? AND is_sold=0 LIMIT ? OFFSET ?",
        (year, per_page, page * per_page)
    ).fetchall()
    conn.close()
    return rows


def count_accounts_by_year(year: int) -> int:
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM accounts WHERE creation_year=? AND is_sold=0", (year,)
    ).fetchone()[0]
    conn.close()
    return n


def get_account_by_id(account_id: int) -> sqlite3.Row | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    conn.close()
    return row


def mark_account_sold(account_id: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE accounts SET is_sold=1 WHERE id=?", (account_id,))
    conn.commit()
    conn.close()


def delete_account(account_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()
    conn.close()


# ─── Order helpers ───────────────────────────────────────────────────────────

def place_order(user_id: int, username: str, account_id: int) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO orders (user_id, username, account_id, placed_at) VALUES (?,?,?,?)",
        (user_id, username, account_id, datetime.utcnow().isoformat())
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    return order_id


def get_user_orders(user_id: int) -> list[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.id, o.placed_at,
                  a.creation_year, a.followers, a.following,
                  a.posts, a.account_type, a.price
           FROM orders o
           JOIN accounts a ON o.account_id = a.id
           WHERE o.user_id = ?
           ORDER BY o.placed_at DESC""",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


# ─── Stats ───────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = get_conn()
    c = conn.cursor()
    stats = {
        "total_users":    c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "available_accs": c.execute("SELECT COUNT(*) FROM accounts WHERE is_sold=0").fetchone()[0],
        "sold_accs":      c.execute("SELECT COUNT(*) FROM accounts WHERE is_sold=1").fetchone()[0],
        "total_orders":   c.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "total_admins":   c.execute("SELECT COUNT(*) FROM admins").fetchone()[0],
        "total_revenue":  c.execute(
            "SELECT COALESCE(SUM(a.price),0) FROM orders o JOIN accounts a ON o.account_id=a.id"
        ).fetchone()[0],
    }
    conn.close()
    return stats
