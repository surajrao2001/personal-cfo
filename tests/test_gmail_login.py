from pathlib import Path

import pytest
from google.oauth2.credentials import Credentials

from gmail.login import GmailSignInError, SCOPES, _ensure_readonly, sign_in


def test_sign_in_requests_readonly_scope_only() -> None:
    assert SCOPES == ("https://www.googleapis.com/auth/gmail.readonly",)


def test_readonly_credentials_are_accepted() -> None:
    _ensure_readonly(Credentials(token="local-test", scopes=list(SCOPES)))


def test_write_scopes_are_rejected() -> None:
    with pytest.raises(GmailSignInError):
        _ensure_readonly(
            Credentials(
                token="local-test",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.modify",
                ],
            )
        )


def test_missing_client_file_does_not_open_a_browser(tmp_path: Path) -> None:
    with pytest.raises(GmailSignInError, match="credentials.json"):
        sign_in(tmp_path / "credentials.json", tmp_path / "token.json", open_browser=False)


def test_token_file_is_gitignored() -> None:
    root = Path(__file__).resolve().parents[1]
    ignored = (root / ".gitignore").read_text(encoding="utf-8")
    assert "src/gmail/token.json" in ignored
    assert "src/gmail/credentials.json" in ignored
