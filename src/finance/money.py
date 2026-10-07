"""Minor-unit money helpers. Amounts are not stored as binary floats."""

from decimal import Decimal, ROUND_HALF_UP

from finance.errors import FinanceError

_CENT = Decimal("0.01")
_RATE = Decimal("0.0001")


def parse_amount(value: object, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or value is None:
        raise FinanceError("invalid_amount", "amount is required")
    if isinstance(value, float):
        text = format(value, "f")
    else:
        text = str(value).strip().replace(",", "")
    if not text:
        raise FinanceError("invalid_amount", "amount is required")
    try:
        amount = Decimal(text)
    except Exception as exc:
        raise FinanceError("invalid_amount", "amount must be a number") from exc
    quantized = amount.quantize(_CENT, rounding=ROUND_HALF_UP)
    if quantized != amount:
        raise FinanceError("invalid_amount", "amount must have at most 2 decimal places")
    if quantized < 0 or (quantized == 0 and not allow_zero):
        raise FinanceError("invalid_amount", "amount must be greater than zero")
    return int(quantized * 100)


def format_amount(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    minor = abs(minor)
    return f"{sign}{minor // 100}.{minor % 100:02d}"


def parse_confidence(value: object, default_bps: int) -> int:
    if value is None:
        return default_bps
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise FinanceError("invalid_confidence", "confidence must be between 0 and 1") from exc
    if parsed < 0 or parsed > 1:
        raise FinanceError("invalid_confidence", "confidence must be between 0 and 1")
    return int((parsed * 10000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_confidence(bps: int) -> str:
    return format((Decimal(bps) / Decimal(10000)).quantize(_RATE), "f")


def format_rate(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    rate = (Decimal(numerator) / Decimal(denominator)).quantize(_RATE, rounding=ROUND_HALF_UP)
    return format(rate, "f")
