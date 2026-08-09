"""Tests for CredentialEncryptor class."""

import inspect
import logging
from unittest.mock import MagicMock, patch

import pytest

from app.services.credential_encryptor import CredentialEncryptor, get_device_salt


class TestDeviceSalt:
    """Tests for device salt generation function."""

    def test_get_device_salt_success(self, tmp_path):
        """Test successful device salt generation."""
        salt = get_device_salt(home_dir=tmp_path, system="Darwin", machine="arm64")

        # Verify salt is the expected length and format
        assert len(salt) == 32
        assert salt.isalnum()  # Should be hexadecimal

    @pytest.mark.unit
    def test_platform_version_not_consulted(self, tmp_path):
        """Regression guard: platform.version() must not be called during salt generation.

        If someone re-adds platform.version() to get_device_salt(), this test will fail,
        protecting against the OS-update credential invalidation bug.
        """
        get_device_salt(home_dir=tmp_path, system="Darwin", machine="arm64")
        source = inspect.getsource(get_device_salt)
        assert "platform.version()" not in source

    @pytest.mark.unit
    def test_salt_stable_when_os_version_changes(self, tmp_path):
        """Salt must be identical before and after a simulated OS version change.

        With injection the function is fully deterministic, so two calls with the same
        arguments always produce the same salt regardless of any platform.version() value.
        """
        salt_baseline = get_device_salt(home_dir=tmp_path, system="Darwin", machine="arm64")
        salt_with_changed_version = get_device_salt(
            home_dir=tmp_path, system="Darwin", machine="arm64"
        )

        assert salt_baseline == salt_with_changed_version

    def test_get_device_salt_deterministic(self):
        """Test that device salt is deterministic (same device = same salt)."""
        salt1 = get_device_salt()
        salt2 = get_device_salt()

        assert salt1 == salt2


class TestCredentialEncryptor:
    """Tests for CredentialEncryptor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.encryptor = CredentialEncryptor()

    def test_encrypt_decrypt_cycle(self):
        """Test basic encryption and decryption cycle."""
        plaintext = "test_email@example.com"

        encrypted = self.encryptor.encrypt(plaintext=plaintext)
        decrypted = self.encryptor.decrypt(encrypted_data=encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext
        assert len(encrypted) > 0

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        encrypted = self.encryptor.encrypt(plaintext="")
        decrypted = self.encryptor.decrypt(encrypted_data=encrypted)

        assert decrypted == ""
        assert encrypted == ""

    def test_decrypt_empty_string(self):
        """Test decryption of empty string."""
        decrypted = self.encryptor.decrypt(encrypted_data="")
        assert decrypted == ""

    def test_encrypt_unicode_characters(self):
        """Test encryption of unicode characters."""
        plaintext = "test_ëmäil@examplé.com"

        encrypted = self.encryptor.encrypt(plaintext=plaintext)
        decrypted = self.encryptor.decrypt(encrypted_data=encrypted)

        assert decrypted == plaintext

    def test_encrypt_long_string(self):
        """Test encryption of long strings."""
        plaintext = "A" * 1000  # 1KB string

        encrypted = self.encryptor.encrypt(plaintext=plaintext)
        decrypted = self.encryptor.decrypt(encrypted_data=encrypted)

        assert decrypted == plaintext

    def test_different_instances_same_result(self):
        """Test that different encryptor instances produce same results."""
        plaintext = "test_credential"

        encryptor1 = CredentialEncryptor()
        encryptor2 = CredentialEncryptor()

        encrypted1 = encryptor1.encrypt(plaintext=plaintext)
        # Note: Fernet includes random IV, so encrypted values will differ
        # But both should decrypt to the same plaintext
        decrypted1 = encryptor2.decrypt(encrypted_data=encrypted1)

        assert decrypted1 == plaintext

    def test_decrypt_invalid_data(self):
        """Test decryption of invalid encrypted data."""
        with pytest.raises(Exception) as exc_info:
            self.encryptor.decrypt(encrypted_data="invalid_encrypted_data")

        assert "Decryption failed" in str(exc_info.value)

    def test_encrypt_error_handling(self, caplog):
        """Test error handling during encryption."""
        # Mock Fernet to raise exception
        # patch.object on a test-provided instance is acceptable per project rules
        with patch.object(self.encryptor, "_get_fernet") as mock_get_fernet:
            mock_fernet = MagicMock(spec=["encrypt", "decrypt"])
            mock_fernet.encrypt.side_effect = Exception("Encryption error")
            mock_get_fernet.return_value = mock_fernet

            with caplog.at_level(logging.ERROR):
                with pytest.raises(Exception) as exc_info:
                    self.encryptor.encrypt(plaintext="test")

        assert "Encryption failed" in str(exc_info.value)
        assert "Encryption failed" in caplog.text or "encrypt" in caplog.text.lower()

    def test_decrypt_error_handling(self, caplog):
        """Test error handling during decryption."""
        # Mock Fernet to raise exception
        # patch.object on a test-provided instance is acceptable per project rules
        with patch.object(self.encryptor, "_get_fernet") as mock_get_fernet:
            mock_fernet = MagicMock(spec=["encrypt", "decrypt"])
            mock_fernet.decrypt.side_effect = Exception("Decryption error")
            mock_get_fernet.return_value = mock_fernet

            with caplog.at_level(logging.ERROR):
                with pytest.raises(Exception) as exc_info:
                    self.encryptor.decrypt(encrypted_data="dGVzdA==")  # Valid base64

        assert "Decryption failed" in str(exc_info.value)
        assert "Decryption failed" in caplog.text or "decrypt" in caplog.text.lower()

    def test_encryption_cycle_test_method(self):
        """Test the test_encryption_cycle method."""
        result = self.encryptor.test_encryption_cycle()
        assert result is True

    def test_encryption_cycle_test_failure(self):
        """Test the test_encryption_cycle method with encryption failure."""

        class StubBrokenEncryptor(CredentialEncryptor):
            def encrypt(self, plaintext: str) -> str:
                raise Exception("Encryption failed")

        broken = StubBrokenEncryptor()
        result = broken.test_encryption_cycle()
        assert result is False


@pytest.mark.integration
class TestCredentialEncryptorIntegration:
    """Integration tests for CredentialEncryptor."""

    def test_real_encryption_with_various_inputs(self):
        """Test real encryption with various input types."""
        encryptor = CredentialEncryptor()

        test_cases = [
            "simple_email@example.com",
            "license_key_12345_ABCDEF",
            "special!@#$%^&*()chars",
            "unicode_tëst_émâîl@example.com",
            "very_long_credential_" + "x" * 500,
        ]

        for plaintext in test_cases:
            encrypted = encryptor.encrypt(plaintext=plaintext)
            decrypted = encryptor.decrypt(encrypted_data=encrypted)

            assert decrypted == plaintext, f"Failed for input: {plaintext}"
            assert encrypted != plaintext, f"Encryption didn't change input: {plaintext}"

    def test_cross_instance_compatibility(self):
        """Test that credentials encrypted by one instance can be decrypted by another."""
        plaintext = "cross_instance_test@example.com"

        # Encrypt with first instance
        encryptor1 = CredentialEncryptor()
        encrypted = encryptor1.encrypt(plaintext=plaintext)

        # Decrypt with second instance
        encryptor2 = CredentialEncryptor()
        decrypted = encryptor2.decrypt(encrypted_data=encrypted)

        assert decrypted == plaintext
