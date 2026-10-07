"""Account balances and net worth from local JSON plus portfolio values."""

from pathlib import Path

from finance.constants import DEFAULT_CURRENCY
from finance.errors import FinanceError
from finance.json_store import read_object
from finance.money import format_amount, parse_amount
from investments.portfolio import load_portfolio


def _currency(value: object) -> str:
    text = DEFAULT_CURRENCY if value in (None, "") else str(value).strip().upper()
    if len(text) != 3 or not text.isalpha():
        raise FinanceError("invalid_config", "currency must be a 3-letter code")
    return text


def account_balances(data_dir: Path) -> dict[str, object]:
    raw = read_object(data_dir / "accounts.json")
    accounts = raw.get("accounts", [])
    if accounts is None:
        accounts = []
    if not isinstance(accounts, list):
        raise FinanceError("invalid_config", "accounts.json accounts must be a list")

    public: list[dict[str, object]] = []
    for index, account in enumerate(accounts):
        if not isinstance(account, dict):
            raise FinanceError("invalid_config", "each account must be an object")
        kind = str(account.get("type") or "asset").strip().lower()
        if kind not in {"asset", "liability"}:
            raise FinanceError("invalid_config", "account type must be asset or liability")
        balance = account.get("balance")
        known = balance not in (None, "")
        amount = None
        if known:
            try:
                amount = parse_amount(balance, allow_zero=True)
            except FinanceError as exc:
                raise FinanceError("invalid_config", f"accounts[{index}].balance {exc.message}") from exc
        public_account = {
            key: value
            for key, value in account.items()
            if key not in {"balance", "type", "currency"}
        }
        public_account.update(
            {
                "type": kind,
                "currency": _currency(account.get("currency")),
                "balance": None if amount is None else format_amount(amount),
                "complete": known,
            }
        )
        public.append(public_account)
    return {"accounts": public, "complete": all(item["complete"] for item in public)}


def net_worth(data_dir: Path) -> dict[str, object]:
    balances = account_balances(data_dir)
    portfolio = load_portfolio(data_dir)
    assets: dict[str, int] = {}
    liabilities: dict[str, int] = {}
    for account in balances["accounts"]:
        if not account["complete"]:
            continue
        assert isinstance(account["balance"], str)
        minor = parse_amount(account["balance"], allow_zero=True)
        currency = str(account["currency"])
        target = assets if account["type"] == "asset" else liabilities
        target[currency] = target.get(currency, 0) + minor

    portfolio_values: dict[str, int] = {}
    for total in portfolio["totals_by_currency"]:
        assert isinstance(total, dict)
        portfolio_values[str(total["currency"])] = parse_amount(total["current_value"], allow_zero=True)

    currencies = sorted(set(assets) | set(liabilities) | set(portfolio_values))
    by_currency = []
    for currency in currencies:
        asset_minor = assets.get(currency, 0) + portfolio_values.get(currency, 0)
        liability_minor = liabilities.get(currency, 0)
        by_currency.append(
            {
                "currency": currency,
                "account_assets": format_amount(assets.get(currency, 0)),
                "liabilities": format_amount(liability_minor),
                "portfolio_value": format_amount(portfolio_values.get(currency, 0)),
                "net_worth": format_amount(asset_minor - liability_minor),
            }
        )
    return {
        "by_currency": by_currency,
        "complete": bool(balances["complete"]) and bool(portfolio["values_complete"]),
    }
