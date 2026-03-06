"""
Tests for backend/encryption.py — Fernet encrypt/decrypt, None handling,
and plaintext fallback for migration compatibility.
"""
import os
import importlib
import pytest
from cryptography.fernet import Fernet


def _reload_encryption(key: str | None):
    """Helper: reload the encryption module with a specific key env var."""
    if key is None:
        os.environ.pop("ENCRYPTION_KEY", None)
    else:
        os.environ["ENCRYPTION_KEY"] = key

    import backend.encryption as enc
    importlib.reload(enc)
    return enc


# ── Without encryption key (dev passthrough) ────────────────────────────────

def test_no_key_encrypt_returns_plaintext():
    enc = _reload_encryption(None)
    assert enc.encrypt("my-secret") == "my-secret"


def test_no_key_decrypt_returns_plaintext():
    enc = _reload_encryption(None)
    assert enc.decrypt("my-secret") == "my-secret"


def test_no_key_encrypt_none_returns_none():
    enc = _reload_encryption(None)
    assert enc.encrypt(None) is None


def test_no_key_decrypt_none_returns_none():
    enc = _reload_encryption(None)
    assert enc.decrypt(None) is None


# ── With a valid Fernet key ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def enc_with_key():
    key = Fernet.generate_key().decode()
    enc = _reload_encryption(key)
    yield enc
    # Restore: no key after tests
    _reload_encryption(None)


def test_encrypt_produces_different_value(enc_with_key):
    plaintext = "sk-supersecret-api-key"
    encrypted = enc_with_key.encrypt(plaintext)
    assert encrypted != plaintext


def test_roundtrip_encrypt_decrypt(enc_with_key):
    plaintext = "sk-supersecret-api-key"
    encrypted = enc_with_key.encrypt(plaintext)
    decrypted = enc_with_key.decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_none_returns_none_with_key(enc_with_key):
    assert enc_with_key.encrypt(None) is None


def test_decrypt_none_returns_none_with_key(enc_with_key):
    assert enc_with_key.decrypt(None) is None


def test_decrypt_empty_string_returns_empty_with_key(enc_with_key):
    assert enc_with_key.encrypt("") == ""


# ── Plaintext fallback for migration ─────────────────────────────────────────

def test_decrypt_plaintext_falls_back_gracefully(enc_with_key):
    """
    If a value was stored in plaintext (legacy record before encryption was added),
    decrypt() must return it as-is rather than raising an exception.
    """
    legacy_plaintext = "old-unencrypted-api-key"
    result = enc_with_key.decrypt(legacy_plaintext)
    assert result == legacy_plaintext


# ── Invalid key warning (no crash) ───────────────────────────────────────────

def test_invalid_key_does_not_crash():
    enc = _reload_encryption("this-is-not-a-valid-fernet-key")
    # Should fall back to passthrough
    assert enc.encrypt("hello") == "hello"
    assert enc.decrypt("hello") == "hello"
