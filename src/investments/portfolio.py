"""Read-only portfolio and SIP views. This module cannot place orders or edit SIPs."""

from pathlib import Path

from finance.constants import DEFAULT_CURRENCY
from finance.errors import FinanceError
from finance.json_store import read_object
from finance.money import format_amount, parse_amount


def _money(value: object, field: str) -> int:
    try:
        return parse_amount(value, allow_zero=True)
    except FinanceError as exc:
        raise FinanceError("invalid_config", f"{field} {exc.message}") from exc


def load_portfolio(data_dir: Path) -> dict[str, object]:
    raw = read_object(data_dir / "portfolio.json")
    holdings = raw.get("holdings", [])
    if holdings is None:
        holdings = []
    if not isinstance(holdings, list):
        raise FinanceError("invalid_config", "portfolio.json holdings must be a list")
    public: list[dict[str, object]] = []
    totals: dict[str, int] = {}
    for index, holding in enumerate(holdings):
        if not isinstance(holding, dict):
            raise FinanceError("invalid_config", "each holding must be an object")
        currency = str(holding.get("currency") or DEFAULT_CURRENCY).strip().upper()
        current = holding.get("current_value")
        missing_value = current in (None, "")
        amount_minor = 0 if missing_value else _money(current, f"holdings[{index}].current_value")
        if not missing_value:
            totals[currency] = totals.get(currency, 0) + amount_minor
        public_holding = dict(holding)
        public_holding["current_value"] = None if missing_value else format_amount(amount_minor)
        public_holding["currency"] = currency
        public_holding["value_known"] = not missing_value
        public.append(public_holding)
    return {
        "holdings": public,
        "values_complete": all(item["value_known"] for item in public),
        "totals_by_currency": [
            {"currency": currency, "current_value": format_amount(amount)}
            for currency, amount in sorted(totals.items())
        ],
    }


def load_sips(data_dir: Path) -> list[dict[str, object]]:
    raw = read_object(data_dir / "portfolio.json")
    sips = raw.get("sips", [])
    if sips is None:
        sips = []
    if not isinstance(sips, list):
        raise FinanceError("invalid_config", "portfolio.json sips must be a list")
    public: list[dict[str, object]] = []
    for sip in sips:
        if not isinstance(sip, dict):
            raise FinanceError("invalid_config", "each SIP must be an object")
        public.append(dict(sip))
    return public
