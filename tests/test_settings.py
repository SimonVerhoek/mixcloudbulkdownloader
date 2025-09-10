"""Tests for SettingsManager class and enhanced license credential functionality."""

import os
import pytest
import time
from unittest.mock import patch, MagicMock, Mock

from app.services.settings_manager import SettingsManager, settings
from app.consts import KEYRING_SERVICE_NAME, KEYRING_EMAIL_KEY, KEYRING_LICENSE_KEY


class TestSettingsManager:
    """Test cases for SettingsManager class."""

    def test_init_creates_qsettings_instance(self):
        """Test that initialization creates a QSettings instance with correct parameters."""
        with patch('app.services.settings_manager.QSettings') as mock_qsettings, \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings_instance = SettingsManager()
            
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
            assert settings_instance._settings is not None

    def test_init_calls_initialize_from_env(self):
        """Test that initialization automatically calls _initialize_from_env."""
        with patch('app.services.settings_manager.QSettings'), \
             patch.object(SettingsManager, '_initialize_from_env') as mock_init:
            SettingsManager()
            
            mock_init.assert_called_once()

    def test_settings_pane_enabled_getter_default(self):
        """Test settings_pane_enabled getter returns default value."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = False
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            result = settings.settings_pane_enabled
            
            assert result is False
            mock_settings.value.assert_called_with("settings_pane_enabled", False, type=bool)

    def test_settings_pane_enabled_getter_true(self):
        """Test settings_pane_enabled getter returns True when stored."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = True
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            result = settings.settings_pane_enabled
            
            assert result is True
            mock_settings.value.assert_called_with("settings_pane_enabled", False, type=bool)

    def test_settings_pane_enabled_getter_returns_bool(self):
        """Test settings_pane_enabled getter always returns bool type."""
        mock_settings = MagicMock()
        # Test various truthy/falsy return values
        test_values = ["true", "false", 1, 0, None, ""]
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            
            for test_value in test_values:
                mock_settings.value.return_value = test_value
                result = settings.settings_pane_enabled
                assert isinstance(result, bool)

    def test_settings_pane_enabled_setter(self):
        """Test settings_pane_enabled setter stores value correctly."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            
            # Reset call count from initialization
            mock_settings.setValue.reset_mock()
            
            # Test setting to True
            settings.settings_pane_enabled = True
            mock_settings.setValue.assert_called_with("settings_pane_enabled", True)
            
            # Test setting to False
            settings.settings_pane_enabled = False
            mock_settings.setValue.assert_called_with("settings_pane_enabled", False)

    def test_initialize_from_env_with_feature_flag_true(self):
        """Test _initialize_from_env sets value when feature flag is True."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', True):
            settings = SettingsManager()
            
            # The setValue should be called during initialization
            mock_settings.setValue.assert_called_with("settings_pane_enabled", True)

    def test_initialize_from_env_with_feature_flag_false(self):
        """Test _initialize_from_env sets value when feature flag is False."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            
            # The setValue should be called during initialization
            mock_settings.setValue.assert_called_with("settings_pane_enabled", False)

    def test_initialize_from_env_directly(self):
        """Test calling _initialize_from_env method directly."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            mock_settings.setValue.reset_mock()
            
            # Test with feature flag True
            with patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', True):
                settings._initialize_from_env()
                mock_settings.setValue.assert_called_with("settings_pane_enabled", True)
            
            mock_settings.setValue.reset_mock()
            
            # Test with feature flag False  
            with patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
                settings._initialize_from_env()
                mock_settings.setValue.assert_called_with("settings_pane_enabled", False)

    def test_sync(self):
        """Test sync method calls QSettings sync."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            settings.sync()
            
            mock_settings.sync.assert_called_once()

    def test_reset_to_defaults(self):
        """Test reset_to_defaults method calls QSettings clear."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            settings.reset_to_defaults()
            
            mock_settings.clear.assert_called_once()

    def test_property_setter_integration(self):
        """Test that property setter and getter work together correctly."""
        mock_settings = MagicMock()
        
        # Store the actual stored value
        stored_values = {}
        
        def mock_set_value(key, value):
            stored_values[key] = value
        
        def mock_get_value(key, default, **kwargs):
            return stored_values.get(key, default)
        
        mock_settings.setValue.side_effect = mock_set_value
        mock_settings.value.side_effect = mock_get_value
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            
            # Environment flag should have been set during init
            assert settings.settings_pane_enabled is False
            
            # Set to True
            settings.settings_pane_enabled = True
            assert settings.settings_pane_enabled is True
            
            # Set to False
            settings.settings_pane_enabled = False
            assert settings.settings_pane_enabled is False

    def test_docstring_examples(self):
        """Test that the class works as described in docstrings."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = False
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            # Should be able to create settings manager
            settings = SettingsManager()
            assert settings is not None
            
            # Should provide centralized interface for settings
            assert hasattr(settings, 'settings_pane_enabled')
            assert hasattr(settings, 'sync')
            assert hasattr(settings, 'reset_to_defaults')
            
            # Should use QSettings for persistence
            assert settings._settings is not None

    @pytest.mark.parametrize("env_value,expected_calls", [
        (True, 1),   # Should call setValue when True
        (False, 1),  # Should call setValue when False  
    ])
    def test_initialize_from_env_parametrized(self, env_value, expected_calls):
        """Test _initialize_from_env with various feature flag values."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', env_value):
            SettingsManager()
            
            assert mock_settings.setValue.call_count == expected_calls
            mock_settings.setValue.assert_called_with("settings_pane_enabled", env_value)

    def test_settings_pane_enabled_setter_type_coercion(self):
        """Test that setter properly handles type coercion for boolean values."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            mock_settings.setValue.reset_mock()
            
            # Test that various truthy/falsy values are passed through as-is to QSettings
            # QSettings will handle the type conversion internally
            test_values = [True, False, 1, 0, "true", "false"]
            
            for value in test_values:
                settings.settings_pane_enabled = value
                mock_settings.setValue.assert_called_with("settings_pane_enabled", value)

    def test_multiple_settings_instances_independent(self):
        """Test that multiple SettingsManager instances are independent."""
        mock_settings_1 = MagicMock()
        mock_settings_2 = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', side_effect=[mock_settings_1, mock_settings_2]), \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            
            settings1 = SettingsManager()
            settings2 = SettingsManager()
            
            # Each instance should have its own QSettings
            assert settings1._settings is mock_settings_1
            assert settings2._settings is mock_settings_2
            assert settings1._settings is not settings2._settings
            
            # Operations on one should not affect the other
            mock_settings_1.setValue.reset_mock()
            mock_settings_2.setValue.reset_mock()
            
            settings1.settings_pane_enabled = True
            mock_settings_1.setValue.assert_called_once_with("settings_pane_enabled", True)
            mock_settings_2.setValue.assert_not_called()

    def test_qsettings_integration_details(self):
        """Test specific QSettings integration details."""
        mock_settings = MagicMock()
        
        with patch('app.services.settings_manager.QSettings', return_value=mock_settings) as mock_qsettings, \
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
            settings = SettingsManager()
            
            # Test that QSettings is initialized with correct organization and application
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
            
            # Test that getter calls QSettings.value with correct parameters
            mock_settings.value.reset_mock()
            mock_settings.value.return_value = True
            
            result = settings.settings_pane_enabled
            mock_settings.value.assert_called_once_with("settings_pane_enabled", False, type=bool)
            assert result is True


@pytest.fixture
def fresh_settings():
    """Create a fresh SettingsManager instance for testing."""
    with patch('app.services.settings_manager.QSettings') as mock_qsettings, \
         patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False):
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

    def test_existing_settings_pane_enabled_property(self, fresh_settings):
        """Test that existing settings_pane_enabled property still works."""
        settings_instance, mock_qsettings = fresh_settings
        mock_qsettings.value.return_value = True
        
        result = settings_instance.settings_pane_enabled
        
        assert result is True
        mock_qsettings.value.assert_called_with("settings_pane_enabled", False, type=bool)

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
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False), \
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
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False), \
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
             patch('app.services.settings_manager.FF_SETTINGS_PANE_ENABLED', False), \
             patch('app.services.settings_manager.DEVELOPMENT', False), \
             patch('app.services.settings_manager.CUSTOM_SETTINGS_PATH', str(custom_dir)):
            mock_instance = Mock()
            mock_qsettings.return_value = mock_instance
            settings_instance = SettingsManager()
            
            # Should not have custom path set
            assert settings_instance._custom_path is None
            
            # QSettings should be called with default parameters, not custom file
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")