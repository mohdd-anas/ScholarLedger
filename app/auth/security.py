"""Password hashing, API key generation, and CSRF utilities."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its Argon2id hash."""
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns (plaintext_key, key_prefix, sha256_hex_hash).
    """
    raw = secrets.token_urlsafe(32)
    plaintext = f"pb1_{raw}"
    prefix = plaintext[:12]
    key_hash = hash_api_key(plaintext)
    return plaintext, prefix, key_hash


def hash_api_key(plaintext_key: str) -> str:
    """Return the SHA-256 hex digest of an API key."""
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()

