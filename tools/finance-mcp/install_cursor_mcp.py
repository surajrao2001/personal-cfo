"""Register the Finance MCP in the user config Cursor lists by default.

Customize → MCPs opens on the user account. A project file at
.cursor/mcp.json stays hidden until that folder is ticked in the scope
dropdown. This writes the same server into ~/.cursor/mcp.json, which is
the list on screen, and leaves every other server untouched.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def user_mcp_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def finance_entry(root: Path, command: str) -> dict:
    return {
        "type": "stdio",
        "command": command,
        "args": [str(root / "tools" / "finance-mcp" / "server.py")],
        "env": {"PERSONAL_CFO_DATA_DIR": str(root / "data")},
    }


def load_config(path: Path) -> dict:
    if not path.exists():
        return {"mcpServers": {}}
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must be a JSON object")
    servers = parsed.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"{path} mcpServers must be an object")
    parsed["mcpServers"] = servers
    return parsed


def merge_finance(config: dict, root: Path, command: str) -> dict:
    updated = dict(config)
    servers = dict(updated.get("mcpServers", {}))
    servers["finance"] = finance_entry(root, command)
    updated["mcpServers"] = servers
    return updated


def install(path: Path, root: Path, command: str) -> Path:
    config = merge_finance(load_config(path), root, command)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    destination = install(user_mcp_path(), ROOT, sys.executable)
    print(f"Wrote the finance server to {destination}")
    print("Quit Cursor completely, then open Customize → MCPs. finance is listed on your user account.")


if __name__ == "__main__":
    main()
