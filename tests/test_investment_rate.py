from finance.service import FinanceService
from helpers import seed_january


def test_investment_rate_nets_redemptions_against_contributions(service: FinanceService) -> None:
    seed_january(service)
    report = service.calculate_investment_rate()
    bucket = report["by_currency"][0]

    assert report["start_date"] == "2026-01-01"
    assert report["end_date"] == "2026-01-07"
    assert bucket["investments"] == "20000.00"
    assert bucket["investment_inflows"] == "1000.00"
    assert bucket["net_invested"] == "19000.00"
    assert bucket["investment_rate"] == "0.1900"
    assert "does not place trades" in report["note"]
