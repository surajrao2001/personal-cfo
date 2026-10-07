"""SQLite schema for the local ledger. Transactions are not deleted here."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    account TEXT NOT NULL,
    account_key TEXT NOT NULL,
    merchant TEXT,
    description TEXT,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('debit', 'credit', 'transfer')),
    category TEXT,
    subcategory TEXT,
    payment_method TEXT,
    reference_id TEXT,
    source TEXT NOT NULL CHECK (source IN ('gmail', 'bank_statement', 'manual', 'investment_api')),
    source_message_id TEXT,
    confidence_bps INTEGER NOT NULL CHECK (confidence_bps BETWEEN 0 AND 10000),
    category_uncertain INTEGER NOT NULL CHECK (category_uncertain IN (0, 1)),
    reviewed INTEGER NOT NULL CHECK (reviewed IN (0, 1)),
    reviewed_at TEXT,
    possible_duplicate_of TEXT,
    fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_account_key ON transactions(account_key);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_lookup
    ON transactions(date, amount_minor, account_key, currency);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_reference
    ON transactions(account_key, reference_id)
    WHERE reference_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS reconciliation_records (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source_label TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    matched_transaction_ids TEXT NOT NULL,
    discrepancies TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_created
    ON reconciliation_records(created_at);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
