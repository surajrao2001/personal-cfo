from finance.service import FinanceService


def add(service: FinanceService, **overrides: object) -> dict:
    payload: dict[str, object] = {
        "date": "2026-01-15",
        "account": "HDFC Savings",
        "amount": "100.00",
        "entry_type": "debit",
        "merchant": "North Market",
        "description": "Test purchase",
        "category": "Food",
        "source": "manual",
        "currency": "INR",
    }
    payload.update(overrides)
    return service.add_transaction(**payload)


def seed_january(service: FinanceService) -> list[dict]:
    rows = [
        {
            "date": "2026-01-01",
            "amount": "100000.00",
            "entry_type": "credit",
            "category": "Salary",
            "merchant": "Employer",
            "description": "January salary",
            "reference_id": "SAL-JAN",
        },
        {
            "date": "2026-01-02",
            "amount": "2000.00",
            "entry_type": "debit",
            "category": "Groceries",
            "merchant": "North Market",
            "description": "Groceries",
            "reference_id": "GR-1",
        },
        {
            "date": "2026-01-03",
            "amount": "500.00",
            "entry_type": "debit",
            "category": "Food",
            "merchant": "City Cafe",
            "description": "Lunch",
            "reference_id": "FD-1",
        },
        {
            "date": "2026-01-04",
            "amount": "20000.00",
            "entry_type": "debit",
            "category": "Investments",
            "merchant": "Index Fund",
            "description": "SIP contribution",
            "reference_id": "SIP-1",
        },
        {
            "date": "2026-01-05",
            "amount": "3000.00",
            "entry_type": "transfer",
            "category": "Transfers",
            "merchant": "Own account",
            "description": "Move to savings",
            "reference_id": "TR-1",
        },
        {
            "date": "2026-01-06",
            "amount": "1000.00",
            "entry_type": "credit",
            "category": "Investments",
            "merchant": "Index Fund",
            "description": "Redemption",
            "reference_id": "RED-1",
        },
        {
            "date": "2026-01-07",
            "amount": "100.00",
            "entry_type": "credit",
            "category": "Food",
            "merchant": "City Cafe",
            "description": "Lunch refund",
            "reference_id": "FD-R",
        },
    ]
    return [add(service, **row) for row in rows]
