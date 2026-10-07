"""Gmail mailbox download is not enabled.

Sign in on this computer with ``python3 src/gmail/login.py``. That stores a
read-only token and does not download mail.
"""


class GmailNotConnectedError(RuntimeError):
    """Raised if mailbox access is attempted."""


def fetch_messages(*_args: object, **_kwargs: object) -> None:
    raise GmailNotConnectedError(
        "Gmail is not connected. The Finance MCP reads the local ledger only."
    )
