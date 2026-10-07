"""Turn caller input into one canonical transaction shape."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from finance.constants import (
    CATEGORIES,
    DEFAULT_CURRENCY,
    ENTRY_TYPE_ALIASES,
    LOW_CONFIDENCE_BPS,
    SOURCE_ALIASES,
)
from finance.errors import FinanceError
from finance.masking import mask_identifier
from finance.money import parse_amount, parse_confidence

_CATEGORY_BY_KEY = {name.casefold(): name for name in CATEGORIES}
_MAX_TEXT = 500


@dataclass(frozen=True)
class NormalizedTransaction:
    date: str
    account: str
    account_key: str
    merchant: str | None
    description: str | None
    amount_minor: int
    currency: str
    entry_type: str
    category: str | None
    subcategory: str | None
    payment_method: str | None
    reference_id: str | None
    source: str
    source_message_id: str | None
    confidence_bps: int
    category_uncertain: bool
    fingerprint: str


def parse_date(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FinanceError("invalid_date", "date is required. Use YYYY-MM-DD or DD/MM/YYYY")
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise FinanceError("invalid_date", "date must be YYYY-MM-DD or DD/MM/YYYY")


def parse_month(value: object) -> tuple[str, str]:
    if not isinstance(value, str):
        raise FinanceError("invalid_month", "month must be YYYY-MM")
    try:
        start = datetime.strptime(value.strip(), "%Y-%m").date()
    except ValueError as exc:
        raise FinanceError("invalid_month", "month must be YYYY-MM") from exc
    if start.month == 12:
        end_month = start.replace(year=start.year + 1, month=1, day=1)
    else:
        end_month = start.replace(month=start.month + 1, day=1)
    end = end_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def require_range(start_date: object, end_date: object) -> tuple[str, str]:
    start = parse_date(start_date)
    end = parse_date(end_date)
    if start > end:
        raise FinanceError("invalid_date", "start_date must be on or before end_date")
    return start, end


def clean_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FinanceError("invalid_field", f"{field} must be text")
    text = " ".join(value.split())
    if not text:
        return None
    if len(text) > _MAX_TEXT:
        raise FinanceError("invalid_field", f"{field} is too long")
    return text


def _fingerprint(txn: dict[str, object]) -> str:
    payload = json.dumps(
        [
            txn["date"],
            str(txn["amount_minor"]),
            txn["currency"],
            txn["account_key"],
            txn["merchant"],
            txn["description"],
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def normalize_transaction(
    *,
    date: object,
    account: object,
    amount: object,
    entry_type: object,
    currency: object = DEFAULT_CURRENCY,
    merchant: object = None,
    description: object = None,
    category: object = None,
    subcategory: object = None,
    payment_method: object = None,
    reference_id: object = None,
    source: object = "manual",
    source_message_id: object = None,
    confidence: object = None,
) -> NormalizedTransaction:
    parsed_date = parse_date(date)
    if not isinstance(account, str) or not account.strip():
        raise FinanceError("invalid_account", "account is required")
    display_account = mask_identifier(account)
    if not display_account:
        raise FinanceError("invalid_account", "account is required")

    if not isinstance(entry_type, str):
        raise FinanceError("invalid_type", "type must be debit, credit, or transfer")
    canonical_type = ENTRY_TYPE_ALIASES.get(entry_type.strip().casefold())
    if canonical_type is None:
        raise FinanceError("invalid_type", "type must be debit, credit, or transfer")

    if not isinstance(source, str):
        raise FinanceError("invalid_source", "source is not supported")
    canonical_source = SOURCE_ALIASES.get(" ".join(source.split()).casefold())
    if canonical_source is None:
        raise FinanceError(
            "invalid_source",
            "source must be gmail, bank_statement, manual, or investment_api",
        )

    currency_text = DEFAULT_CURRENCY if currency is None else str(currency)
    canonical_currency = currency_text.strip().upper()
    if len(canonical_currency) != 3 or not canonical_currency.isalpha():
        raise FinanceError("invalid_currency", "currency must be a 3-letter code")

    category_text = clean_text(category, "category")
    canonical_category = None
    if category_text is not None:
        canonical_category = _CATEGORY_BY_KEY.get(category_text.casefold())

    default_bps = 8500 if canonical_category else 4000
    confidence_bps = parse_confidence(confidence, default_bps)
    uncertain = canonical_category is None or confidence_bps < LOW_CONFIDENCE_BPS
    merchant_text = clean_text(merchant, "merchant")
    description_text = clean_text(description, "description")
    account_key = display_account.casefold()
    parts = {
        "date": parsed_date,
        "amount_minor": parse_amount(amount),
        "currency": canonical_currency,
        "account_key": account_key,
        "merchant": None if merchant_text is None else merchant_text.casefold(),
        "description": None if description_text is None else description_text.casefold(),
    }
    return NormalizedTransaction(
        date=parsed_date,
        account=display_account,
        account_key=account_key,
        merchant=merchant_text,
        description=description_text,
        amount_minor=int(parts["amount_minor"]),
        currency=canonical_currency,
        entry_type=canonical_type,
        category=canonical_category,
        subcategory=clean_text(subcategory, "subcategory"),
        payment_method=clean_text(payment_method, "payment_method"),
        reference_id=mask_identifier(clean_text(reference_id, "reference_id")),
        source=canonical_source,
        source_message_id=clean_text(source_message_id, "source_message_id"),
        confidence_bps=confidence_bps,
        category_uncertain=uncertain,
        fingerprint=_fingerprint(parts),
    )
