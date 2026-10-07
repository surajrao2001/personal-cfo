from finance.service import FinanceService
from helpers import seed_january


def test_category_spending_nets_refunds_and_skips_investments(service: FinanceService) -> None:
    seed_january(service)
    report = service.get_category_spending("2026-01-01", "2026-01-31")

    assert report["ok"] is True
    bucket = report["by_currency"][0]
    assert bucket["currency"] == "INR"
    assert bucket["total"] == "2400.00"
    assert bucket["categories"] == [
        {"category": "Groceries", "total": "2000.00"},
        {"category": "Food", "total": "400.00"},
    ]
    names = {item["category"] for item in bucket["categories"]}
    assert "Investments" not in names
    assert "Transfers" not in names
    assert "Salary" not in names
