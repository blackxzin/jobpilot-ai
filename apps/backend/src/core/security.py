"""
JobPilot AI — Security Utilities

Encryption, hashing, and API key management.
"""

from __future__ import annotations

from cryptography.fernet import Fernet

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
