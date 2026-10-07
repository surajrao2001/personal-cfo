# personal-cfo

Local-first personal finance and investment research agent. There is no UI and no web server. Cursor rules define how the agent behaves. The Finance MCP is the only data interface, and it speaks MCP over standard input and output.

Gmail sign-in is local and read-only. Mail is not downloaded yet. Transactions, categories, and reconciliation notes stay in SQLite on this machine. Profile, accounts, portfolio, SIPs, and goals stay in local JSON files.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest
python3 tools/finance-mcp/server.py
```

The server process waits for MCP messages on stdin. Do not write logs to stdout.

Cursor starts that process from `.cursor/mcp.json`. The config uses `${workspaceFolder}` so the ledger path stays inside this project even when Cursor's working directory is somewhere else:

```json
{
  "mcpServers": {
    "finance": {
      "type": "stdio",
      "command": "python3",
      "args": ["${workspaceFolder}/tools/finance-mcp/server.py"],
      "env": {
        "PERSONAL_CFO_DATA_DIR": "${workspaceFolder}/data"
      }
    }
  }
}
```

This file is on `cursor/finance-mcp-setup-a4ca`. Check out that branch, open the folder in Cursor desktop, then quit Cursor completely and open it again. The `finance` server is listed under Customize → MCPs for that folder.

Cloud Agents do not read this file on their own. On [cursor.com/agents](https://cursor.com/agents), open the MCP menu and add the same stdio server: command `python3`, args `${workspaceFolder}/tools/finance-mcp/server.py`, and env `PERSONAL_CFO_DATA_DIR=${workspaceFolder}/data`. The agent VM needs `python3 -m pip install -r requirements.txt` before the first tool call.

## Sign in to Gmail

Run this on the same computer where the browser will open:

```bash
python3 -m pip install -r requirements.txt
python3 src/gmail/login.py
```

Approve the Google prompt for read-only Gmail access. Google redirects to `http://localhost` on this computer, and the command saves `src/gmail/token.json`. That file is gitignored. The command does not download mail.

If the browser does not open, copy the printed URL into a browser on this same computer.

Set `PERSONAL_CFO_DATA_DIR` when you want the ledger and JSON files somewhere other than `data/`.

## Tools

Read tools:

- `get_profile`
- `get_transactions(start_date, end_date)`
- `search_transactions(query)`
- `get_transaction(transaction_id)`
- `get_monthly_spending(month)`
- `get_cashflow(start_date, end_date)`
- `get_category_spending(start_date, end_date)`
- `get_account_balances`
- `get_net_worth`
- `get_portfolio`
- `get_sips`
- `get_goals`
- `calculate_savings_rate`
- `calculate_investment_rate`

Controlled local writes:

- `add_transaction`
- `update_transaction_category`
- `mark_transaction_reviewed`
- `create_reconciliation_record`

The server cannot transfer money, trade, change a SIP, make a payment, or delete a transaction.

## Ledger

SQLite file: `data/transactions.db` (not committed).

Each transaction stores id, date, account, merchant, description, amount, currency, type (`debit`, `credit`, or `transfer`), category, subcategory, payment method, reference id, source, source message id, confidence, and timestamps. `source` is one of `gmail`, `bank_statement`, `manual`, or `investment_api`.

Amounts use two decimal places. The default currency is INR. Dates accept `YYYY-MM-DD` and `DD/MM/YYYY`.

Supported categories are Housing, Food, Groceries, Transport, Utilities, Shopping, Entertainment, Travel, Health, Education, Insurance, Debt, Investments, Transfers, Salary, and Other. An unknown category is left blank and marked uncertain. Merchant text is stored only when you supply it.

### Duplicates

An exact duplicate is the same account plus reference id, or the same date, amount, account, merchant, and description. Exact duplicates are not inserted.

If the reference id already exists with a different amount or date, the ledger is left unchanged.

If the date, amount, and account match but the merchant or description differs, the insert is refused and the existing rows are returned as an uncertain duplicate. Pass `accept_uncertain_duplicate=true` only when you have decided it is a separate transaction. The new row points at the earlier one with `possible_duplicate_of`.

Nothing in the ledger deletes a transaction.

### Rates

Savings rate is `(income - consumption expenses) / income`. Transfers and investment rows are outside consumption. A credit in an expense category, such as a refund, reduces that expense.

Investment rate is `(investment purchases - redemptions) / income`.

Omit the dates on either rate tool to use every row in the ledger.

## Local JSON

`data/profile.json` is returned as stored, with secret-like keys removed.

`data/accounts.json`:

```json
{
  "accounts": [
    {"id": "cash", "name": "Cash", "type": "asset", "balance": "0.00", "currency": "INR"}
  ]
}
```

Use `type` `asset` or `liability`. Do not put a full account number in this file. If one is present, responses show only the last four digits.

`data/portfolio.json`:

```json
{
  "holdings": [
    {"name": "Example fund", "current_value": "0.00", "currency": "INR"}
  ],
  "sips": [
    {"name": "Example SIP", "amount": "0.00", "currency": "INR", "frequency": "monthly"}
  ]
}
```

Holdings and SIPs are read-only. Net worth is account assets plus holding values, minus liabilities. Do not list the same holding both as an account balance and as a portfolio value.

`data/goals.json` is `{"goals": []}` until you add goal objects.

Bank statements dropped in `imports/bank-statements/` and files written under `reports/` are gitignored.

## Layout

```text
src/finance/            normalization, dedup, SQLite ledger, balances
src/gmail/              read-only sign-in; mail download is not enabled
src/reconciliation/     reconciliation metadata only
src/investments/        read-only portfolio and SIPs
src/reports/            cash-flow and rate calculations
tools/finance-mcp/server.py
```
