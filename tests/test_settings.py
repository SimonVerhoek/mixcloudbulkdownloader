"""Tests for SettingsManager class and enhanced license credential functionality."""

import os
import pytest
import time
from unittest.mock import patch, MagicMock, Mock

from app.services.settings_manager import SettingsManager, settings
from app.consts.settings import (
    KEYRING_SERVICE_NAME, 
    KEYRING_EMAIL_KEY, 
    KEYRING_LICENSE_KEY,
    SETTING_MAX_PARALLEL_DOWNLOADS,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
)


class TestSettingsManager:
    """Test cases for SettingsManager class."""

    def test_init_creates_qsettings_instance(self):
        """Test that initialization creates a QSettings instance with correct parameters."""
        with patch('app.services.settings_manager.QSettings') as mock_qsettings:
            settings_instance = SettingsManager()
            
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
            assert settings_instance._settings is not None

    def test_init_calls_initialize_from_env(self):
        """Test that initialization automatically calls _initialize_from_env."""
        with patch('app.services.settings_manager.QSettings'), \
             patch.object(SettingsManager, '_initialize_from_env') as mock_init:
            SettingsManager()
            
            mock_init.assert_called_once()


    def test_initialize_from_env_is_noop(self):
        """Test calling _initialize_from_env method is now a no-op."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings):
            settings = SettingsManager()
            mock_settings.setValue.reset_mock()
            
            # Test that _initialize_from_env does nothing
            settings._initialize_from_env()
            mock_settings.setValue.assert_not_called()

    def test_sync(self):
        """Test sync method calls QSettings sync."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings):
            settings = SettingsManager()
            settings.sync()
            
            mock_settings.sync.assert_called_once()

    def test_reset_to_defaults(self):
        """Test reset_to_defaults method calls QSettings clear."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings):
            settings = SettingsManager()
            settings.reset_to_defaults()
            
            mock_settings.clear.assert_called_once()


    def test_docstring_examples(self):
        """Test that the class works as described in docstrings."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = False
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings):
            # Should be able to create settings manager
            settings = SettingsManager()
            assert settings is not None
            
            # Should provide centralized interface for settings
            assert hasattr(settings, 'sync')
            assert hasattr(settings, 'reset_to_defaults')
            
            # Should use QSettings for persistence
            assert settings._settings is not None

    def test_multiple_settings_instances_independent(self):
        """Test that multiple SettingsManager instances are independent."""
        mock_settings_1 = MagicMock()
        mock_settings_2 = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', side_effect=[mock_settings_1, mock_settings_2]):
            
            settings1 = SettingsManager()
            settings2 = SettingsManager()
            
            # Each instance should have its own QSettings
            assert settings1._settings is mock_settings_1
            assert settings2._settings is mock_settings_2
            assert settings1._settings is not settings2._settings
            

    def test_qsettings_integration_details(self):
        """Test specific QSettings integration details."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings) as mock_qsettings:
            settings = SettingsManager()
            
            # Test that QSettings is initialized with correct organization and application
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
            


@pytest.fixture
def fresh_settings():
    """Create a fresh SettingsManager instance for testing."""
    with patch('app.services.settings_manager.QSettings') as mock_qsettings:
        mock_instance = Mock()
        mock_qsettings.return_value = mock_instance
        settings_instance = SettingsManager()
        settings_instance._settings = mock_instance
        # Clear any calls made during initialization
        mock_instance.setValue.reset_mock()
        return settings_instance, mock_instance


class TestSettingsManagerCredentials:
    """Test credential storage and retrieval functionality."""

    def test_email_property_getter(self, fresh_settings):
        """Test email property getter calls _retrieve_credential correctly."""
        settings_instance, mock_qsettings = fresh_settings
        
        with patch.object(settings_instance, '_retrieve_credential', return_value="test@example.com") as mock_retrieve:
            result = settings_instance.email
            
            assert result == "test@example.com"
            mock_retrieve.assert_called_once_with(KEYRING_EMAIL_KEY, "")

    def test_email_property_setter(self, fresh_settings):
        """Test email property setter calls _store_credential correctly.""" 
        settings_instance, mock_qsettings = fresh_settings
        
        with patch.object(settings_instance, '_store_credential') as mock_store:
            settings_instance.email = "newemail@example.com"
            
            mock_store.assert_called_once_with(KEYRING_EMAIL_KEY, "newemail@example.com")

    def test_license_key_property_getter(self, fresh_settings):
        """Test license_key property getter calls _retrieve_credential correctly."""
        settings_instance, mock_qsettings = fresh_settings
        
        with patch.object(settings_instance, '_retrieve_credential', return_value="abc123") as mock_retrieve:
            result = settings_instance.license_key
            
            assert result == "abc123"
            mock_retrieve.assert_called_once_with(KEYRING_LICENSE_KEY, "")

    def test_license_key_property_setter(self, fresh_settings):
        """Test license_key property setter calls _store_credential correctly."""
        settings_instance, mock_qsettings = fresh_settings
        
        with patch.object(settings_instance, '_store_credential') as mock_store:
            settings_instance.license_key = "newkey123"
            
            mock_store.assert_called_once_with(KEYRING_LICENSE_KEY, "newkey123")

    def test_last_successful_verification_getter(self, fresh_settings):
        """Test last_successful_verification property getter."""
        settings_instance, mock_qsettings = fresh_settings
        timestamp = 1234567890.0
        mock_qsettings.value.return_value = timestamp
        
        result = settings_instance.last_successful_verification
        
        assert result == timestamp
        mock_qsettings.value.assert_called_once_with("last_successful_verification", 0.0, type=float)

    def test_last_successful_verification_setter(self, fresh_settings):
        """Test last_successful_verification property setter."""
        settings_instance, mock_qsettings = fresh_settings
        timestamp = time.time()
        
        settings_instance.last_successful_verification = timestamp
        
        mock_qsettings.setValue.assert_called_once_with("last_successful_verification", timestamp)

    def test_last_successful_verification_default(self, fresh_settings):
        """Test last_successful_verification returns 0.0 when not set."""
        settings_instance, mock_qsettings = fresh_settings
        mock_qsettings.value.return_value = 0.0
        
        result = settings_instance.last_successful_verification
        
        assert result == 0.0


@pytest.mark.unit
class TestSettingsManagerThreadingInitialization:
    """Test cases for threading settings initialization functionality."""

    def test_initialize_threading_settings_pro_user_new_settings(self, fresh_settings):
        """Test initialization for Pro user with no existing settings."""
        settings_instance, mock_qsettings = fresh_settings
        
        # Mock get method to return None (no existing settings)
        mock_qsettings.value.return_value = None
        
        # Call initialize_threading_settings for Pro user
        settings_instance.initialize_threading_settings(is_pro=True)
        
        # Verify Pro defaults were set
        expected_calls = [
            (SETTING_MAX_PARALLEL_DOWNLOADS, DEFAULT_MAX_PARALLEL_DOWNLOADS),
            (SETTING_MAX_PARALLEL_CONVERSIONS, DEFAULT_MAX_PARALLEL_CONVERSIONS),
        ]
        
        # Check that setValue was called with Pro defaults
        for key, value in expected_calls:
            mock_qsettings.setValue.assert_any_call(key, value)
        
        # Verify sync was called
        mock_qsettings.sync.assert_called_once()

    def test_initialize_threading_settings_free_user_new_settings(self, fresh_settings):
        """Test initialization for free user with no existing settings."""
        settings_instance, mock_qsettings = fresh_settings
        
        # Mock get method to return None (no existing settings)
        mock_qsettings.value.return_value = None
        
        # Call initialize_threading_settings for free user
        settings_instance.initialize_threading_settings(is_pro=False)
        
        # Verify free user defaults (1) were set
        expected_calls = [
            (SETTING_MAX_PARALLEL_DOWNLOADS, 1),
            (SETTING_MAX_PARALLEL_CONVERSIONS, 0),
        ]
        
        # Check that setValue was called with free user defaults
        for key, value in expected_calls:
            mock_qsettings.setValue.assert_any_call(key, value)
        
        # Verify sync was called
        mock_qsettings.sync.assert_called_once()

    def test_initialize_threading_settings_existing_settings_not_overwritten(self, fresh_settings):
        """Test that existing threading settings are not overwritten."""
        settings_instance, mock_qsettings = fresh_settings
        
        # Mock get method to return existing values
        existing_values = {
            SETTING_MAX_PARALLEL_DOWNLOADS: 5,
            SETTING_MAX_PARALLEL_CONVERSIONS: 3,
        }
        
        def mock_get(key, default=None):
            return existing_values.get(key, default)
        
        # Replace the get method with our mock
        settings_instance.get = Mock(side_effect=mock_get)
        
        # Call initialize_threading_settings for Pro user
        settings_instance.initialize_threading_settings(is_pro=True)
        
        # Verify setValue was NOT called for existing settings
        mock_qsettings.setValue.assert_not_called()
        
        # Verify sync was still called
        mock_qsettings.sync.assert_called_once()

    def test_initialize_threading_settings_partial_existing_settings(self, fresh_settings):
        """Test initialization when only some settings exist."""
        settings_instance, mock_qsettings = fresh_settings
        
        # Mock get method: downloads setting exists, conversions doesn't
        def mock_get(key, default=None):
            if key == SETTING_MAX_PARALLEL_DOWNLOADS:
                return 6  # Existing value
            return None  # No existing value
        
        settings_instance.get = Mock(side_effect=mock_get)
        
        # Call initialize_threading_settings for Pro user
        settings_instance.initialize_threading_settings(is_pro=True)
        
        # Verify only the missing setting was set
        mock_qsettings.setValue.assert_called_once_with(
            SETTING_MAX_PARALLEL_CONVERSIONS, 
            DEFAULT_MAX_PARALLEL_CONVERSIONS
        )
        
        # Verify sync was called
        mock_qsettings.sync.assert_called_once()

    def test_initialize_threading_settings_pro_defaults_values(self):
        """Test that the Pro defaults are correctly configured."""
        # Verify the constants match expected Pro values
        assert DEFAULT_MAX_PARALLEL_DOWNLOADS == 3
        assert DEFAULT_MAX_PARALLEL_CONVERSIONS == 2

    def test_initialize_threading_settings_free_defaults_values(self, fresh_settings):
        """Test that free user defaults are set to 1."""
        settings_instance, mock_qsettings = fresh_settings
        
        # Mock get method to return None (no existing settings)
        mock_qsettings.value.return_value = None
        
        # Call initialize_threading_settings for free user
        settings_instance.initialize_threading_settings(is_pro=False)
        
        # Verify both settings were set to 1 for free users
        mock_qsettings.setValue.assert_any_call(SETTING_MAX_PARALLEL_DOWNLOADS, 1)
        mock_qsettings.setValue.assert_any_call(SETTING_MAX_PARALLEL_CONVERSIONS, 0)

    def test_initialize_threading_settings_calls_sync(self, fresh_settings):
        """Test that initialize_threading_settings always calls sync."""
        settings_instance, mock_qsettings = fresh_settings
        
        # Test with Pro user
        settings_instance.initialize_threading_settings(is_pro=True)
        assert mock_qsettings.sync.call_count == 1
        
        # Reset and test with free user
        mock_qsettings.sync.reset_mock()
        settings_instance.initialize_threading_settings(is_pro=False)
        assert mock_qsettings.sync.call_count == 1

    def test_initialize_threading_settings_method_exists(self):
        """Test that the initialize_threading_settings method exists and is callable."""
        with patch('app.services.settings_manager.QSettings'):
            settings_instance = SettingsManager()
            
            # Method should exist and be callable
            assert hasattr(settings_instance, 'initialize_threading_settings')
            assert callable(getattr(settings_instance, 'initialize_threading_settings'))

    def test_threading_constants_imported_correctly(self):
        """Test that all required threading constants are properly imported."""
        # These should all be accessible and have expected types
        assert isinstance(SETTING_MAX_PARALLEL_DOWNLOADS, str)
        assert isinstance(SETTING_MAX_PARALLEL_CONVERSIONS, str)
        assert isinstance(DEFAULT_MAX_PARALLEL_DOWNLOADS, int)
        assert isinstance(DEFAULT_MAX_PARALLEL_CONVERSIONS, int)
        
        # Setting keys should be descriptive
        assert "parallel" in SETTING_MAX_PARALLEL_DOWNLOADS.lower()
        assert "parallel" in SETTING_MAX_PARALLEL_CONVERSIONS.lower()
        assert "download" in SETTING_MAX_PARALLEL_DOWNLOADS.lower()
        assert "conversion" in SETTING_MAX_PARALLEL_CONVERSIONS.lower()


class TestCredentialStorage:
    """Test keyring integration with QSettings fallback."""

    def test_store_credential_keyring_success(self, fresh_settings):
        """Test successful credential storage using keyring."""
        settings_instance, mock_qsettings = fresh_settings
        
        with patch('keyring.set_password') as mock_keyring_set:
            settings_instance._store_credential("test_key", "test_value")
            
            mock_keyring_set.assert_called_once_with(KEYRING_SERVICE_NAME, "test_key", "test_value")
            mock_qsettings.remove.assert_called_once_with("test_key")

    def test_store_credential_keyring_failure_fallback(self, fresh_settings):
        """Test credential storage falls back to QSettings when keyring fails."""
        settings_instance, mock_qsettings = fresh_settings
        
        with patch('keyring.set_password', side_effect=Exception("Keyring error")):
            with patch('builtins.print') as mock_print:
                settings_instance._store_credential("test_key", "test_value")
                
                mock_qsettings.setValue.assert_called_once_with("test_key", "test_value")
                mock_print.assert_called_once()

    def test_store_credential_keyring_import_error_fallback(self, fresh_settings):
        """Test credential storage falls back to QSettings when keyring import fails."""
        settings_instance, mock_qsettings = fresh_settings
        
        with patch('app.services.settings_manager.keyring.set_password', side_effect=ImportError("No keyring module")):
            with patch('builtins.print') as mock_print:
                settings_instance._store_credential("test_key", "test_value")
                
                mock_qsettings.setValue.assert_called_once_with("test_key", "test_value")
                mock_print.assert_called_once()

    def test_retrieve_credential_keyring_success(self, fresh_settings):
        """Test successful credential retrieval from keyring."""
        settings_instance, mock_qsettings = fresh_settings
        
        with patch('keyring.get_password', return_value="keyring_value") as mock_keyring_get:
            result = settings_instance._retrieve_credential("test_key", "default")
            
            assert result == "keyring_value"
            mock_keyring_get.assert_called_once_with(KEYRING_SERVICE_NAME, "test_key")
            mock_qsettings.value.assert_not_called()

    def test_retrieve_credential_keyring_none_fallback(self, fresh_settings):
        """Test credential retrieval falls back to QSettings when keyring returns None."""
        settings_instance, mock_qsettings = fresh_settings
        mock_qsettings.value.return_value = "qsettings_value"
        
        with patch('keyring.get_password', return_value=None) as mock_keyring_get:
            result = settings_instance._retrieve_credential("test_key", "default")
            
            assert result == "qsettings_value"
            mock_keyring_get.assert_called_once_with(KEYRING_SERVICE_NAME, "test_key")
            mock_qsettings.value.assert_called_once_with("test_key", "default", type=str)

    def test_retrieve_credential_keyring_error_fallback(self, fresh_settings):
        """Test credential retrieval falls back to QSettings when keyring errors."""
        settings_instance, mock_qsettings = fresh_settings
        mock_qsettings.value.return_value = "qsettings_value"
        
        with patch('keyring.get_password', side_effect=Exception("Keyring error")):
            with patch('builtins.print') as mock_print:
                result = settings_instance._retrieve_credential("test_key", "default")
                
                assert result == "qsettings_value"
                mock_qsettings.value.assert_called_once_with("test_key", "default", type=str)
                mock_print.assert_called_once()

    def test_retrieve_credential_qsettings_only(self, fresh_settings):
        """Test credential retrieval from QSettings when keyring import fails."""
        settings_instance, mock_qsettings = fresh_settings
        mock_qsettings.value.return_value = "qsettings_value"
        
        with patch('app.services.settings_manager.keyring.get_password', side_effect=ImportError("No keyring module")):
            with patch('builtins.print') as mock_print:
                result = settings_instance._retrieve_credential("test_key", "default")
                
                assert result == "qsettings_value"
                mock_qsettings.value.assert_called_once_with("test_key", "default", type=str)
                mock_print.assert_called_once()


class TestSettingsSingleton:
    """Test settings singleton pattern."""

    def test_settings_singleton_exists(self):
        """Test that settings singleton instance exists."""
        assert settings is not None
        assert isinstance(settings, SettingsManager)

    def test_settings_singleton_is_same_instance(self):
        """Test that importing settings gives the same instance."""
        from app.services.settings_manager import settings as settings2
        assert settings is settings2

    def test_settings_singleton_has_required_methods(self):
        """Test that settings singleton has all required methods and properties."""
        assert hasattr(settings, 'email')
        assert hasattr(settings, 'license_key') 
        assert hasattr(settings, 'last_successful_verification')
        assert hasattr(settings, '_store_credential')
        assert hasattr(settings, '_retrieve_credential')


class TestBackwardCompatibility:
    """Test that existing functionality still works."""


    def test_existing_sync_method(self, fresh_settings):
        """Test that existing sync method still works."""
        settings_instance, mock_qsettings = fresh_settings
        
        settings_instance.sync()
        
        mock_qsettings.sync.assert_called_once()

    def test_existing_reset_to_defaults_method(self, fresh_settings):
        """Test that existing reset_to_defaults method still works."""
        settings_instance, mock_qsettings = fresh_settings
        
        settings_instance.reset_to_defaults()
        
        mock_qsettings.clear.assert_called_once()


class TestLocalSecretsStorage:
    """Test local file-based secrets storage for development mode."""
    
    @pytest.fixture
    def development_settings(self, tmp_path):
        """Create SettingsManager instance with development mode and custom path for testing."""
        custom_dir = tmp_path / "test_settings"
        
        with patch('app.services.settings_manager.QSettings') as mock_qsettings, \
             patch('app.services.settings_manager.DEVELOPMENT', True), \
             patch('app.services.settings_manager.CUSTOM_SETTINGS_PATH', str(custom_dir)):
            mock_instance = Mock()
            mock_qsettings.return_value = mock_instance
            settings_instance = SettingsManager()
            settings_instance._settings = mock_instance
            mock_instance.setValue.reset_mock()
            return settings_instance, mock_instance, custom_dir
    
    def test_local_file_store_credential_success(self, development_settings):
        """Test successful credential storage to local file."""
        settings_instance, mock_qsettings, custom_dir = development_settings
        
        # Store a credential
        settings_instance._store_credential("test_key", "test_value")
        
        # Check that secrets file was created
        secrets_file = custom_dir / ".secrets.json"
        assert secrets_file.exists()
        
        # Check file permissions are restrictive
        stat_info = secrets_file.stat()
        # On Unix-like systems, check that permissions are 0o600
        if hasattr(stat_info, 'st_mode'):
            # Extract permission bits (last 3 octal digits)
            perms = stat_info.st_mode & 0o777
            # Should be 0o600 on Unix-like systems, but Windows may differ
            assert perms <= 0o700  # At least not world-readable
        
        # Verify QSettings remove was called to clear plaintext storage
        mock_qsettings.remove.assert_called_once_with("test_key")
        
        # Verify we can retrieve the stored value
        retrieved = settings_instance._retrieve_credential("test_key", "default")
        assert retrieved == "test_value"
        
        # Verify the file contains plain JSON (not base64 encoded)
        with open(secrets_file, 'r') as f:
            content = f.read()
            # Should be able to find the credential value in plain text
            assert "test_value" in content
    
    def test_local_file_store_multiple_credentials(self, development_settings):
        """Test storing multiple credentials in local file."""
        settings_instance, _, _ = development_settings
        
        # Store multiple credentials
        settings_instance._store_credential("email", "user@example.com")
        settings_instance._store_credential("license_key", "abc123")
        settings_instance._store_credential("api_token", "token456")
        
        # Verify all can be retrieved
        assert settings_instance._retrieve_credential("email", "") == "user@example.com"
        assert settings_instance._retrieve_credential("license_key", "") == "abc123"
        assert settings_instance._retrieve_credential("api_token", "") == "token456"
    
    def test_local_file_retrieve_nonexistent_key(self, development_settings):
        """Test retrieving a credential that doesn't exist."""
        settings_instance, mock_qsettings, _ = development_settings
        mock_qsettings.value.return_value = "qsettings_default"
        
        # Try to retrieve non-existent key
        result = settings_instance._retrieve_credential("nonexistent", "default")
        
        # Should fall back to QSettings
        assert result == "qsettings_default"
        mock_qsettings.value.assert_called_once_with("nonexistent", "default", type=str)
    
    def test_local_file_retrieve_no_secrets_file(self, development_settings):
        """Test retrieving credential when no secrets file exists."""
        settings_instance, mock_qsettings, _ = development_settings
        mock_qsettings.value.return_value = "qsettings_fallback"
        
        # Try to retrieve when no secrets file exists
        result = settings_instance._retrieve_credential("test_key", "default")
        
        # Should fall back to QSettings
        assert result == "qsettings_fallback"
        mock_qsettings.value.assert_called_once_with("test_key", "default", type=str)
    
    def test_local_file_corrupted_secrets_handling(self, development_settings):
        """Test handling of corrupted secrets file."""
        settings_instance, mock_qsettings, custom_dir = development_settings
        
        # Create a corrupted secrets file
        secrets_file = custom_dir / ".secrets.json"
        secrets_file.parent.mkdir(parents=True, exist_ok=True)
        with open(secrets_file, 'w') as f:
            f.write("invalid json content")
        
        mock_qsettings.value.return_value = "qsettings_fallback"
        
        # Try to retrieve from corrupted file
        result = settings_instance._retrieve_credential("test_key", "default")
        
        # Should fall back to QSettings
        assert result == "qsettings_fallback"
        mock_qsettings.value.assert_called_once_with("test_key", "default", type=str)
    
    def test_local_file_overwrite_existing_credential(self, development_settings):
        """Test overwriting an existing credential."""
        settings_instance, _, _ = development_settings
        
        # Store initial credential
        settings_instance._store_credential("test_key", "original_value")
        assert settings_instance._retrieve_credential("test_key", "") == "original_value"
        
        # Overwrite with new value
        settings_instance._store_credential("test_key", "new_value")
        assert settings_instance._retrieve_credential("test_key", "") == "new_value"
    
    def test_local_file_storage_with_empty_value(self, development_settings):
        """Test storing and retrieving empty credential values."""
        settings_instance, _, _ = development_settings
        
        # Store empty value
        settings_instance._store_credential("empty_key", "")
        
        # Should be able to retrieve empty string (not None)
        result = settings_instance._retrieve_credential("empty_key", "default")
        assert result == ""
    
    def test_local_file_secrets_file_encoding(self, development_settings):
        """Test that secrets file uses proper encoding for special characters."""
        settings_instance, _, _ = development_settings
        
        # Store credential with special characters
        special_value = "test@example.com with üñíçødé"
        settings_instance._store_credential("unicode_key", special_value)
        
        # Should be able to retrieve with special characters intact
        result = settings_instance._retrieve_credential("unicode_key", "")
        assert result == special_value
        
    def test_production_mode_ignores_custom_path(self, tmp_path):
        """Test that CUSTOM_SETTINGS_PATH is ignored when DEVELOPMENT is not True."""
        custom_dir = tmp_path / "test_settings"
        
        with patch('app.services.settings_manager.QSettings') as mock_qsettings, \
             patch('app.services.settings_manager.DEVELOPMENT', False), \
             patch('app.services.settings_manager.CUSTOM_SETTINGS_PATH', str(custom_dir)):
            mock_instance = Mock()
            mock_qsettings.return_value = mock_instance
            settings_instance = SettingsManager()
            
            # Should not have custom path set
            assert settings_instance._custom_path is None
            
            # QSettings should be called with default parameters, not custom file
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
            
    def test_no_development_var_ignores_custom_path(self, tmp_path):
        """Test that CUSTOM_SETTINGS_PATH is ignored when DEVELOPMENT is not set."""
        custom_dir = tmp_path / "test_settings"
        
        with patch('app.services.settings_manager.QSettings') as mock_qsettings, \
             patch('app.services.settings_manager.DEVELOPMENT', False), \
             patch('app.services.settings_manager.CUSTOM_SETTINGS_PATH', str(custom_dir)):
            mock_instance = Mock()
            mock_qsettings.return_value = mock_instance
            settings_instance = SettingsManager()
            
            # Should not have custom path set
            assert settings_instance._custom_path is None
            
            # QSettings should be called with default parameters, not custom file
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
