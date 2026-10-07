"""Facade used by the Finance MCP. Money movement is intentionally absent."""

import os
import sqlite3
from pathlib import Path
from collections.abc import Callable

from finance.balances import account_balances, net_worth
from finance.db import connect, init_db
from finance.dedup import check_duplicate
from finance.errors import FinanceError
from finance.json_store import read_object
from finance.ledger import (
    count_transactions,
    date_bounds,
    insert_transaction,
    mark_reviewed,
    present,
    require_row,
    rows_between,
    search_transactions,
    update_category,
)
from finance.normalize import normalize_transaction, parse_month, require_range
from investments.portfolio import load_portfolio, load_sips
from reconciliation.records import create_reconciliation_record
from reports.metrics import cashflow_report, category_report, investment_report, monthly_report, savings_report

SAVINGS_NOTE = (
    "Savings rate is (income - consumption expenses) / income. "
    "Transfers and investment transactions are excluded from consumption. "
    "A credit in an expense category reduces that expense."
)
INVESTMENT_NOTE = (
    "Investment rate is (investment purchases - investment redemptions) / income. "
    "This does not place trades or change SIPs."
)


def resolve_data_dir() -> Path:
    override = os.environ.get("PERSONAL_CFO_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "data"


class FinanceService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.db_path = data_dir / "transactions.db"

    def _run(self, operation: Callable[[sqlite3.Connection], dict[str, object]]) -> dict[str, object]:
        connection = connect(self.db_path)
        try:
            init_db(connection)
            result = operation(connection)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_profile(self) -> dict[str, object]:
        return {"ok": True, "profile": read_object(self.data_dir / "profile.json")}

    def get_transactions(self, start_date: str, end_date: str) -> dict[str, object]:
        start, end = require_range(start_date, end_date)

        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            rows = rows_between(connection, start, end)
            return {"ok": True, "transactions": [present(row) for row in rows]}

        return self._run(operation)

    def search_transactions(self, query: str) -> dict[str, object]:
        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            return {"ok": True, "transactions": search_transactions(connection, query)}

        return self._run(operation)

    def get_transaction(self, transaction_id: str) -> dict[str, object]:
        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            return {"ok": True, "transaction": present(require_row(connection, transaction_id))}

        return self._run(operation)

    def get_monthly_spending(self, month: str) -> dict[str, object]:
        start, end = parse_month(month)

        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            report = monthly_report(rows_between(connection, start, end), month.strip(), start, end)
            report["ok"] = True
            return report

        return self._run(operation)

    def get_cashflow(self, start_date: str, end_date: str) -> dict[str, object]:
        start, end = require_range(start_date, end_date)

        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            report = cashflow_report(rows_between(connection, start, end), start, end)
            report["ok"] = True
            return report

        return self._run(operation)

    def get_category_spending(self, start_date: str, end_date: str) -> dict[str, object]:
        start, end = require_range(start_date, end_date)

        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            report = category_report(rows_between(connection, start, end), start, end)
            report["ok"] = True
            return report

        return self._run(operation)

    def get_account_balances(self) -> dict[str, object]:
        payload = account_balances(self.data_dir)
        payload["ok"] = True
        return payload

    def get_net_worth(self) -> dict[str, object]:
        payload = net_worth(self.data_dir)
        payload["ok"] = True
        return payload

    def get_portfolio(self) -> dict[str, object]:
        payload = load_portfolio(self.data_dir)
        payload["ok"] = True
        return payload

    def get_sips(self) -> dict[str, object]:
        return {"ok": True, "sips": load_sips(self.data_dir)}

    def get_goals(self) -> dict[str, object]:
        raw = read_object(self.data_dir / "goals.json")
        goals = raw.get("goals", [])
        if goals is None:
            goals = []
        if not isinstance(goals, list):
            raise FinanceError("invalid_config", "goals.json goals must be a list")
        return {"ok": True, "goals": goals}

    def calculate_savings_rate(self, start_date: str | None = None, end_date: str | None = None) -> dict[str, object]:
        return self._rate(savings_report, SAVINGS_NOTE, start_date, end_date)

    def calculate_investment_rate(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, object]:
        return self._rate(investment_report, INVESTMENT_NOTE, start_date, end_date)

    def _rate(
        self,
        builder: Callable[[list[sqlite3.Row], str | None, str | None], dict[str, object]],
        note: str,
        start_date: str | None,
        end_date: str | None,
    ) -> dict[str, object]:
        if (start_date is None) ^ (end_date is None):
            raise FinanceError("invalid_date", "Provide both start_date and end_date, or neither")
        chosen = require_range(start_date, end_date) if start_date is not None and end_date is not None else None

        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            bounds = chosen or date_bounds(connection)
            if bounds is None:
                report = builder([], None, None)
            else:
                report = builder(rows_between(connection, bounds[0], bounds[1]), bounds[0], bounds[1])
            report["ok"] = True
            report["note"] = note
            return report

        return self._run(operation)

    def add_transaction(
        self,
        *,
        date: str,
        account: str,
        amount: object,
        entry_type: str,
        currency: str = "INR",
        merchant: str | None = None,
        description: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        payment_method: str | None = None,
        reference_id: str | None = None,
        source: str = "manual",
        source_message_id: str | None = None,
        confidence: object = None,
        accept_uncertain_duplicate: bool = False,
    ) -> dict[str, object]:
        txn = normalize_transaction(
            date=date,
            account=account,
            amount=amount,
            entry_type=entry_type,
            currency=currency,
            merchant=merchant,
            description=description,
            category=category,
            subcategory=subcategory,
            payment_method=payment_method,
            reference_id=reference_id,
            source=source,
            source_message_id=source_message_id,
            confidence=confidence,
        )

        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            duplicate = check_duplicate(connection, txn)
            if duplicate.kind == "exact":
                return {
                    "ok": True,
                    "status": "duplicate",
                    "inserted": False,
                    "transaction": present(duplicate.rows[0]),
                }
            if duplicate.kind == "conflict":
                raise FinanceError(
                    "reference_conflict",
                    "A transaction with this reference already exists with a different amount or date. "
                    "The ledger was not changed.",
                )
            possible_duplicate_of = None
            if duplicate.kind == "uncertain":
                if not accept_uncertain_duplicate:
                    return {
                        "ok": True,
                        "status": "uncertain_duplicate",
                        "inserted": False,
                        "candidates": [present(row) for row in duplicate.rows],
                    }
                possible_duplicate_of = str(duplicate.rows[0]["id"])
            try:
                transaction = insert_transaction(connection, txn, possible_duplicate_of)
            except sqlite3.IntegrityError as exc:
                existing = connection.execute(
                    "SELECT * FROM transactions WHERE fingerprint = ?",
                    (txn.fingerprint,),
                ).fetchone()
                if existing is None:
                    raise FinanceError(
                        "conflict",
                        "The transaction conflicts with an existing ledger row and was not saved.",
                    ) from exc
                return {
                    "ok": True,
                    "status": "duplicate",
                    "inserted": False,
                    "transaction": present(existing),
                }
            return {"ok": True, "status": "created", "inserted": True, "transaction": transaction}

        return self._run(operation)

    def update_transaction_category(
        self,
        transaction_id: str,
        category: str,
        subcategory: str | None = None,
        confidence: object = None,
    ) -> dict[str, object]:
        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            before = require_row(connection, transaction_id)
            updated = update_category(connection, transaction_id, category, subcategory, confidence)
            after = require_row(connection, transaction_id)
            if before["amount_minor"] != after["amount_minor"] or before["date"] != after["date"]:
                raise FinanceError("internal_error", "Category update attempted to change the financial amount")
            return {"ok": True, "transaction": updated}

        return self._run(operation)

    def mark_transaction_reviewed(self, transaction_id: str) -> dict[str, object]:
        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            return {"ok": True, "transaction": mark_reviewed(connection, transaction_id)}

        return self._run(operation)

    def create_reconciliation_record(
        self,
        source_label: str,
        period_start: str | None = None,
        period_end: str | None = None,
        matched_transaction_ids: list[str] | None = None,
        discrepancies_json: str | None = None,
        notes: str | None = None,
    ) -> dict[str, object]:
        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            before = count_transactions(connection)
            record = create_reconciliation_record(
                connection,
                source_label=source_label,
                period_start=period_start,
                period_end=period_end,
                matched_transaction_ids=matched_transaction_ids,
                discrepancies_json=discrepancies_json,
                notes=notes,
            )
            if count_transactions(connection) != before:
                raise FinanceError("internal_error", "Reconciliation changed the transaction count")
            return {"ok": True, "record": record}

        return self._run(operation)

    def transaction_count(self) -> int:
        def operation(connection: sqlite3.Connection) -> dict[str, object]:
            return {"count": count_transactions(connection)}

        return int(self._run(operation)["count"])
