"""Store reconciliation metadata. Recording a result does not change transactions."""

import json
import sqlite3

from finance.errors import FinanceError
from finance.ledger import new_id, require_row, utc_now
from finance.normalize import parse_date

_MAX_NOTES = 2000
_MAX_DISCREPANCIES = 20000


def create_reconciliation_record(
    connection: sqlite3.Connection,
    *,
    source_label: str,
    period_start: str | None,
    period_end: str | None,
    matched_transaction_ids: list[str] | None,
    discrepancies_json: str | None,
    notes: str | None,
) -> dict[str, object]:
    label = " ".join(source_label.split())
    if not label:
        raise FinanceError("invalid_field", "source_label is required")
    if len(label) > 200:
        raise FinanceError("invalid_field", "source_label is too long")

    start = parse_date(period_start) if period_start else None
    end = parse_date(period_end) if period_end else None
    if start and end and start > end:
        raise FinanceError("invalid_date", "period_start must be on or before period_end")

    ids = matched_transaction_ids or []
    if not isinstance(ids, list) or not all(isinstance(item, str) and item.strip() for item in ids):
        raise FinanceError("invalid_field", "matched_transaction_ids must be a list of transaction ids")
    for transaction_id in ids:
        require_row(connection, transaction_id)

    if discrepancies_json in (None, ""):
        discrepancies: object = []
    else:
        if len(discrepancies_json) > _MAX_DISCREPANCIES:
            raise FinanceError("invalid_field", "discrepancies_json is too long")
        try:
            discrepancies = json.loads(discrepancies_json)
        except json.JSONDecodeError as exc:
            raise FinanceError("invalid_field", "discrepancies_json must be a JSON array") from exc
        if not isinstance(discrepancies, list):
            raise FinanceError("invalid_field", "discrepancies_json must be a JSON array")

    if notes is not None:
        notes = " ".join(notes.split())
        if len(notes) > _MAX_NOTES:
            raise FinanceError("invalid_field", "notes are too long")
        if notes == "":
            notes = None

    record_id = new_id("rec")
    created_at = utc_now()
    connection.execute(
        """
        INSERT INTO reconciliation_records (
            id, created_at, source_label, period_start, period_end,
            matched_transaction_ids, discrepancies, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            created_at,
            label,
            start,
            end,
            json.dumps(ids),
            json.dumps(discrepancies),
            notes,
        ),
    )
    return {
        "id": record_id,
        "created_at": created_at,
        "source_label": label,
        "period_start": start,
        "period_end": end,
        "matched_transaction_ids": ids,
        "discrepancies": discrepancies,
        "notes": notes,
    }
