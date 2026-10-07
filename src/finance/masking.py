"""Mask identifiers that look like account or card numbers."""

import re

_SENSITIVE_PARTS = ("password", "pin", "cvv", "otp", "secret", "token", "credential")
_ACCOUNT_KEYS = {"account_number", "card_number", "pan"}


def looks_like_account_number(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    compact = re.sub(r"\s+", "", value)
    if len(digits) < 8 or not compact:
        return False
    return len(digits) / len(compact) >= 0.7


def mask_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = " ".join(value.split())
    if not stripped:
        return None
    if not looks_like_account_number(stripped):
        return stripped
    digits = re.sub(r"\D", "", stripped)
    return f"XXXX{digits[-4:]}"


def scrub(value: object) -> object:
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _SENSITIVE_PARTS):
                continue
            if lowered in _ACCOUNT_KEYS:
                if "masked_identifier" not in cleaned:
                    cleaned["masked_identifier"] = mask_identifier(None if item is None else str(item))
                continue
            cleaned[str(key)] = scrub(item)
        return cleaned
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value
