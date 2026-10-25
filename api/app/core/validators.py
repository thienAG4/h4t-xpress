"""Field rules shared by several schemas (phone numbers, passwords, codes)."""

import re

PHONE_PATTERN = re.compile(r"^0\d{9}$")
PASSWORD_MIN_LENGTH = 8


def normalize_phone(value: str) -> str:
    """Accept '0xxxxxxxxx', '+84xxxxxxxxx' or '84xxxxxxxxx' and store '0xxxxxxxxx'."""
    digits = re.sub(r"[\s.\-()]", "", value)
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if not PHONE_PATTERN.match(digits):
        raise ValueError("Phone number must have 10 digits and start with 0 (or +84)")
    return digits


def validate_password(value: str) -> str:
    """Figma rule: 'Must include letter, number and a character' (min 8 characters)."""
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must have at least {PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must include a letter and a number")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must include a special character")
    return value


def normalize_identifier(value: str) -> str:
    """Login identifier: e-mail (lower-cased) or phone number (normalised)."""
    value = value.strip()
    if "@" in value:
        return value.lower()
    try:
        return normalize_phone(value)
    except ValueError:
        return value
