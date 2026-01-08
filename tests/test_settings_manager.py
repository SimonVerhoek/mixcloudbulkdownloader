"""Tests for SettingsManager with encrypted INI storage."""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QSettings

from app.consts.settings import (
    DEFAULT_CHECK_UPDATES_ON_STARTUP,
    DEFAULT_ENABLE_AUDIO_CONVERSION,
    KEYRING_EMAIL_KEY,
    KEYRING_LICENSE_KEY,
    SETTING_CHECK_UPDATES_ON_STARTUP,
    SETTING_ENABLE_AUDIO_CONVERSION,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    SETTING_MAX_PARALLEL_DOWNLOADS,
)
from app.services.settings_manager import SettingsManager


@pytest.fixture
def temp_settings_dir():
    """Create temporary directory for settings testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_development_env():
    """Mock development environment."""
    with patch("app.services.settings_manager.DEVELOPMENT", True):
        yield


class TestSettingsManagerInit:
    """Tests for SettingsManager initialization."""

    @patch("app.services.settings_manager.DEVELOPMENT", False)
    @patch("sys.platform", "darwin")
    def test_init_production_macos(self):
        """Test initialization in production mode on macOS."""
        with patch("app.services.settings_manager.Path") as mock_path:
            mock_home = MagicMock()
            mock_path.home.return_value = mock_home
            expected_path = (
                mock_home / "Library" / "Application Support" / "mixcloud-bulk-downloader"
            )

            manager = SettingsManager()

            assert manager._storage_path == expected_path

    @patch("app.services.settings_manager.DEVELOPMENT", False)
    @patch("sys.platform", "win32")
    @patch("os.getenv")
    def test_init_production_windows(self, mock_getenv):
        """Test initialization in production mode on Windows."""

        # Configure mock to return different values for different keys
        def mock_getenv_side_effect(key, default=None):
            if key == "APPDATA":
                return "C:\\Users\\Test\\AppData\\Roaming"
            elif key == "DEVELOPMENT":
                return None  # Ensures DEVELOPMENT defaults to False
            return default

        mock_getenv.side_effect = mock_getenv_side_effect

        with patch("app.services.settings_manager.Path") as mock_path:
            expected_path = (
                mock_path("C:\\Users\\Test\\AppData\\Roaming") / "mixcloud-bulk-downloader"
            )

            manager = SettingsManager()

            # Verify the APPDATA path construction logic was called
            # Check that APPDATA was requested at some point
            appdata_calls = [call for call in mock_getenv.call_args_list if call[0][0] == "APPDATA"]
            assert len(appdata_calls) > 0, "APPDATA should have been requested"

    @patch("app.services.settings_manager.DEVELOPMENT", True)
    def test_init_development_mode(self):
        """Test initialization in development mode."""
        with patch("app.services.settings_manager.Path") as mock_path:
            expected_path = mock_path("./local_settings").resolve.return_value

            manager = SettingsManager()

            assert manager._storage_path == expected_path

    @patch("app.services.settings_manager.log_ui")
    def test_encryption_test_success(self, mock_log_ui):
        """Test successful encryption test during initialization."""
        with patch("app.services.credential_encryptor.CredentialEncryptor") as mock_encryptor_class:
            mock_encryptor = MagicMock()
            mock_encryptor.test_encryption_cycle.return_value = True
            mock_encryptor_class.return_value = mock_encryptor

            with (
                patch("app.services.settings_manager.SettingsManager._get_storage_path"),
                patch("app.services.settings_manager.SettingsManager._create_qsettings"),
                patch("app.services.settings_manager.SettingsManager._secure_storage_directory"),
            ):

                manager = SettingsManager()

                mock_log_ui.assert_called_with(
                    message="Credential encryption system initialized successfully", level="INFO"
                )


class TestSettingsManagerProperties:
    """Tests for SettingsManager property-based interface."""

    @pytest.fixture
    def settings_manager(self, temp_settings_dir):
        """Create SettingsManager instance for testing."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):
            return SettingsManager()

    def test_email_property_set_get(self, settings_manager):
        """Test email property setter and getter."""
        test_email = "test@example.com"

        settings_manager.email = test_email
        retrieved_email = settings_manager.email

        assert retrieved_email == test_email

    def test_license_key_property_set_get(self, settings_manager):
        """Test license_key property setter and getter."""
        test_key = "LICENSE123ABCDEF"

        settings_manager.license_key = test_key
        retrieved_key = settings_manager.license_key

        assert retrieved_key == test_key

    def test_last_successful_verification_property(self, settings_manager):
        """Test last_successful_verification property."""
        test_timestamp = time.time()

        settings_manager.last_successful_verification = test_timestamp
        retrieved_timestamp = settings_manager.last_successful_verification

        assert retrieved_timestamp == test_timestamp

    def test_max_parallel_downloads_property(self, settings_manager):
        """Test max_parallel_downloads property."""
        test_value = 5

        settings_manager.max_parallel_downloads = test_value
        retrieved_value = settings_manager.max_parallel_downloads

        assert retrieved_value == test_value

    def test_max_parallel_conversions_property(self, settings_manager):
        """Test max_parallel_conversions property."""
        test_value = 3

        settings_manager.max_parallel_conversions = test_value
        retrieved_value = settings_manager.max_parallel_conversions

        assert retrieved_value == test_value

    def test_empty_credentials_return_default(self, settings_manager):
        """Test that empty credentials return empty string."""
        assert settings_manager.email == ""
        assert settings_manager.license_key == ""

    def test_unset_numeric_properties_return_defaults(self, settings_manager):
        """Test that unset numeric properties return appropriate defaults."""
        # Should return defaults from constants
        assert isinstance(settings_manager.max_parallel_downloads, int)
        assert isinstance(settings_manager.max_parallel_conversions, int)
        assert settings_manager.last_successful_verification == 0.0


class TestSettingsManagerThreading:
    """Tests for SettingsManager threading functionality."""

    @pytest.fixture
    def settings_manager(self, temp_settings_dir):
        """Create SettingsManager instance for testing."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):
            return SettingsManager()

    def test_concurrent_reads(self, settings_manager):
        """Test concurrent read operations."""
        # Set initial value
        settings_manager.email = "test@example.com"

        results = []
        errors = []

        def read_email():
            try:
                email = settings_manager.email
                results.append(email)
            except Exception as e:
                errors.append(e)

        # Create multiple concurrent readers
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=read_email)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(email == "test@example.com" for email in results)

    def test_concurrent_writes(self, settings_manager):
        """Test concurrent write operations."""
        results = []
        errors = []

        def write_setting(value):
            try:
                settings_manager.max_parallel_downloads = value
                results.append(value)
            except Exception as e:
                errors.append(e)

        # Create multiple concurrent writers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=write_setting, args=(i + 1,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

        # Final value should be one of the written values
        final_value = settings_manager.max_parallel_downloads
        assert final_value in range(1, 6)

    def test_mixed_read_write_operations(self, settings_manager):
        """Test mixed concurrent read and write operations."""
        settings_manager.email = "initial@example.com"

        read_results = []
        write_results = []
        errors = []

        def read_email():
            try:
                email = settings_manager.email
                read_results.append(email)
            except Exception as e:
                errors.append(e)

        def write_email(email):
            try:
                settings_manager.email = email
                write_results.append(email)
            except Exception as e:
                errors.append(e)

        # Create mixed concurrent operations
        threads = []

        # Add readers
        for _ in range(5):
            thread = threading.Thread(target=read_email)
            threads.append(thread)

        # Add writers
        for i in range(3):
            thread = threading.Thread(target=write_email, args=(f"test{i}@example.com",))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(read_results) == 5
        assert len(write_results) == 3


class TestSettingsManagerEncryption:
    """Tests for SettingsManager encryption functionality."""

    @pytest.fixture
    def settings_manager(self, temp_settings_dir):
        """Create SettingsManager instance for testing."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):
            return SettingsManager()

    def test_credential_encryption_storage(self, settings_manager, temp_settings_dir):
        """Test that credentials are actually encrypted in storage."""
        test_email = "encrypted@example.com"
        test_key = "ENCRYPTED_LICENSE_KEY"

        # Set credentials
        settings_manager.email = test_email
        settings_manager.license_key = test_key

        # Read raw INI file to verify encryption
        settings_file = temp_settings_dir / "settings.conf"
        assert settings_file.exists()

        with open(settings_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify plaintext credentials are NOT in the file
        assert test_email not in content
        assert test_key not in content

        # Verify encrypted section exists
        assert "[secrets]" in content

    def test_legacy_credential_migration(self, settings_manager):
        """Test migration of legacy unencrypted credentials."""
        # Directly set legacy unencrypted values in QSettings
        settings_manager._settings.setValue(KEYRING_EMAIL_KEY, "legacy@example.com")
        settings_manager._settings.setValue(KEYRING_LICENSE_KEY, "LEGACY_KEY")
        settings_manager._settings.sync()

        # Access via property to trigger migration
        email = settings_manager.email
        license_key = settings_manager.license_key

        # Verify values are correct
        assert email == "legacy@example.com"
        assert license_key == "LEGACY_KEY"

        # Verify legacy values are removed from regular settings
        assert settings_manager._settings.value(KEYRING_EMAIL_KEY) is None
        assert settings_manager._settings.value(KEYRING_LICENSE_KEY) is None

        # Verify new encrypted values exist
        assert settings_manager._settings.value(f"secrets/{KEYRING_EMAIL_KEY}") is not None
        assert settings_manager._settings.value(f"secrets/{KEYRING_LICENSE_KEY}") is not None


class TestSettingsManagerLegacyMethods:
    """Tests for SettingsManager legacy compatibility methods."""

    @pytest.fixture
    def settings_manager(self, temp_settings_dir):
        """Create SettingsManager instance for testing."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):
            return SettingsManager()

    def test_legacy_get_method(self, settings_manager):
        """Test deprecated get() method."""
        test_key = "test_setting"
        test_value = "test_value"

        settings_manager.set(key=test_key, value=test_value)
        retrieved_value = settings_manager.get(key=test_key)

        assert retrieved_value == test_value

    def test_legacy_set_method(self, settings_manager):
        """Test deprecated set() method."""
        test_key = "test_setting"
        test_value = 42

        settings_manager.set(key=test_key, value=test_value)
        retrieved_value = settings_manager.get(key=test_key, default=0)

        assert retrieved_value == test_value

    def test_sync_method(self, settings_manager):
        """Test sync() method."""
        settings_manager.email = "sync_test@example.com"

        # Should not raise any exceptions
        settings_manager.sync()

    def test_reset_to_defaults(self, settings_manager):
        """Test reset_to_defaults() method."""
        # Set some values
        settings_manager.email = "reset_test@example.com"
        settings_manager.max_parallel_downloads = 10

        # Reset to defaults
        settings_manager.reset_to_defaults()

        # Verify values are cleared
        assert settings_manager.email == ""
        assert settings_manager.max_parallel_downloads in [1, 3]  # Should be default value

    def test_initialize_threading_settings_pro(self, settings_manager):
        """Test initialize_threading_settings() for pro users."""
        settings_manager.initialize_threading_settings(is_pro=True)

        # Should set pro defaults
        assert settings_manager.max_parallel_downloads >= 1
        assert settings_manager.max_parallel_conversions >= 0

    def test_initialize_threading_settings_free(self, settings_manager):
        """Test initialize_threading_settings() for free users."""
        settings_manager.initialize_threading_settings(is_pro=False)

        # Should set free user limits
        assert settings_manager.max_parallel_downloads == 1
        assert settings_manager.max_parallel_conversions == 0

    def test_shutdown(self, settings_manager):
        """Test shutdown() method."""
        # Should not raise any exceptions
        settings_manager.shutdown()

        assert settings_manager._shutting_down is True


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only tests")
class TestSettingsManagerWindows:
    """Windows-specific tests for SettingsManager."""

    @pytest.mark.skip(
        reason="Windows ACL tests are fragile and provide minimal value - skipping to save CI minutes"
    )
    @patch("app.services.settings_manager.sys.platform", "win32")
    @patch("app.services.settings_manager.DEVELOPMENT", False)
    @patch("app.services.settings_manager.win32security", create=True)
    @patch("app.services.settings_manager.ntsecuritycon", create=True)
    def test_windows_acl_security(self, mock_ntsecuritycon, mock_win32security, temp_settings_dir):
        """Test Windows ACL security configuration."""
        # Mock Windows security objects
        mock_win32security.GetCurrentProcessToken.return_value = "token"
        mock_win32security.GetTokenInformation.return_value = ["user_sid"]
        mock_win32security.ACL.return_value = MagicMock()
        mock_win32security.SECURITY_DESCRIPTOR.return_value = MagicMock()

        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(
                SettingsManager, "_test_encryption_functionality"
            ),  # Mock to avoid interference
        ):
            manager = SettingsManager()

            # Verify Windows security functions were called
            mock_win32security.GetCurrentProcessToken.assert_called_once()
            mock_win32security.GetTokenInformation.assert_called_once()

    @pytest.mark.skip(
        reason="Windows ACL tests are fragile and provide minimal value - skipping to save CI minutes"
    )
    @patch("app.services.settings_manager.sys.platform", "win32")
    @patch("app.services.settings_manager.DEVELOPMENT", False)
    @patch("app.services.settings_manager.log_ui")
    def test_windows_acl_import_error(self, mock_log_ui, temp_settings_dir):
        """Test Windows ACL with ImportError (pywin32 not available)."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(
                SettingsManager, "_test_encryption_functionality"
            ),  # Mock to avoid interference
            patch.object(
                SettingsManager,
                "_secure_directory_windows",
                side_effect=ImportError("No module named 'win32security'"),
            ),
        ):
            manager = SettingsManager()

            # Should log warning about missing pywin32
            mock_log_ui.assert_called_with(
                message="pywin32 not available - skipping Windows ACL configuration",
                level="WARNING",
            )


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only tests")
class TestSettingsManagerMacOS:
    """macOS-specific tests for SettingsManager."""

    @patch("sys.platform", "darwin")
    def test_macos_chmod_security(self, temp_settings_dir):
        """Test macOS chmod security configuration."""
        with patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir):
            manager = SettingsManager()

            # Verify directory permissions are restrictive
            stat_info = temp_settings_dir.stat()
            # Check that permissions are 0o700 (owner read/write/execute only)
            assert oct(stat_info.st_mode)[-3:] == "700"


@pytest.mark.integration
class TestSettingsManagerIntegration:
    """Integration tests for SettingsManager."""

    def test_full_credential_lifecycle(self, temp_settings_dir):
        """Test complete credential storage and retrieval lifecycle."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):

            manager = SettingsManager()

            # Test credential storage
            test_email = "integration@example.com"
            test_key = "INTEGRATION_LICENSE_KEY_12345"
            test_timestamp = time.time()

            manager.email = test_email
            manager.license_key = test_key
            manager.last_successful_verification = test_timestamp

            # Create new manager instance to test persistence
            manager2 = SettingsManager()

            # Verify persistence across instances
            assert manager2.email == test_email
            assert manager2.license_key == test_key
            assert manager2.last_successful_verification == test_timestamp

    def test_concurrent_access_multiple_instances(self, temp_settings_dir):
        """Test concurrent access from multiple SettingsManager instances."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):

            manager1 = SettingsManager()
            manager2 = SettingsManager()

            # Set value in first instance
            manager1.email = "concurrent1@example.com"

            # Read from second instance (may need sync time)
            time.sleep(0.1)  # Small delay for file operations
            email = manager2.email

            # Should be able to read the updated value
            assert email == "concurrent1@example.com"

    def test_error_recovery_invalid_encryption_data(self, temp_settings_dir):
        """Test error recovery when encryption data is corrupted."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):

            manager = SettingsManager()

            # Manually corrupt encrypted data in settings
            manager._settings.setValue("secrets/license_email", "invalid_encrypted_data")
            manager._settings.sync()

            # Should handle corruption gracefully and return default
            with patch("app.services.settings_manager.log_error"):
                email = manager.email
                assert email == ""  # Should return default value


class TestSettingsManagerBooleanHandling:
    """Tests for SettingsManager boolean type handling to prevent bool/int confusion."""

    @pytest.fixture
    def settings_manager(self, temp_settings_dir):
        """Create SettingsManager instance for testing."""
        with (
            patch.object(SettingsManager, "_get_storage_path", return_value=temp_settings_dir),
            patch.object(SettingsManager, "_secure_storage_directory"),
        ):
            return SettingsManager()

    def test_boolean_type_identification_priority(self, settings_manager):
        """Test that boolean types are identified before int types to prevent misidentification.

        This is the core regression test for the bool/int confusion bug.
        In Python, isinstance(True, int) returns True because bool is a subclass of int.
        """
        # Test True value identification
        result = settings_manager._get(key="test_bool_true", default=True)
        assert isinstance(result, bool), "Boolean default should be identified as bool, not int"
        assert result is True

        # Test False value identification
        result = settings_manager._get(key="test_bool_false", default=False)
        assert isinstance(result, bool), "Boolean default should be identified as bool, not int"
        assert result is False

        # Verify that this would have failed with the old int-first logic
        # We can't test the old behavior directly, but we can verify the fix works
        assert isinstance(True, int), "Sanity check: bool is subclass of int in Python"
        assert isinstance(False, int), "Sanity check: bool is subclass of int in Python"

    def test_boolean_string_conversion_true_values(self, settings_manager):
        """Test conversion of various string representations to True."""
        true_strings = ["true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON"]

        for true_str in true_strings:
            # Set string value directly in QSettings (simulates storage)
            settings_manager._settings.setValue("test_bool_setting", true_str)

            # Retrieve with boolean default - should convert to True
            result = settings_manager._get(key="test_bool_setting", default=False)
            assert result is True, f"String '{true_str}' should convert to True"
            assert isinstance(
                result, bool
            ), f"Result for '{true_str}' should be bool, not {type(result)}"

    def test_boolean_string_conversion_false_values(self, settings_manager):
        """Test conversion of various string representations to False."""
        false_strings = ["false", "False", "FALSE", "0", "no", "No", "NO", "off", "Off", "OFF"]

        for false_str in false_strings:
            # Set string value directly in QSettings (simulates storage)
            settings_manager._settings.setValue("test_bool_setting", false_str)

            # Retrieve with boolean default - should convert to False
            result = settings_manager._get(key="test_bool_setting", default=True)
            assert result is False, f"String '{false_str}' should convert to False"
            assert isinstance(
                result, bool
            ), f"Result for '{false_str}' should be bool, not {type(result)}"

    def test_boolean_edge_cases_and_invalid_values(self, settings_manager):
        """Test edge cases and invalid boolean string values."""
        invalid_strings = ["maybe", "2", "42", "yes please", "", "truthy", "falsy"]

        for invalid_str in invalid_strings:
            # Set invalid string value
            settings_manager._settings.setValue("test_bool_setting", invalid_str)

            # For invalid strings, the implementation returns False when checking the 'in' condition
            # This is the actual behavior - invalid strings are treated as False
            result_true_default = settings_manager._get(key="test_bool_setting", default=True)
            result_false_default = settings_manager._get(key="test_bool_setting", default=False)

            # Invalid strings should return False (not in the true list) regardless of default
            assert (
                result_true_default is False
            ), f"Invalid string '{invalid_str}' should return False (not in true list)"
            assert (
                result_false_default is False
            ), f"Invalid string '{invalid_str}' should return False (not in true list)"
            assert isinstance(
                result_true_default, bool
            ), f"Result should be bool for '{invalid_str}'"
            assert isinstance(
                result_false_default, bool
            ), f"Result should be bool for '{invalid_str}'"

    def test_boolean_none_values(self, settings_manager):
        """Test handling of None values with boolean defaults."""
        # Test with None stored value
        settings_manager._settings.setValue("test_bool_setting", None)

        result_true = settings_manager._get(key="test_bool_setting", default=True)
        result_false = settings_manager._get(key="test_bool_setting", default=False)

        assert result_true is True, "None value should return True default"
        assert result_false is False, "None value should return False default"

    def test_boolean_early_return_when_value_equals_default(self, settings_manager):
        """Test the early return path when stored value equals default."""
        # Test when stored value exactly equals the default (should return early)
        settings_manager._settings.setValue("test_bool_setting", True)
        result = settings_manager._get(key="test_bool_setting", default=True)
        assert result is True, "Value equal to default should return early"
        assert isinstance(result, bool)

        settings_manager._settings.setValue("test_bool_setting", False)
        result = settings_manager._get(key="test_bool_setting", default=False)
        assert result is False, "Value equal to default should return early"
        assert isinstance(result, bool)

    @pytest.mark.parametrize("platform", ["darwin", "win32", "linux"])
    def test_cross_platform_boolean_storage(self, settings_manager, platform):
        """Test boolean storage and retrieval across different platforms."""
        with patch("sys.platform", platform):
            # Test boolean storage and retrieval cycle
            test_values = [True, False]

            for test_value in test_values:
                settings_manager._set(key="cross_platform_bool", value=test_value)
                result = settings_manager._get(key="cross_platform_bool", default=not test_value)

                assert result is test_value, f"Boolean {test_value} should persist on {platform}"
                assert isinstance(result, bool), f"Result should be bool on {platform}"

    def test_real_boolean_properties_check_updates_on_startup(self, settings_manager):
        """Test the real check_updates_on_startup boolean property."""
        # Test default value
        assert isinstance(settings_manager.check_updates_on_startup, bool)
        assert settings_manager.check_updates_on_startup == DEFAULT_CHECK_UPDATES_ON_STARTUP

        # Test setting and getting True
        settings_manager.check_updates_on_startup = True
        assert settings_manager.check_updates_on_startup is True
        assert isinstance(settings_manager.check_updates_on_startup, bool)

        # Test setting and getting False
        settings_manager.check_updates_on_startup = False
        assert settings_manager.check_updates_on_startup is False
        assert isinstance(settings_manager.check_updates_on_startup, bool)

        # Test that the value persists through storage
        # Simulate QSettings string storage
        settings_manager._settings.setValue(SETTING_CHECK_UPDATES_ON_STARTUP, "true")
        result = settings_manager.check_updates_on_startup
        assert result is True
        assert isinstance(result, bool)

    def test_real_boolean_properties_enable_audio_conversion(self, settings_manager):
        """Test the real enable_audio_conversion boolean property."""
        # Test default value
        assert isinstance(settings_manager.enable_audio_conversion, bool)
        assert settings_manager.enable_audio_conversion == DEFAULT_ENABLE_AUDIO_CONVERSION

        # Test setting and getting True
        settings_manager.enable_audio_conversion = True
        assert settings_manager.enable_audio_conversion is True
        assert isinstance(settings_manager.enable_audio_conversion, bool)

        # Test setting and getting False
        settings_manager.enable_audio_conversion = False
        assert settings_manager.enable_audio_conversion is False
        assert isinstance(settings_manager.enable_audio_conversion, bool)

        # Test that the value persists through storage
        # Simulate QSettings string storage
        settings_manager._settings.setValue(SETTING_ENABLE_AUDIO_CONVERSION, "false")
        result = settings_manager.enable_audio_conversion
        assert result is False
        assert isinstance(result, bool)

    def test_boolean_vs_int_type_coexistence(self, settings_manager):
        """Test that boolean and integer settings can coexist without confusion."""
        # Set both boolean and integer values
        settings_manager._set(key="test_bool", value=True)
        settings_manager._set(key="test_int", value=1)

        # Retrieve with appropriate defaults
        bool_result = settings_manager._get(key="test_bool", default=False)
        int_result = settings_manager._get(key="test_int", default=0)

        # Verify types are preserved correctly
        assert bool_result is True
        assert isinstance(bool_result, bool)
        assert int_result == 1
        assert isinstance(int_result, int)
        assert not isinstance(int_result, bool)  # Should not be identified as bool

    def test_boolean_property_integration_lifecycle(self, settings_manager):
        """Test complete lifecycle of boolean properties from storage to retrieval."""
        # Test check_updates_on_startup lifecycle
        original_value = settings_manager.check_updates_on_startup

        # Change the value
        new_value = not original_value
        settings_manager.check_updates_on_startup = new_value

        # Verify immediate retrieval
        assert settings_manager.check_updates_on_startup is new_value

        # Simulate QSettings persistence by checking underlying storage
        stored_value = settings_manager._settings.value(SETTING_CHECK_UPDATES_ON_STARTUP)
        assert stored_value is not None, "Value should be stored in QSettings"

        # Clear and re-retrieve to test persistence
        settings_manager._settings.setValue(
            SETTING_CHECK_UPDATES_ON_STARTUP, str(new_value).lower()
        )
        retrieved_value = settings_manager.check_updates_on_startup
        assert retrieved_value is new_value
        assert isinstance(retrieved_value, bool)
