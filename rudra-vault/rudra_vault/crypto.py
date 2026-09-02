"""Cryptographic operations for Rudra Secret Safe."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

VAULT_DIR = Path.home() / ".rudra" / "vault"
SALT_FILE = VAULT_DIR / "salt.bin"
AUTH_CHECK_FILE = VAULT_DIR / "auth_check.bin"
SESSION_FILE = VAULT_DIR / ".session"
SESSION_TIMEOUT_SECS = 3600  # 1 hour auto-lock

AUTH_TOKEN_MAGIC = b"RUDRA_SAFE_VALIDATED_V1"


def ensure_vault_dir() -> Path:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(VAULT_DIR, 0o700)
    blobs_dir = VAULT_DIR / "blobs"
    blobs_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(blobs_dir, 0o700)
    return VAULT_DIR


def get_or_create_salt() -> bytes:
    ensure_vault_dir()
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    os.chmod(SALT_FILE, 0o600)
    return salt


def derive_key(password: str, salt: Optional[bytes] = None) -> bytes:
    if salt is None:
        salt = get_or_create_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    """Encrypt using AES-256-GCM. Returns 12-byte IV + ciphertext + 16-byte tag."""
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, data, None)
    return iv + ciphertext


def decrypt_bytes(payload: bytes, key: bytes) -> bytes:
    """Decrypt using AES-256-GCM from 12-byte IV + ciphertext + 16-byte tag."""
    if len(payload) < 28:
        raise ValueError("Encrypted payload is corrupted or too short")
    iv = payload[:12]
    ciphertext = payload[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ciphertext, None)


def init_credentials(password: str) -> bytes:
    """Initialize master password and write salt and auth check token."""
    ensure_vault_dir()
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    os.chmod(SALT_FILE, 0o600)
    key = derive_key(password, salt)
    encrypted_auth = encrypt_bytes(AUTH_TOKEN_MAGIC, key)
    AUTH_CHECK_FILE.write_bytes(encrypted_auth)
    os.chmod(AUTH_CHECK_FILE, 0o600)
    cache_session_key(key)
    return key


def verify_password(password: str) -> Optional[bytes]:
    """Verify master password against auth_check.bin. Returns derived key on success."""
    if not AUTH_CHECK_FILE.exists() or not SALT_FILE.exists():
        return None
    salt = SALT_FILE.read_bytes()
    key = derive_key(password, salt)
    try:
        decrypted = decrypt_bytes(AUTH_CHECK_FILE.read_bytes(), key)
        if decrypted == AUTH_TOKEN_MAGIC:
            cache_session_key(key)
            return key
    except Exception:
        pass
    return None


def cache_session_key(key: bytes) -> None:
    """Store session key with expiry timestamp."""
    ensure_vault_dir()
    expiry = int(time.time()) + SESSION_TIMEOUT_SECS
    payload = f"{expiry}:{key.hex()}".encode("utf-8")
    SESSION_FILE.write_bytes(payload)
    os.chmod(SESSION_FILE, 0o600)


def get_cached_session_key() -> Optional[bytes]:
    """Retrieve unexpired session key if available."""
    if not SESSION_FILE.exists():
        return None
    try:
        content = SESSION_FILE.read_bytes().decode("utf-8")
        expiry_str, key_hex = content.split(":", 1)
        if int(expiry_str) > time.time():
            return bytes.fromhex(key_hex)
        else:
            clear_session_key()
    except Exception:
        clear_session_key()
    return None


def clear_session_key() -> None:
    """Lock the vault by deleting the session key."""
    if SESSION_FILE.exists():
        try:
            SESSION_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def is_initialized() -> bool:
    return AUTH_CHECK_FILE.exists() and SALT_FILE.exists()


def is_unlocked() -> bool:
    return get_cached_session_key() is not None
