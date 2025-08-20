import os
import sqlite3
import datetime as dt
from typing import Any, Dict, List, Optional


DB_PATH = os.getenv("EXPENSE_TRACKER_DB", os.path.join(os.getcwd(), "expense_tracker.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS group_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            payer_id INTEGER NOT NULL,
            category TEXT,
            date TEXT NOT NULL,
            description TEXT,
            is_settled INTEGER DEFAULT 0,           -- settlement tracking
            settled_at TEXT,                        -- settlement timestamp
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (payer_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS group_expense_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_expense_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            share_amount REAL NOT NULL,
            is_settled INTEGER DEFAULT 0,           -- share settlement status
            settled_at TEXT,                        -- share settlement timestamp
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (group_expense_id) REFERENCES group_expenses(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            category TEXT,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('Expense','Income')),
            payment_method TEXT,
            tags TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            year_month TEXT NOT NULL,               -- format YYYY-MM
            category TEXT,                          -- NULL means overall budget
            amount REAL NOT NULL,
            UNIQUE(user_id, year_month, category),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_txn_user_date ON transactions(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_txn_user_cat ON transactions(user_id, category);
        """
    )
    conn.commit()
    conn.close()


# ---------- User operations ---------- #
def create_user(name: str, email: str, password_hash: str) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(name, email, password_hash) VALUES(?,?,?)",
        (name, email.lower().strip(), password_hash),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return int(user_id)


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    return row


def update_user_password(user_id: int, new_hash: str) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()


# Transaction operations
def add_transaction(
    user_id: int,
    amount: float,
    description: Optional[str],
    category: Optional[str],
    date: dt.date,
    txn_type: str,
    payment_method: Optional[str],
    tags: Optional[str],
) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO transactions(user_id, amount, description, category, date, type, payment_method, tags)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            amount,
            (description or None),
            (category or None),
            date.isoformat(),
            txn_type,
            (payment_method or None),
            (tags or None),
        ),
    )
    conn.commit()
    txn_id = cur.lastrowid
    conn.close()
    return int(txn_id)


def update_transaction(
    txn_id: int,
    user_id: int,
    amount: float,
    description: Optional[str],
    category: Optional[str],
    date: dt.date,
    txn_type: str,
    payment_method: Optional[str],
    tags: Optional[str],
) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE transactions
           SET amount = ?, description = ?, category = ?, date = ?, type = ?, payment_method = ?, tags = ?
         WHERE id = ? AND user_id = ?
        """,
        (
            amount,
            (description or None),
            (category or None),
            date.isoformat(),
            txn_type,
            (payment_method or None),
            (tags or None),
            txn_id,
            user_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_transaction(txn_id: int, user_id: int) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (txn_id, user_id))
    conn.commit()
    conn.close()


def list_transactions(
    user_id: int,
    start_date: dt.date,
    end_date: dt.date,
    category: Optional[str] = None,
    txn_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    query = [
        "SELECT id, user_id, amount, description, category, date, type, payment_method, tags FROM transactions",
        "WHERE user_id = ? AND date BETWEEN ? AND ?",
    ]
    params: List[Any] = [user_id, start_date.isoformat(), end_date.isoformat()]
    if category:
        query.append("AND category = ?")
        params.append(category)
    if txn_type:
        query.append("AND type = ?")
        params.append(txn_type)
    query.append("ORDER BY date DESC, id DESC")
    cur.execute(" ".join(query), params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_distinct_categories(user_id: int) -> List[str]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT COALESCE(category,'Uncategorized') AS category FROM transactions WHERE user_id = ? ORDER BY 1",
        (user_id,),
    )
    rows = [r["category"] for r in cur.fetchall()]
    conn.close()
    return rows


# Group Expense operations 
def add_group_expense(
    title: str,
    amount: float,
    payer_id: int,
    category: str,
    date: dt.date,
    description: str,
    shares: List[Dict[str, Any]]
) -> int:
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO group_expenses(title, amount, payer_id, category, date, description)
            VALUES(?,?,?,?,?,?)
            """,
            (title, amount, payer_id, category, date.isoformat(), description)
        )
        expense_id = cur.lastrowid
        
        for share in shares:
            cur.execute(
                """
                INSERT INTO group_expense_shares(group_expense_id, user_id, share_amount)
                VALUES(?,?,?)
                """,
                (expense_id, share["user_id"], share["amount"])
            )
        
        conn.commit()
        return int(expense_id)
    finally:
        conn.close()


def get_group_expenses(user_id: int) -> List[Dict[str, Any]]:
    """Fetch all group expenses related to a user, including their share info."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            ge.id AS expense_id,
            ge.title,
            ge.amount,
            ge.category,
            ge.date,
            ge.description,
            ge.payer_id,
            ge.is_settled,         -- NEW
            ge.settled_at,         -- NEW
            u.name AS payer_name,
            ges.id AS share_id,
            ges.user_id,
            ges.share_amount,
            ges.is_settled AS share_settled,
            ges.settled_at AS share_settled_at
        FROM group_expenses ge
        JOIN users u ON ge.payer_id = u.id
        JOIN group_expense_shares ges ON ge.id = ges.group_expense_id
        WHERE ges.user_id = ? OR ge.payer_id = ?
        ORDER BY ge.date DESC, ge.id DESC
        """,
        (user_id, user_id)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def settle_expense_share(share_id: int, user_id: int) -> None:
    """Mark a specific user's share in a group expense as settled.
       If all shares are settled, also mark the whole expense as settled.
    """
    conn = _connect()
    cur = conn.cursor()

    # 1. Mark this share as settled
    cur.execute(
        """
        UPDATE group_expense_shares
        SET is_settled = 1, settled_at = datetime('now')
        WHERE id = ? AND user_id = ?
        """,
        (share_id, user_id)
    )

    # 2. Find the expense_id linked to this share
    cur.execute(
        "SELECT group_expense_id FROM group_expense_shares WHERE id = ?",
        (share_id,)
    )
    row = cur.fetchone()
    if row:
        group_expense_id = row[0]

        # 3. Check if all shares of this expense are settled
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM group_expense_shares
            WHERE group_expense_id = ? AND is_settled = 0
            """,
            (group_expense_id,)
        )
        pending_count = cur.fetchone()[0]

        if pending_count == 0:
            cur.execute(
                """
                UPDATE group_expenses
                SET is_settled = 1, settled_at = datetime('now')
                WHERE id = ?
                """,
                (group_expense_id,)
            )


    conn.commit()
    conn.close()


def get_all_users() -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email FROM users ORDER BY name")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# Budget operations
def set_budget(user_id: int, year_month: str, category: Optional[str], amount: float) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO budgets(user_id, year_month, category, amount)
        VALUES(?,?,?,?)
        ON CONFLICT(user_id, year_month, category)
        DO UPDATE SET amount=excluded.amount
        """,
        (user_id, year_month, category, amount),
    )
    conn.commit()
    conn.close()


def get_budget(user_id: int, year_month: str, category: Optional[str]) -> Optional[float]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT amount FROM budgets WHERE user_id = ? AND year_month = ? AND category IS ?",
        (user_id, year_month, category),
    )
    row = cur.fetchone()
    conn.close()
    return float(row["amount"]) if row else None
