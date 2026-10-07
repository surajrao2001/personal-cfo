"""Register the Finance MCP in the user config Cursor lists by default.

The account list reads ~/.cursor/mcp.json on the computer where Cursor is
open. ${workspaceFolder} is left as plain text in that file, so this writes
absolute paths and leaves every other server untouched.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def user_mcp_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def venv_python(root: Path) -> Path:
    if sys.platform == "win32":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def finance_entry(root: Path, command: str) -> dict:
    server = root / "tools" / "finance-mcp" / "server.py"
    return {
        "type": "stdio",
        "command": command,
        "args": [str(server)],
        "env": {"PERSONAL_CFO_DATA_DIR": str(root / "data")},
    }


def ensure_local_python(root: Path) -> str:
    """Create a project virtualenv and install the MCP package into it."""
    python = venv_python(root)
    if not python.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(root / ".venv")])
    subprocess.check_call(
        [str(python), "-m", "pip", "install", "-r", str(root / "requirements.txt")]
    )
    return str(python)


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
    server = ROOT / "tools" / "finance-mcp" / "server.py"
    if not server.is_file():
        raise SystemExit(f"Missing {server}. Run this inside the personal-cfo checkout.")
    command = ensure_local_python(ROOT)
    destination = install(user_mcp_path(), ROOT, command)
    print(f"Wrote the finance server to {destination}")
    print(f"Python: {command}")
    print(f"Server: {server}")
    print("Quit Cursor completely, then open Customize → MCPs.")


if __name__ == "__main__":
    main()
