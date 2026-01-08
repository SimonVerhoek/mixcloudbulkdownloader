"""Tests for CredentialEncryptor class."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.credential_encryptor import CredentialEncryptor, get_device_salt


class TestDeviceSalt:
    """Tests for device salt generation function."""

    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.version")
    @patch("app.services.credential_encryptor.Path")
    def test_get_device_salt_success(self, mock_path, mock_version, mock_machine, mock_system):
        """Test successful device salt generation."""
        # Mock platform information
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"
        mock_version.return_value = "23.1.0"

        # Mock Path.home()
        mock_home = MagicMock()
        mock_home.__str__ = MagicMock(return_value="/Users/testuser")
        mock_path.home.return_value = mock_home

        salt = get_device_salt()

        # Verify salt is the expected length and format
        assert len(salt) == 32
        assert salt.isalnum()  # Should be hexadecimal

    def test_get_device_salt_deterministic(self):
        """Test that device salt is deterministic (same device = same salt)."""
        salt1 = get_device_salt()
        salt2 = get_device_salt()

        assert salt1 == salt2

    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.version")
    @patch("app.services.credential_encryptor.Path")
    @patch("os.getenv")
    def test_get_device_salt_home_fallback(
        self, mock_getenv, mock_path, mock_version, mock_machine, mock_system
    ):
        """Test device salt generation with home directory fallback."""
        # Mock platform information
        mock_system.return_value = "Windows"
        mock_machine.return_value = "x86_64"
        mock_version.return_value = "10.0.19041"

        # Mock Path.home() failing
        mock_path.home.side_effect = Exception("Home directory not accessible")

        # Mock environment variable fallback
        mock_getenv.side_effect = lambda var, default=None: {
            "USER": None,
            "USERNAME": "testuser",
        }.get(var, default)

        salt = get_device_salt()

        # Verify salt is still generated successfully
        assert len(salt) == 32
        assert salt.isalnum()


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

    @patch("app.services.credential_encryptor.log_error")
    def test_encrypt_error_handling(self, mock_log_error):
        """Test error handling during encryption."""
        # Mock Fernet to raise exception
        with patch.object(self.encryptor, "_get_fernet") as mock_get_fernet:
            mock_fernet = MagicMock()
            mock_fernet.encrypt.side_effect = Exception("Encryption error")
            mock_get_fernet.return_value = mock_fernet

            with pytest.raises(Exception) as exc_info:
                self.encryptor.encrypt(plaintext="test")

            assert "Encryption failed" in str(exc_info.value)
            mock_log_error.assert_called_once()

    @patch("app.services.credential_encryptor.log_error")
    def test_decrypt_error_handling(self, mock_log_error):
        """Test error handling during decryption."""
        # Mock Fernet to raise exception
        with patch.object(self.encryptor, "_get_fernet") as mock_get_fernet:
            mock_fernet = MagicMock()
            mock_fernet.decrypt.side_effect = Exception("Decryption error")
            mock_get_fernet.return_value = mock_fernet

            with pytest.raises(Exception) as exc_info:
                self.encryptor.decrypt(encrypted_data="dGVzdA==")  # Valid base64

            assert "Decryption failed" in str(exc_info.value)
            mock_log_error.assert_called_once()

    def test_encryption_cycle_test_method(self):
        """Test the test_encryption_cycle method."""
        result = self.encryptor.test_encryption_cycle()
        assert result is True

    @patch.object(CredentialEncryptor, "encrypt")
    def test_encryption_cycle_test_failure(self, mock_encrypt):
        """Test the test_encryption_cycle method with encryption failure."""
        mock_encrypt.side_effect = Exception("Encryption failed")

        result = self.encryptor.test_encryption_cycle()
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
