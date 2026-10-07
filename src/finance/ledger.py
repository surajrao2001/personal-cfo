"""Read and write normalized transactions. There is no delete operation."""

import sqlite3
import uuid
from datetime import datetime, timezone

from finance.constants import CATEGORIES
from finance.errors import FinanceError
from finance.masking import mask_identifier
from finance.money import format_amount, format_confidence, parse_confidence
from finance.normalize import NormalizedTransaction, clean_text

_CATEGORY_UNCERTAIN_BELOW = 6000


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def present(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "date": row["date"],
        "account": row["account"],
        "merchant": row["merchant"],
        "description": row["description"],
        "amount": format_amount(row["amount_minor"]),
        "currency": row["currency"],
        "type": row["entry_type"],
        "category": row["category"],
        "subcategory": row["subcategory"],
        "payment_method": row["payment_method"],
        "reference_id": mask_identifier(row["reference_id"]),
        "source": row["source"],
        "source_message_id": row["source_message_id"],
        "confidence": format_confidence(row["confidence_bps"]),
        "category_uncertain": bool(row["category_uncertain"]),
        "reviewed": bool(row["reviewed"]),
        "possible_duplicate_of": row["possible_duplicate_of"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_row(connection: sqlite3.Connection, transaction_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM transactions WHERE id = ?",
        (transaction_id,),
    ).fetchone()


def require_row(connection: sqlite3.Connection, transaction_id: str) -> sqlite3.Row:
    row = get_row(connection, transaction_id)
    if row is None:
        raise FinanceError("not_found", "No transaction exists with that id")
    return row


def insert_transaction(
    connection: sqlite3.Connection,
    txn: NormalizedTransaction,
    possible_duplicate_of: str | None = None,
) -> dict[str, object]:
    timestamp = utc_now()
    transaction_id = new_id("txn")
    connection.execute(
        """
        INSERT INTO transactions (
            id, date, account, account_key, merchant, description, amount_minor,
            currency, entry_type, category, subcategory, payment_method, reference_id,
            source, source_message_id, confidence_bps, category_uncertain, reviewed,
            reviewed_at, possible_duplicate_of, fingerprint, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, 0,
            NULL, ?, ?, ?, ?
        )
        """,
        (
            transaction_id,
            txn.date,
            txn.account,
            txn.account_key,
            txn.merchant,
            txn.description,
            txn.amount_minor,
            txn.currency,
            txn.entry_type,
            txn.category,
            txn.subcategory,
            txn.payment_method,
            txn.reference_id,
            txn.source,
            txn.source_message_id,
            txn.confidence_bps,
            int(txn.category_uncertain),
            possible_duplicate_of,
            txn.fingerprint,
            timestamp,
            timestamp,
        ),
    )
    row = require_row(connection, transaction_id)
    return present(row)


def rows_between(connection: sqlite3.Connection, start: str, end: str) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT * FROM transactions
            WHERE date >= ? AND date <= ?
            ORDER BY date, id
            """,
            (start, end),
        ).fetchall()
    )


def date_bounds(connection: sqlite3.Connection) -> tuple[str, str] | None:
    row = connection.execute("SELECT MIN(date), MAX(date) FROM transactions").fetchone()
    if row is None or row[0] is None:
        return None
    return str(row[0]), str(row[1])


def search_transactions(connection: sqlite3.Connection, query: str) -> list[dict[str, object]]:
    text = query.strip()
    if not text:
        raise FinanceError("invalid_query", "query is required")
    if len(text) > 200:
        raise FinanceError("invalid_query", "query is too long")
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like = f"%{escaped}%"
    rows = connection.execute(
        """
        SELECT * FROM transactions
        WHERE merchant LIKE ? ESCAPE '\\'
           OR description LIKE ? ESCAPE '\\'
           OR category LIKE ? ESCAPE '\\'
           OR IFNULL(reference_id, '') LIKE ? ESCAPE '\\'
           OR account LIKE ? ESCAPE '\\'
        ORDER BY date DESC, id ASC
        LIMIT 100
        """,
        (like, like, like, like, like),
    ).fetchall()
    return [present(row) for row in rows]


def update_category(
    connection: sqlite3.Connection,
    transaction_id: str,
    category: str,
    subcategory: str | None,
    confidence: object,
) -> dict[str, object]:
    row = require_row(connection, transaction_id)
    allowed = {name.casefold(): name for name in CATEGORIES}
    if not isinstance(category, str) or category.strip().casefold() not in allowed:
        raise FinanceError("invalid_category", "category must be one of the supported categories")
    canonical = allowed[category.strip().casefold()]
    next_subcategory = row["subcategory"] if subcategory is None else clean_text(subcategory, "subcategory")
    confidence_bps = parse_confidence(confidence, int(row["confidence_bps"]))
    uncertain = confidence_bps < _CATEGORY_UNCERTAIN_BELOW
    connection.execute(
        """
        UPDATE transactions
        SET category = ?, subcategory = ?, confidence_bps = ?, category_uncertain = ?, updated_at = ?
        WHERE id = ?
        """,
        (canonical, next_subcategory, confidence_bps, int(uncertain), utc_now(), transaction_id),
    )
    return present(require_row(connection, transaction_id))


def mark_reviewed(connection: sqlite3.Connection, transaction_id: str) -> dict[str, object]:
    row = require_row(connection, transaction_id)
    if not row["reviewed"]:
        timestamp = utc_now()
        connection.execute(
            """
            UPDATE transactions
            SET reviewed = 1, reviewed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (timestamp, timestamp, transaction_id),
        )
    return present(require_row(connection, transaction_id))


def count_transactions(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) FROM transactions").fetchone()
    return int(row[0])
