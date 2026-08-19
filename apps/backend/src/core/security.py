"""
JobPilot AI — Security Utilities

Encryption, password hashing, and API key management.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet

# ── Password hashing ────────────────────────────────────────────────────────
# PBKDF2-HMAC-SHA256. The legacy format was a bare, unsalted SHA-256 digest;
# `verify_password` still accepts it so existing accounts keep working, and
# `needs_rehash` tells callers to upgrade the stored hash on next login.
PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
LEGACY_SHA256_LENGTH = 64

# Encrypts LLM API keys at rest in the database
_ENCRYPTION_KEY: bytes | None = None
_fernet: Fernet | None = None


def get_encryption_key() -> bytes:
    """Return the encryption key from settings or generate one."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        import base64

        from core.config import settings
        # Derive a Fernet-compatible key from the app secret
        digest = __import__("hashlib").sha256(settings.SECRET_KEY.encode()).digest()
        _ENCRYPTION_KEY = base64.urlsafe_b64encode(digest)
    return _ENCRYPTION_KEY


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_encryption_key())
    return _fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key for use."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_encryption_key())
    return _fernet.decrypt(encrypted_key.encode()).decode()


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Hash a password with a random salt.

    Returns a self-describing string: ``pbkdf2_sha256$<iterations>$<salt>$<hash>``.
    """
    salt = secrets.token_hex(SALT_BYTES)
    digest = _pbkdf2(password, salt, iterations)
    return f"{PBKDF2_ALGORITHM}${iterations}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a password against a stored hash, in constant time.

    Accepts both the current PBKDF2 format and the legacy unsalted SHA-256
    digest so pre-existing accounts can still log in.
    """
    if not stored_hash:
        return False

    if stored_hash.startswith(f"{PBKDF2_ALGORITHM}$"):
        try:
            _, iterations, salt, digest = stored_hash.split("$", 3)
            candidate = _pbkdf2(password, salt, int(iterations))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(candidate, digest)

    if len(stored_hash) == LEGACY_SHA256_LENGTH:
        legacy = hashlib.sha256(password.encode()).hexdigest()
        return hmac.compare_digest(legacy, stored_hash)

    return False


def needs_rehash(stored_hash: str) -> bool:
    """Return True when a stored hash uses an outdated format or cost."""
    if not stored_hash.startswith(f"{PBKDF2_ALGORITHM}$"):
        return True
    try:
        iterations = int(stored_hash.split("$", 2)[1])
    except (IndexError, ValueError):
        return True
    return iterations < PBKDF2_ITERATIONS


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    ).hex()


def generate_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(48)
