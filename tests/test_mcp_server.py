import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.shared.memory import create_connected_server_and_client_session

from finance.service import FinanceService
from gmail import GmailNotConnectedError, fetch_messages

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "get_profile",
    "get_transactions",
    "search_transactions",
    "get_transaction",
    "get_monthly_spending",
    "get_cashflow",
    "get_category_spending",
    "get_account_balances",
    "get_net_worth",
    "get_portfolio",
    "get_sips",
    "get_goals",
    "calculate_savings_rate",
    "calculate_investment_rate",
    "add_transaction",
    "update_transaction_category",
    "mark_transaction_reviewed",
    "create_reconciliation_record",
}
FORBIDDEN_TOOLS = {
    "delete_transaction",
    "transfer_funds",
    "place_trade",
    "update_sip",
    "create_payment",
    "send_payment",
}


def test_user_mcp_install_adds_finance_without_removing_other_servers(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "install_cursor_mcp",
        ROOT / "tools" / "finance-mcp" / "install_cursor_mcp.py",
    )
    assert spec is not None and spec.loader is not None
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)

    destination = tmp_path / ".cursor" / "mcp.json"
    destination.parent.mkdir()
    destination.write_text(
        json.dumps({"mcpServers": {"other": {"command": "echo", "args": ["hi"]}}}),
        encoding="utf-8",
    )
    installer.install(destination, ROOT, sys.executable)
    saved = json.loads(destination.read_text(encoding="utf-8"))
    assert saved["mcpServers"]["other"]["command"] == "echo"
    finance = saved["mcpServers"]["finance"]
    assert finance["type"] == "stdio"
    assert finance["command"] == sys.executable
    assert finance["args"] == [str(ROOT / "tools" / "finance-mcp" / "server.py")]
    assert "${workspaceFolder}" not in finance["args"][0]
    assert finance["env"]["PERSONAL_CFO_DATA_DIR"] == str(ROOT / "data")
    assert "${workspaceFolder}" not in finance["env"]["PERSONAL_CFO_DATA_DIR"]


def test_cursor_mcp_config_points_at_the_local_server() -> None:
    config = json.loads((ROOT / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    finance = config["mcpServers"]["finance"]
    assert finance["type"] == "stdio"
    assert finance["command"] == "python3"
    assert finance["args"] == ["${workspaceFolder}/tools/finance-mcp/server.py"]
    assert finance["env"]["PERSONAL_CFO_DATA_DIR"] == "${workspaceFolder}/data"
    assert (ROOT / "tools" / "finance-mcp" / "server.py").is_file()


def _load_server():
    spec = importlib.util.spec_from_file_location(
        "finance_mcp_server",
        ROOT / "tools" / "finance-mcp" / "server.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(result) -> dict:
    assert result.isError is False
    structured = result.structuredContent
    if isinstance(structured, dict):
        if set(structured) == {"result"} and isinstance(structured["result"], dict):
            return structured["result"]
        return structured
    return json.loads(result.content[0].text)


def test_local_documents_balances_and_gmail_stays_disconnected(data_dir: Path, service: FinanceService) -> None:
    (data_dir / "profile.json").write_text(
        json.dumps({"display_name": "Test", "base_currency": "INR", "otp": "do-not-keep"}),
        encoding="utf-8",
    )
    (data_dir / "accounts.json").write_text(
        json.dumps(
            {
                "accounts": [
                    {"id": "cash", "name": "Cash", "type": "asset", "balance": "1000.00", "currency": "INR"},
                    {
                        "id": "card",
                        "name": "Card",
                        "type": "liability",
                        "balance": "200.00",
                        "currency": "INR",
                        "account_number": "1234567890123456",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "portfolio.json").write_text(
        json.dumps(
            {
                "holdings": [
                    {"name": "Index fund", "current_value": "500.00", "currency": "INR"},
                ],
                "sips": [
                    {"name": "Index SIP", "amount": "100.00", "currency": "INR", "frequency": "monthly"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "goals.json").write_text(
        json.dumps({"goals": [{"name": "Emergency fund", "target_amount": "1000.00", "currency": "INR"}]}),
        encoding="utf-8",
    )

    profile = service.get_profile()["profile"]
    assert profile["display_name"] == "Test"
    assert "otp" not in profile

    balances = json.dumps(service.get_account_balances())
    assert "1234567890123456" not in balances
    assert "XXXX3456" in balances

    worth = service.get_net_worth()["by_currency"][0]
    assert worth["account_assets"] == "1000.00"
    assert worth["liabilities"] == "200.00"
    assert worth["portfolio_value"] == "500.00"
    assert worth["net_worth"] == "1300.00"
    assert service.get_sips()["sips"][0]["name"] == "Index SIP"
    assert service.get_goals()["goals"][0]["name"] == "Emergency fund"

    try:
        fetch_messages()
    except GmailNotConnectedError:
        pass
    else:
        raise AssertionError("Gmail access should be refused")

    created = service.add_transaction(
        date="2026-04-02",
        account="Cash",
        amount="15.00",
        entry_type="debit",
        category="Food",
        merchant="Test Kiosk",
        description="Offline gmail-shaped row",
        source="gmail",
        source_message_id="msg-1",
    )
    assert created["status"] == "created"
    assert created["transaction"]["source"] == "gmail"


def test_mcp_tools_round_trip_with_test_data(data_dir: Path, monkeypatch) -> None:
    monkeypatch.setenv("PERSONAL_CFO_DATA_DIR", str(data_dir))
    module = _load_server()

    async def exercise() -> None:
        async with create_connected_server_and_client_session(module.mcp, raise_exceptions=True) as session:
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names == EXPECTED_TOOLS
            assert names.isdisjoint(FORBIDDEN_TOOLS)
            by_name = {tool.name: tool for tool in listed.tools}
            assert by_name["get_profile"].annotations.readOnlyHint is True
            assert by_name["add_transaction"].annotations.readOnlyHint is False

            created = _payload(
                await session.call_tool(
                    "add_transaction",
                    {
                        "date": "2026-04-01",
                        "account": "Cash",
                        "amount": "42.00",
                        "type": "debit",
                        "merchant": "Test Kiosk",
                        "description": "Sample snack",
                        "category": "Food",
                        "source": "manual",
                    },
                )
            )
            assert created["status"] == "created"
            transaction_id = created["transaction"]["id"]

            updated = _payload(
                await session.call_tool(
                    "update_transaction_category",
                    {"transaction_id": transaction_id, "category": "Groceries"},
                )
            )
            assert updated["transaction"]["category"] == "Groceries"
            assert updated["transaction"]["amount"] == "42.00"

            reviewed = _payload(
                await session.call_tool(
                    "mark_transaction_reviewed",
                    {"transaction_id": transaction_id},
                )
            )
            assert reviewed["transaction"]["reviewed"] is True
            assert reviewed["transaction"]["amount"] == "42.00"

            record = _payload(
                await session.call_tool(
                    "create_reconciliation_record",
                    {
                        "source_label": "April test statement",
                        "period_start": "2026-04-01",
                        "period_end": "2026-04-30",
                        "matched_transaction_ids": [transaction_id],
                        "notes": "Matched the sample row",
                    },
                )
            )
            assert record["record"]["matched_transaction_ids"] == [transaction_id]

            found = _payload(await session.call_tool("search_transactions", {"query": "Test Kiosk"}))
            assert len(found["transactions"]) == 1

        server = StdioServerParameters(
            command="python3",
            args=["tools/finance-mcp/server.py"],
            cwd=ROOT,
            env={
                "PERSONAL_CFO_DATA_DIR": str(data_dir),
                "HOME": os.environ.get("HOME", ""),
                "PATH": os.environ.get("PATH", ""),
            },
        )
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                spending = _payload(await session.call_tool("get_monthly_spending", {"month": "2026-04"}))
                assert spending["by_currency"][0]["total"] == "42.00"
                rates = _payload(await session.call_tool("calculate_savings_rate", {}))
                assert rates["by_currency"][0]["expenses"] == "42.00"

    asyncio.run(exercise())
