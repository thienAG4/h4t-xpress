"""Password hashing, JWT access tokens, refresh tokens and OTP codes (SPEC §5.2)."""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

# Argon2id with pwdlib's recommended parameters (NFR-02).
_password_hash = PasswordHash.recommended()


# =============================== Passwords ===============================


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def generate_temporary_password() -> str:
    """Readable temporary password that still meets the password policy."""
    return f"H4t-{secrets.token_urlsafe(6)}{secrets.randbelow(90) + 10}"


# =============================== Opaque tokens ===============================


def hash_token(token: str) -> str:
    """One-way hash for API keys, refresh tokens and OTP codes (compared, never shown)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def sign_webhook(body: bytes, secret: str) -> str:
    """HMAC-SHA256 signature sent in the X-H4T-Signature header of partner webhooks."""
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


# =============================== Access tokens (JWT) ===============================


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    role: str
    hub_id: uuid.UUID | None
    permissions: frozenset[str]


def create_access_token(
    *, user_id: uuid.UUID, role: str, hub_id: uuid.UUID | None, permissions: list[str]
) -> tuple[str, int]:
    """Return (token, lifetime in seconds). Permissions are embedded to avoid a DB hit."""
    settings = get_settings()
    lifetime = timedelta(minutes=settings.access_token_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "hub": str(hub_id) if hub_id else None,
        "perms": sorted(permissions),
        "iat": now,
        "exp": now + lifetime,
        "typ": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> AccessClaims | None:
    """Return the claims, or None when the token is invalid or expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    hub = payload.get("hub")
    return AccessClaims(
        user_id=uuid.UUID(payload["sub"]),
        role=payload["role"],
        hub_id=uuid.UUID(hub) if hub else None,
        permissions=frozenset(payload.get("perms", [])),
    )
