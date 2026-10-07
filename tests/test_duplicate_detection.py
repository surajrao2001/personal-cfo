from pathlib import Path

from finance.errors import FinanceError
from finance.service import FinanceService
from helpers import add


def test_reference_and_fingerprint_duplicates_are_not_inserted(service: FinanceService) -> None:
    first = add(service, reference_id="UTR-100", amount="250.00", description="Coffee")
    second = add(service, reference_id="UTR-100", amount="250.00", description="Coffee copy")
    third = add(
        service,
        reference_id=None,
        amount="80.00",
        description="Bus ticket",
        merchant="City Transit",
        category="Transport",
    )
    fourth = add(
        service,
        reference_id=None,
        amount="80.00",
        description="  bus   ticket ",
        merchant="city transit",
        category="Transport",
    )

    assert first["status"] == "created"
    assert second["status"] == "duplicate"
    assert second["inserted"] is False
    assert second["transaction"]["id"] == first["transaction"]["id"]
    assert third["status"] == "created"
    assert fourth["status"] == "duplicate"
    assert service.transaction_count() == 2


def test_uncertain_duplicate_is_flagged_until_explicitly_accepted(service: FinanceService) -> None:
    original = add(service, amount="500.00", merchant="North Market", description="Basket")
    flagged = add(service, amount="500.00", merchant="Other Shop", description="Different basket")

    assert flagged["status"] == "uncertain_duplicate"
    assert flagged["inserted"] is False
    assert flagged["candidates"][0]["id"] == original["transaction"]["id"]
    assert service.transaction_count() == 1

    accepted = add(
        service,
        amount="500.00",
        merchant="Other Shop",
        description="Different basket",
        accept_uncertain_duplicate=True,
    )
    assert accepted["status"] == "created"
    assert accepted["transaction"]["possible_duplicate_of"] == original["transaction"]["id"]
    assert service.transaction_count() == 2


def test_reference_conflict_does_not_overwrite_or_delete(service: FinanceService) -> None:
    created = add(service, reference_id="UTR-200", amount="999.00", description="Original")
    try:
        add(service, reference_id="UTR-200", amount="100.00", description="Changed")
    except FinanceError as exc:
        assert exc.code == "reference_conflict"
    else:
        raise AssertionError("expected a reference conflict")

    stored = service.get_transaction(created["transaction"]["id"])
    assert stored["transaction"]["amount"] == "999.00"
    assert stored["transaction"]["description"] == "Original"
    assert service.transaction_count() == 1


def test_transactions_are_not_deleted_by_the_ledger_code() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    assert "DELETE FROM transactions" not in source
    assert "DROP TABLE" not in source
