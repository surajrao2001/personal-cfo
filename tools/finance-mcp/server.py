"""Local Finance MCP server.

Speaks MCP over stdin and stdout. It does not open a port.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from finance.errors import FinanceError
from finance.service import FinanceService, resolve_data_dir

READ = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
LOCAL_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)
IDEMPOTENT_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

mcp = FastMCP(
    name="finance",
    instructions=(
        "Local personal-finance ledger stored in SQLite and JSON on this machine. "
        "Read tools report stored data. Write tools only add a normalized transaction, "
        "change a category, mark a row reviewed, or store reconciliation metadata. "
        "This server cannot move money, trade, change SIPs, or delete transactions."
    ),
)


def _service() -> FinanceService:
    return FinanceService(resolve_data_dir())


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FinanceError as exc:
        return exc.to_dict()


@mcp.tool(annotations=READ)
def get_profile() -> dict:
    """Read the local profile document. Does not change any financial record."""
    return _call(_service().get_profile)


@mcp.tool(annotations=READ)
def get_transactions(start_date: str, end_date: str) -> dict:
    """Read normalized ledger rows in an inclusive date range. Dates are YYYY-MM-DD or DD/MM/YYYY."""
    return _call(_service().get_transactions, start_date, end_date)


@mcp.tool(annotations=READ)
def search_transactions(query: str) -> dict:
    """Search merchant, description, category, reference, and account text in the local ledger."""
    return _call(_service().search_transactions, query)


@mcp.tool(annotations=READ)
def get_transaction(transaction_id: str) -> dict:
    """Read one ledger row by id."""
    return _call(_service().get_transaction, transaction_id)


@mcp.tool(annotations=READ)
def get_monthly_spending(month: str) -> dict:
    """Read consumption spending for one YYYY-MM month. Transfers and investments are excluded."""
    return _call(_service().get_monthly_spending, month)


@mcp.tool(annotations=READ)
def get_cashflow(start_date: str, end_date: str) -> dict:
    """Read income, consumption, investments, transfers, savings, and net cash flow for a date range."""
    return _call(_service().get_cashflow, start_date, end_date)


@mcp.tool(annotations=READ)
def get_category_spending(start_date: str, end_date: str) -> dict:
    """Read consumption totals by category for a date range. Transfers and investments are excluded."""
    return _call(_service().get_category_spending, start_date, end_date)


@mcp.tool(annotations=READ)
def get_account_balances() -> dict:
    """Read balances from data/accounts.json. Full account numbers are not returned."""
    return _call(_service().get_account_balances)


@mcp.tool(annotations=READ)
def get_net_worth() -> dict:
    """Read account assets, liabilities, portfolio value, and net worth by currency."""
    return _call(_service().get_net_worth)


@mcp.tool(annotations=READ)
def get_portfolio() -> dict:
    """Read holdings from data/portfolio.json. This does not place trades."""
    return _call(_service().get_portfolio)


@mcp.tool(annotations=READ)
def get_sips() -> dict:
    """Read SIP records from data/portfolio.json. This does not create or modify a SIP."""
    return _call(_service().get_sips)


@mcp.tool(annotations=READ)
def get_goals() -> dict:
    """Read goals from data/goals.json."""
    return _call(_service().get_goals)


@mcp.tool(annotations=READ)
def calculate_savings_rate(start_date: str | None = None, end_date: str | None = None) -> dict:
    """Calculate savings rate from the local ledger. Omit dates to use the full ledger."""
    return _call(_service().calculate_savings_rate, start_date, end_date)


@mcp.tool(annotations=READ)
def calculate_investment_rate(start_date: str | None = None, end_date: str | None = None) -> dict:
    """Calculate investment rate from the local ledger. This does not move money."""
    return _call(_service().calculate_investment_rate, start_date, end_date)


@mcp.tool(annotations=LOCAL_WRITE)
def add_transaction(
    date: str,
    account: str,
    amount: str,
    type: str,
    currency: str = "INR",
    merchant: str | None = None,
    description: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    payment_method: str | None = None,
    reference_id: str | None = None,
    source: str = "manual",
    source_message_id: str | None = None,
    confidence: float | None = None,
    accept_uncertain_duplicate: bool = False,
) -> dict:
    """Add one normalized local transaction.

    type is debit, credit, or transfer.
    source is gmail, bank_statement, manual, or investment_api.
    Exact duplicates are not inserted. Uncertain duplicates are flagged unless
    accept_uncertain_duplicate is true. Transactions are never deleted.
    """
    return _call(
        _service().add_transaction,
        date=date,
        account=account,
        amount=amount,
        entry_type=type,
        currency=currency,
        merchant=merchant,
        description=description,
        category=category,
        subcategory=subcategory,
        payment_method=payment_method,
        reference_id=reference_id,
        source=source,
        source_message_id=source_message_id,
        confidence=confidence,
        accept_uncertain_duplicate=accept_uncertain_duplicate,
    )


@mcp.tool(annotations=IDEMPOTENT_WRITE)
def update_transaction_category(
    transaction_id: str,
    category: str,
    subcategory: str | None = None,
    confidence: float | None = None,
) -> dict:
    """Change only the category metadata of one local transaction. Amount and date stay the same."""
    return _call(
        _service().update_transaction_category,
        transaction_id,
        category,
        subcategory,
        confidence,
    )


@mcp.tool(annotations=IDEMPOTENT_WRITE)
def mark_transaction_reviewed(transaction_id: str) -> dict:
    """Mark one local transaction reviewed. This does not change its amount."""
    return _call(_service().mark_transaction_reviewed, transaction_id)


@mcp.tool(annotations=LOCAL_WRITE)
def create_reconciliation_record(
    source_label: str,
    period_start: str | None = None,
    period_end: str | None = None,
    matched_transaction_ids: list[str] | None = None,
    discrepancies_json: str | None = None,
    notes: str | None = None,
) -> dict:
    """Store a local reconciliation note. This does not overwrite or delete transactions.

    discrepancies_json is an optional JSON array describing mismatches.
    """
    return _call(
        _service().create_reconciliation_record,
        source_label,
        period_start,
        period_end,
        matched_transaction_ids,
        discrepancies_json,
        notes,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
