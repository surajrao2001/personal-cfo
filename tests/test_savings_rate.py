from finance.service import FinanceService
from helpers import seed_january


def test_savings_rate_uses_income_minus_consumption(service: FinanceService) -> None:
    seed_january(service)
    report = service.calculate_savings_rate("2026-01-01", "2026-01-31")
    bucket = report["by_currency"][0]

    assert bucket["income"] == "100000.00"
    assert bucket["expenses"] == "2400.00"
    assert bucket["savings"] == "97600.00"
    assert bucket["savings_rate"] == "0.9760"


def test_savings_rate_is_null_without_income(service: FinanceService) -> None:
    service.add_transaction(
        date="2026-03-01",
        account="Cash",
        amount="50.00",
        entry_type="debit",
        category="Food",
        merchant="City Cafe",
        description="Snack",
        source="manual",
    )
    report = service.calculate_savings_rate()
    assert report["by_currency"][0]["savings_rate"] is None
