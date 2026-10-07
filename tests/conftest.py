import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finance.service import FinanceService


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    for name in ("profile.json", "accounts.json", "portfolio.json", "goals.json"):
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def service(data_dir: Path) -> FinanceService:
    return FinanceService(data_dir)
