"""Gmail is not connected.

Do not read or search a mailbox from this package. A transaction may still
record source='gmail' when some other importer has already extracted fields.
"""


class GmailNotConnectedError(RuntimeError):
    """Raised if mailbox access is attempted."""


def fetch_messages(*_args: object, **_kwargs: object) -> None:
    raise GmailNotConnectedError(
        "Gmail is not connected. The Finance MCP reads the local ledger only."
    )
