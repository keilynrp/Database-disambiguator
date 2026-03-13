"""
Symmetric encryption for sensitive credentials stored in the database.
Uses Fernet (AES-128-CBC + HMAC-SHA256).

Generate a key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Set the result as ENCRYPTION_KEY env var. Without it, values are stored in plaintext
(acceptable for local dev, NOT for production).
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_fernet = None

_raw_key = os.environ.get("ENCRYPTION_KEY")
if _raw_key:
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(_raw_key.encode())
    except Exception:
        logger.warning(
            "ENCRYPTION_KEY is set but invalid (must be URL-safe base64 32-byte key). "
            "Credentials will be stored in PLAINTEXT. Generate with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
else:
    logger.warning(
        "ENCRYPTION_KEY not set — credentials stored in plaintext. "
        "Set ENCRYPTION_KEY in production."
    )


def encrypt(value: Optional[str]) -> Optional[str]:
    """Encrypt a plaintext string. No-op if no key is configured."""
    if not _fernet or not value:
        return value
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: Optional[str]) -> Optional[str]:
    """
    Decrypt a Fernet-encrypted string.
    Falls back to returning the value as-is to handle legacy plaintext during migration.
    """
    if not _fernet or not value:
        return value
    try:
        from cryptography.fernet import InvalidToken
        return _fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        logger.warning(
            "decrypt(): InvalidToken — value appears to be plaintext (legacy migration). "
            "Re-save this record to encrypt it."
        )
        return value
    except Exception as e:
        logger.error("decrypt(): unexpected error: %s — returning value as-is", e)
        return value
