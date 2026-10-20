import re


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def phone_key(value: str | None) -> str | None:
    """Last 9 digits, so +251911234567, 0911234567 and 911234567 all match."""
    d = digits(value)
    return d[-9:] if len(d) >= 7 else None
