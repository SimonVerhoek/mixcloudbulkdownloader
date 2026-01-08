"""Credential encryption for secure INI file storage."""

import base64
import hashlib
import os
import platform
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.qt_logger import log_error


def get_device_salt() -> str:
    """Generate stable, device-specific salt for encryption.

    Returns:
        str: A 32-character hexadecimal salt unique to this device and user.
    """
    # Use stable platform identifiers
    stable_identifiers = [
        platform.system(),  # 'Windows', 'Darwin', 'Linux'
        platform.machine(),  # 'x86_64', 'arm64', etc.
        platform.version(),  # OS version (more stable than hostname)
    ]

    # Add user-specific component (stable per user)
    try:
        # Use home directory path as user identifier
        home_path = str(Path.home())
        stable_identifiers.append(home_path)
    except Exception:
        # Fallback if home directory unavailable
        user_fallback = os.getenv("USER") or os.getenv("USERNAME") or "default"
        stable_identifiers.append(user_fallback)

    # Create deterministic hash
    combined = "|".join(stable_identifiers)
    salt = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:32]

    return salt


class CredentialEncryptor:
    """Handles encryption and decryption of credentials using device-specific salts.

    Uses Fernet (AES-128 in CBC mode) with PBKDF2 key derivation for secure
    encryption of sensitive credentials before storage in INI files.
    """

    def __init__(self) -> None:
        """Initialize the encryptor with device-specific salt."""
        self._salt = get_device_salt()
        self._fernet = None

    def _get_fernet(self) -> Fernet:
        """Get or create Fernet instance with derived key.

        Returns:
            Fernet: Initialized Fernet instance for encryption/decryption.
        """
        if self._fernet is None:
            # Derive key using PBKDF2 with device salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 32 bytes for Fernet key
                salt=self._salt.encode("utf-8"),
                iterations=100000,  # Standard security recommendation
            )
            # Use a fixed password component combined with salt for deterministic key
            key = base64.urlsafe_b64encode(kdf.derive(b"mixcloud_bulk_downloader"))
            self._fernet = Fernet(key)

        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt.

        Returns:
            str: Base64-encoded encrypted data.

        Raises:
            Exception: If encryption fails.
        """
        if not plaintext:
            return ""

        try:
            fernet = self._get_fernet()
            encrypted_data = fernet.encrypt(plaintext.encode("utf-8"))
            return base64.urlsafe_b64encode(encrypted_data).decode("utf-8")
        except Exception as e:
            log_error(message=f"Failed to encrypt credential: {e}")
            raise Exception(f"Encryption failed: {e}") from e

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt an encrypted string.

        Args:
            encrypted_data: Base64-encoded encrypted data.

        Returns:
            str: Decrypted plaintext string.

        Raises:
            Exception: If decryption fails.
        """
        if not encrypted_data:
            return ""

        try:
            fernet = self._get_fernet()
            # Decode from base64 and decrypt
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode("utf-8"))
            decrypted_data = fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode("utf-8")
        except Exception as e:
            log_error(message=f"Failed to decrypt credential: {e}")
            raise Exception(f"Decryption failed: {e}") from e

    def test_encryption_cycle(self) -> bool:
        """Test encryption/decryption cycle to verify functionality.

        Returns:
            bool: True if encryption cycle works correctly, False otherwise.
        """
        test_data = "test_credential_data_12345"

        try:
            encrypted = self.encrypt(plaintext=test_data)
            decrypted = self.decrypt(encrypted_data=encrypted)
            return decrypted == test_data
        except Exception:
            return False
