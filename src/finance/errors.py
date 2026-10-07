"""Errors that are safe to return to the Finance MCP caller."""


class FinanceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, object]:
        return {"ok": False, "error": {"code": self.code, "message": self.message}}
