"""Local JSON documents. Missing files stay missing until the user creates them."""

import json
from pathlib import Path

from finance.errors import FinanceError
from finance.masking import scrub


def read_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FinanceError("invalid_config", f"{path.name} is not valid JSON") from exc
    if not isinstance(loaded, dict):
        raise FinanceError("invalid_config", f"{path.name} must be a JSON object")
    scrubbed = scrub(loaded)
    if not isinstance(scrubbed, dict):
        raise FinanceError("invalid_config", f"{path.name} must be a JSON object")
    return scrubbed
