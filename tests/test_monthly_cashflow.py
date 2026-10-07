from finance.service import FinanceService
from helpers import seed_january


def test_monthly_cash_flow_separates_income_spending_and_investments(service: FinanceService) -> None:
    seed_january(service)
    spending = service.get_monthly_spending("2026-01")
    cashflow = service.get_cashflow("01/01/2026", "31/01/2026")

    assert spending["month"] == "2026-01"
    assert spending["by_currency"][0]["total"] == "2400.00"

    bucket = cashflow["by_currency"][0]
    assert bucket["income"] == "100000.00"
    assert bucket["expenses"] == "2400.00"
    assert bucket["investments"] == "20000.00"
    assert bucket["investment_inflows"] == "1000.00"
    assert bucket["transfers"] == "3000.00"
    assert bucket["savings"] == "97600.00"
    assert bucket["net_cashflow"] == "78600.00"
