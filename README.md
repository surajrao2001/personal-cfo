# personal-cfo

Local-first personal finance and investment research agent. There is no UI. Cursor rules define how the agent behaves, and a local MCP server is the only integration point. Personal data stays in files on this machine.

Rule text, domain logic, and MCP tools are not written yet.

## Layout

```text
personal-cfo/
├── .cursor/
│   ├── rules/                  agent rules (content pending)
│   │   ├── cfo-core.mdc
│   │   ├── financial-data.mdc
│   │   ├── investment-research.mdc
│   │   └── security.mdc
│   └── mcp.json                registers the local finance MCP server
├── src/
│   ├── finance/                ledger and cash-flow logic
│   ├── gmail/                  mail ingestion
│   ├── reconciliation/         match imports to the ledger
│   ├── investments/            portfolio and research logic
│   └── reports/                report generation
├── data/                       local profile, accounts, portfolio, goals, ledger
├── imports/bank-statements/    raw statements dropped in locally
├── reports/                    generated reports
├── tools/finance-mcp/server.py local MCP entrypoint
├── .env                        local secrets (not committed)
└── .gitignore
```

## Local data

| Path | Role |
| --- | --- |
| `data/profile.json` | Household or personal profile |
| `data/accounts.json` | Account registry |
| `data/transactions.db` | Local transaction ledger (SQLite, not committed) |
| `data/portfolio.json` | Holdings snapshot |
| `data/goals.json` | Savings and investment goals |
| `imports/bank-statements/` | Unprocessed statement files (not committed) |
| `reports/` | Generated output (not committed) |
| `.env` | Secrets such as API keys (not committed) |

The JSON files are empty objects until requirements define their shape. Do not commit real financial records, statements, or secrets.
