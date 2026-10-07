"""Cash-flow, category, savings, and investment-rate calculations."""

import sqlite3
from dataclasses import dataclass, field

from finance.constants import EXPENSE_CATEGORIES, UNCERTAIN_CATEGORY
from finance.money import format_amount, format_rate


def classify(entry_type: str, category: str | None) -> str:
    if entry_type == "transfer" or category == "Transfers":
        return "transfer"
    if category == "Investments":
        if entry_type == "credit":
            return "investment_in"
        if entry_type == "debit":
            return "investment_out"
        return "transfer"
    if entry_type == "credit":
        if category in EXPENSE_CATEGORIES:
            return "refund"
        return "income"
    if entry_type == "debit":
        if category == "Salary":
            return "excluded"
        return "expense"
    return "excluded"


@dataclass
class Totals:
    income: int = 0
    expenses: int = 0
    investment_out: int = 0
    investment_in: int = 0
    transfers: int = 0
    excluded: int = 0
    categories: dict[str, int] = field(default_factory=dict)

    @property
    def savings(self) -> int:
        return self.income - self.expenses

    @property
    def net_invested(self) -> int:
        return self.investment_out - self.investment_in

    @property
    def net_cashflow(self) -> int:
        return self.income - self.expenses - self.investment_out + self.investment_in


def accumulate(rows: list[sqlite3.Row]) -> dict[str, Totals]:
    grouped: dict[str, Totals] = {}
    for row in rows:
        bucket = grouped.setdefault(str(row["currency"]), Totals())
        amount = int(row["amount_minor"])
        kind = classify(str(row["entry_type"]), row["category"])
        if kind == "income":
            bucket.income += amount
        elif kind == "expense":
            bucket.expenses += amount
            name = row["category"] or UNCERTAIN_CATEGORY
            bucket.categories[name] = bucket.categories.get(name, 0) + amount
        elif kind == "refund":
            bucket.expenses -= amount
            name = row["category"] or UNCERTAIN_CATEGORY
            bucket.categories[name] = bucket.categories.get(name, 0) - amount
        elif kind == "investment_out":
            bucket.investment_out += amount
        elif kind == "investment_in":
            bucket.investment_in += amount
        elif kind == "transfer":
            bucket.transfers += amount
        else:
            bucket.excluded += amount
    return grouped


def _block(currency: str, bucket: Totals) -> dict[str, object]:
    return {
        "currency": currency,
        "income": format_amount(bucket.income),
        "expenses": format_amount(bucket.expenses),
        "investments": format_amount(bucket.investment_out),
        "investment_inflows": format_amount(bucket.investment_in),
        "net_invested": format_amount(bucket.net_invested),
        "transfers": format_amount(bucket.transfers),
        "excluded": format_amount(bucket.excluded),
        "savings": format_amount(bucket.savings),
        "net_cashflow": format_amount(bucket.net_cashflow),
        "savings_rate": format_rate(bucket.savings, bucket.income),
        "investment_rate": format_rate(bucket.net_invested, bucket.income),
    }


def _categories(bucket: Totals) -> list[dict[str, str]]:
    items = [(name, amount) for name, amount in bucket.categories.items() if amount != 0]
    items.sort(key=lambda item: (-item[1], item[0]))
    return [{"category": name, "total": format_amount(amount)} for name, amount in items]


def cashflow_report(rows: list[sqlite3.Row], start_date: str, end_date: str) -> dict[str, object]:
    grouped = accumulate(rows)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "by_currency": [_block(currency, grouped[currency]) for currency in sorted(grouped)],
    }


def category_report(rows: list[sqlite3.Row], start_date: str, end_date: str) -> dict[str, object]:
    grouped = accumulate(rows)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "by_currency": [
            {
                "currency": currency,
                "total": format_amount(grouped[currency].expenses),
                "categories": _categories(grouped[currency]),
            }
            for currency in sorted(grouped)
        ],
    }


def monthly_report(rows: list[sqlite3.Row], month: str, start_date: str, end_date: str) -> dict[str, object]:
    report = category_report(rows, start_date, end_date)
    report["month"] = month
    return report


def savings_report(rows: list[sqlite3.Row], start_date: str | None, end_date: str | None) -> dict[str, object]:
    grouped = accumulate(rows)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "by_currency": [
            {
                "currency": currency,
                "income": format_amount(bucket.income),
                "expenses": format_amount(bucket.expenses),
                "savings": format_amount(bucket.savings),
                "savings_rate": format_rate(bucket.savings, bucket.income),
            }
            for currency, bucket in ((key, grouped[key]) for key in sorted(grouped))
        ],
    }


def investment_report(rows: list[sqlite3.Row], start_date: str | None, end_date: str | None) -> dict[str, object]:
    grouped = accumulate(rows)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "by_currency": [
            {
                "currency": currency,
                "income": format_amount(bucket.income),
                "investments": format_amount(bucket.investment_out),
                "investment_inflows": format_amount(bucket.investment_in),
                "net_invested": format_amount(bucket.net_invested),
                "investment_rate": format_rate(bucket.net_invested, bucket.income),
            }
            for currency, bucket in ((key, grouped[key]) for key in sorted(grouped))
        ],
    }
