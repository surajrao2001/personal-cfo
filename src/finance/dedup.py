"""Duplicate checks. Exact matches are not inserted. Uncertain matches are flagged."""

import sqlite3
from dataclasses import dataclass

from finance.normalize import NormalizedTransaction


@dataclass(frozen=True)
class DuplicateCheck:
    kind: str
    rows: list[sqlite3.Row]


def check_duplicate(connection: sqlite3.Connection, txn: NormalizedTransaction) -> DuplicateCheck:
    if txn.reference_id:
        existing = connection.execute(
            """
            SELECT * FROM transactions
            WHERE account_key = ? AND reference_id = ?
            """,
            (txn.account_key, txn.reference_id),
        ).fetchone()
        if existing is not None:
            same_value = (
                existing["amount_minor"] == txn.amount_minor and existing["date"] == txn.date
            )
            return DuplicateCheck("exact" if same_value else "conflict", [existing])

    existing = connection.execute(
        "SELECT * FROM transactions WHERE fingerprint = ?",
        (txn.fingerprint,),
    ).fetchone()
    if existing is not None:
        return DuplicateCheck("exact", [existing])

    candidates = connection.execute(
        """
        SELECT * FROM transactions
        WHERE date = ? AND amount_minor = ? AND account_key = ? AND currency = ?
        ORDER BY created_at, id
        """,
        (txn.date, txn.amount_minor, txn.account_key, txn.currency),
    ).fetchall()
    if candidates:
        return DuplicateCheck("uncertain", list(candidates))
    return DuplicateCheck("none", [])
