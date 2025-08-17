"""Tests for MBDSettings class."""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.settings import MBDSettings


class TestMBDSettings:
    """Test cases for MBDSettings class."""

    def test_init_creates_qsettings_instance(self):
        """Test that initialization creates a QSettings instance with correct parameters."""
        with patch('app.settings.QSettings') as mock_qsettings, \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
            assert settings._settings is not None

    def test_init_calls_initialize_from_env(self):
        """Test that initialization automatically calls _initialize_from_env."""
        with patch('app.settings.QSettings'), \
             patch.object(MBDSettings, '_initialize_from_env') as mock_init:
            MBDSettings()
            
            mock_init.assert_called_once()

    def test_settings_pane_enabled_getter_default(self):
        """Test settings_pane_enabled getter returns default value."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = False
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            result = settings.settings_pane_enabled
            
            assert result is False
            mock_settings.value.assert_called_with("settings_pane_enabled", False, type=bool)

    def test_settings_pane_enabled_getter_true(self):
        """Test settings_pane_enabled getter returns True when stored."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = True
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            result = settings.settings_pane_enabled
            
            assert result is True
            mock_settings.value.assert_called_with("settings_pane_enabled", False, type=bool)

    def test_settings_pane_enabled_getter_returns_bool(self):
        """Test settings_pane_enabled getter always returns bool type."""
        mock_settings = MagicMock()
        # Test various truthy/falsy return values
        test_values = ["true", "false", 1, 0, None, ""]
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            
            for test_value in test_values:
                mock_settings.value.return_value = test_value
                result = settings.settings_pane_enabled
                assert isinstance(result, bool)

    def test_settings_pane_enabled_setter(self):
        """Test settings_pane_enabled setter stores value correctly."""
        mock_settings = MagicMock()
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            
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
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', True):
            settings = MBDSettings()
            
            # The setValue should be called during initialization
            mock_settings.setValue.assert_called_with("settings_pane_enabled", True)

    def test_initialize_from_env_with_feature_flag_false(self):
        """Test _initialize_from_env sets value when feature flag is False."""
        mock_settings = MagicMock()
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            
            # The setValue should be called during initialization
            mock_settings.setValue.assert_called_with("settings_pane_enabled", False)

    def test_initialize_from_env_directly(self):
        """Test calling _initialize_from_env method directly."""
        mock_settings = MagicMock()
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            mock_settings.setValue.reset_mock()
            
            # Test with feature flag True
            with patch('app.settings.FF_SETTINGS_PANE_ENABLED', True):
                settings._initialize_from_env()
                mock_settings.setValue.assert_called_with("settings_pane_enabled", True)
            
            mock_settings.setValue.reset_mock()
            
            # Test with feature flag False  
            with patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
                settings._initialize_from_env()
                mock_settings.setValue.assert_called_with("settings_pane_enabled", False)

    def test_sync(self):
        """Test sync method calls QSettings sync."""
        mock_settings = MagicMock()
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            settings.sync()
            
            mock_settings.sync.assert_called_once()

    def test_reset_to_defaults(self):
        """Test reset_to_defaults method calls QSettings clear."""
        mock_settings = MagicMock()
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
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
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            
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
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            # Should be able to create settings manager
            settings = MBDSettings()
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
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', env_value):
            MBDSettings()
            
            assert mock_settings.setValue.call_count == expected_calls
            mock_settings.setValue.assert_called_with("settings_pane_enabled", env_value)

    def test_settings_pane_enabled_setter_type_coercion(self):
        """Test that setter properly handles type coercion for boolean values."""
        mock_settings = MagicMock()
        
        with patch('app.settings.QSettings', return_value=mock_settings), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            mock_settings.setValue.reset_mock()
            
            # Test that various truthy/falsy values are passed through as-is to QSettings
            # QSettings will handle the type conversion internally
            test_values = [True, False, 1, 0, "true", "false"]
            
            for value in test_values:
                settings.settings_pane_enabled = value
                mock_settings.setValue.assert_called_with("settings_pane_enabled", value)

    def test_multiple_settings_instances_independent(self):
        """Test that multiple MBDSettings instances are independent."""
        mock_settings_1 = MagicMock()
        mock_settings_2 = MagicMock()
        
        with patch('app.settings.QSettings', side_effect=[mock_settings_1, mock_settings_2]), \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            
            settings1 = MBDSettings()
            settings2 = MBDSettings()
            
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
        
        with patch('app.settings.QSettings', return_value=mock_settings) as mock_qsettings, \
             patch('app.settings.FF_SETTINGS_PANE_ENABLED', False):
            settings = MBDSettings()
            
            # Test that QSettings is initialized with correct organization and application
            mock_qsettings.assert_called_once_with("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
            
            # Test that getter calls QSettings.value with correct parameters
            mock_settings.value.reset_mock()
            mock_settings.value.return_value = True
            
            result = settings.settings_pane_enabled
            mock_settings.value.assert_called_once_with("settings_pane_enabled", False, type=bool)
            assert result is True