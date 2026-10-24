import hashlib

from pwdlib import PasswordHash

# Argon2id with pwdlib's recommended parameters (NFR-02).
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def hash_token(token: str) -> str:
    """One-way hash for API keys and refresh tokens that are compared, never displayed."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
