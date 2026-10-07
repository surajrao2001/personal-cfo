"""One-time Gmail sign-in on this computer.

The browser and this command must run on the same machine. Google redirects
to http://localhost, and this process receives that redirect. The saved token
is read-only. This command does not download mail.
"""

from __future__ import annotations

import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ("https://www.googleapis.com/auth/gmail.readonly",)
_GMAIL_DIR = Path(__file__).resolve().parent


class GmailSignInError(RuntimeError):
    """Raised when local Gmail sign-in cannot start."""


def sign_in(
    credentials_file: Path | None = None,
    token_file: Path | None = None,
    *,
    open_browser: bool = True,
) -> str:
    """Sign in with the local OAuth client and store a read-only token.

    Returns "existing" when a usable token is already present, or "created"
    when a new browser sign-in succeeds.
    """
    credentials_path = credentials_file or (_GMAIL_DIR / "credentials.json")
    token_path = token_file or (_GMAIL_DIR / "token.json")
    if not credentials_path.is_file():
        raise GmailSignInError(
            f"Missing {credentials_path}. Download the Desktop OAuth client JSON "
            "from Google Cloud and save it at that path."
        )

    saved = _load_token(token_path)
    if saved is not None:
        return "existing"

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), list(SCOPES))
    credentials = flow.run_local_server(
        host="localhost",
        bind_addr="127.0.0.1",
        port=0,
        open_browser=open_browser,
        authorization_prompt_message="Open this URL in a browser on this computer:\n{url}\n",
        success_message="Gmail read-only access granted. You can close this tab.",
        access_type="offline",
        prompt="consent",
    )
    _ensure_readonly(credentials)
    _write_token(token_path, credentials)
    return "created"


def _load_token(token_file: Path) -> Credentials | None:
    if not token_file.is_file():
        return None
    try:
        credentials = Credentials.from_authorized_user_file(str(token_file), list(SCOPES))
    except (ValueError, OSError):
        return None
    if not credentials.has_scopes(list(SCOPES)):
        return None
    if credentials.valid:
        return credentials
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        _ensure_readonly(credentials)
        _write_token(token_file, credentials)
        return credentials
    return None


def _ensure_readonly(credentials: Credentials) -> None:
    scopes = set(credentials.scopes or [])
    allowed = set(SCOPES)
    if not allowed.issubset(scopes):
        raise GmailSignInError("Gmail sign-in did not grant read-only access.")
    if any(scope != SCOPES[0] and scope.startswith("https://www.googleapis.com/auth/gmail") for scope in scopes):
        raise GmailSignInError("Gmail sign-in granted more than read-only access.")
    if "https://mail.google.com/" in scopes:
        raise GmailSignInError("Gmail sign-in granted full mailbox access.")


def _write_token(token_file: Path, credentials: Credentials) -> None:
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    token_file.chmod(0o600)


def main() -> None:
    try:
        result = sign_in()
    except GmailSignInError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    if result == "existing":
        print("Already signed in with read-only Gmail access. No mail was downloaded.")
    else:
        print("Signed in. Read-only token saved locally. No mail was downloaded.")


if __name__ == "__main__":
    main()
