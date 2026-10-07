import pytest

from finance.errors import FinanceError
from finance.normalize import normalize_transaction


def test_normalizes_indian_date_amount_and_type_aliases() -> None:
    txn = normalize_transaction(
        date="15/01/2026",
        account="HDFC Savings",
        amount="1,250.50",
        entry_type="expense",
        currency="inr",
        merchant="  North   Market ",
        description="Weekly groceries",
        category=" groceries ",
        source="bank statement",
    )

    assert txn.date == "2026-01-15"
    assert txn.amount_minor == 125050
    assert txn.currency == "INR"
    assert txn.entry_type == "debit"
    assert txn.category == "Groceries"
    assert txn.merchant == "North Market"
    assert txn.source == "bank_statement"
    assert txn.category_uncertain is False


def test_does_not_invent_merchant_or_unknown_category() -> None:
    txn = normalize_transaction(
        date="2026-01-15",
        account="HDFC Savings",
        amount="10.00",
        entry_type="debit",
        merchant="   ",
        category="Rent",
        source="manual",
    )

    assert txn.merchant is None
    assert txn.category is None
    assert txn.category_uncertain is True
    assert txn.confidence_bps == 4000


def test_masks_account_numbers_and_rejects_bad_source() -> None:
    txn = normalize_transaction(
        date="2026-02-01",
        account="1234 5678 9012 3456",
        amount="10",
        entry_type="credit",
        source="gmail",
        reference_id="9988776655443322",
    )

    assert txn.account == "XXXX3456"
    assert txn.reference_id == "XXXX3322"
    assert "1234567890123456" not in txn.account

    with pytest.raises(FinanceError) as caught:
        normalize_transaction(
            date="2026-02-01",
            account="HDFC Savings",
            amount="10",
            entry_type="debit",
            source="mailbox",
        )
    assert caught.value.code == "invalid_source"


def test_rejects_extra_precision_and_non_positive_amounts() -> None:
    with pytest.raises(FinanceError) as extra:
        normalize_transaction(
            date="2026-02-01",
            account="Cash",
            amount="10.125",
            entry_type="debit",
            source="manual",
        )
    assert extra.value.code == "invalid_amount"

    with pytest.raises(FinanceError):
        normalize_transaction(
            date="2026-02-01",
            account="Cash",
            amount="0",
            entry_type="debit",
            source="manual",
        )


def test_low_confidence_marks_category_uncertain() -> None:
    txn = normalize_transaction(
        date="2026-02-01",
        account="Cash",
        amount="10.00",
        entry_type="debit",
        category="Food",
        confidence="0.40",
        source="manual",
    )
    assert txn.category == "Food"
    assert txn.category_uncertain is True
    assert txn.confidence_bps == 4000
