"""Closed sets for ledger fields. Categories stay conservative on purpose."""

CATEGORIES = (
    "Housing",
    "Food",
    "Groceries",
    "Transport",
    "Utilities",
    "Shopping",
    "Entertainment",
    "Travel",
    "Health",
    "Education",
    "Insurance",
    "Debt",
    "Investments",
    "Transfers",
    "Salary",
    "Other",
)

EXPENSE_CATEGORIES = frozenset(
    {
        "Housing",
        "Food",
        "Groceries",
        "Transport",
        "Utilities",
        "Shopping",
        "Entertainment",
        "Travel",
        "Health",
        "Education",
        "Insurance",
        "Debt",
    }
)

SOURCES = frozenset({"gmail", "bank_statement", "manual", "investment_api"})

ENTRY_TYPES = frozenset({"debit", "credit", "transfer"})

SOURCE_ALIASES = {
    "gmail": "gmail",
    "bank_statement": "bank_statement",
    "bank statement": "bank_statement",
    "manual": "manual",
    "investment_api": "investment_api",
    "investment api": "investment_api",
}

ENTRY_TYPE_ALIASES = {
    "debit": "debit",
    "dr": "debit",
    "expense": "debit",
    "withdrawal": "debit",
    "credit": "credit",
    "cr": "credit",
    "income": "credit",
    "deposit": "credit",
    "transfer": "transfer",
}

LOW_CONFIDENCE_BPS = 6000
DEFAULT_CURRENCY = "INR"
UNCERTAIN_CATEGORY = "Uncategorized"
