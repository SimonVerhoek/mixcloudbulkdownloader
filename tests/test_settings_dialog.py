"""Tests for the settings dialog and its Pro feature integration."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox

from app.custom_widgets.dialogs.settings_dialog import SettingsDialog
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager


@pytest.fixture
def mock_license_manager():
    """Create a mock license manager for testing."""
    manager = Mock(spec=LicenseManager)
    manager.is_pro = False
    manager.license_status_changed = Mock()
    manager.license_status_changed.connect = Mock()
    return manager


@pytest.fixture
def mock_settings_manager():
    """Create a mock settings manager for testing."""
    manager = Mock(spec=SettingsManager)
    # Return default values for common settings keys
    def mock_get(key, default=None):
        defaults = {
            "default_download_directory": None,
            "default_audio_format": "MP3"
        }
        return defaults.get(key, default)
    
    manager.get = Mock(side_effect=mock_get)
    manager.set = Mock()
    return manager


@pytest.fixture
def pro_license_manager():
    """Create a mock pro license manager for testing."""
    manager = Mock(spec=LicenseManager)
    manager.is_pro = True
    manager.license_status_changed = Mock()
    manager.license_status_changed.connect = Mock()
    return manager


@pytest.mark.qt
class TestSettingsDialog:
    """Test cases for settings dialog functionality."""

    def test_settings_dialog_creation_free_user(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test settings dialog creation for free users."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Dialog should be created successfully
        assert dialog.windowTitle() == "Settings"
        assert dialog.isModal()
        
        # Pro widgets should be disabled
        assert not dialog.download_dir_button.isEnabled()
        assert not dialog.audio_format_combo.isEnabled()

    def test_settings_dialog_creation_pro_user(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test settings dialog creation for pro users."""
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Dialog should be created successfully
        assert dialog.windowTitle() == "Settings"
        
        # Pro widgets should be enabled
        assert dialog.download_dir_button.isEnabled()
        assert dialog.audio_format_combo.isEnabled()


    def test_pro_settings_loading_pro_user(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test loading of pro settings for pro users."""
        test_dir = "/test/directory"
        test_format = "FLAC"
        
        mock_settings_manager.get.side_effect = lambda key, default=None: {
            "default_download_directory": test_dir,
            "default_audio_format": test_format
        }.get(key, default)
        
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Pro settings should be loaded correctly
        assert dialog.download_dir_label.text() == test_dir
        assert dialog.audio_format_combo.currentText() == test_format

    def test_pro_settings_not_loaded_free_user(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test pro settings are not loaded for free users."""
        mock_settings_manager.get.side_effect = lambda key, default=None: {
            "default_download_directory": "/test/directory",
            "default_audio_format": "FLAC"
        }.get(key, default)
        
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Pro settings should not be loaded
        assert dialog.download_dir_label.text() == "Not set"
        assert dialog.audio_format_combo.currentText() == "MP3"  # Default

    @patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory')
    def test_browse_directory_pro_user(self, mock_file_dialog, qtbot, pro_license_manager, mock_settings_manager):
        """Test directory browsing for pro users."""
        test_directory = "/selected/directory"
        mock_file_dialog.return_value = test_directory
        
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Click browse button
        qtbot.mouseClick(dialog.download_dir_button, Qt.MouseButton.LeftButton)
        
        # Directory should be set in label
        assert dialog.download_dir_label.text() == test_directory
        mock_file_dialog.assert_called_once()

    def test_browse_directory_free_user_does_nothing(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test directory browsing for free users does nothing."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        original_text = dialog.download_dir_label.text()
        
        # Click browse button (should do nothing since not pro)
        qtbot.mouseClick(dialog.download_dir_button, Qt.MouseButton.LeftButton)
        
        # Directory label should remain unchanged
        assert dialog.download_dir_label.text() == original_text


    def test_save_settings_free_user(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test saving settings for free users (no Pro settings saved)."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Click OK button
        ok_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)
        
        # No settings should be saved for free users
        mock_settings_manager.set.assert_not_called()
        mock_settings_manager.sync.assert_called_once()

    def test_save_pro_settings_pro_user(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test saving pro settings for pro users."""
        test_directory = "/test/directory"
        
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Set pro settings
        dialog._set_directory_text(test_directory)  # Use the proper method to set directory
        dialog.audio_format_combo.setCurrentText("FLAC")
        
        # Click OK button
        ok_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)
        
        # Settings should be saved for pro users
        from unittest.mock import call
        expected_calls = [
            call("default_download_directory", test_directory),
            call("default_audio_format", "FLAC")
        ]
        mock_settings_manager.set.assert_has_calls(expected_calls, any_order=True)
        mock_settings_manager.sync.assert_called_once()


    def test_cancel_dialog(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test cancelling the dialog doesn't save settings."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Dialog created successfully
        
        # Click Cancel button
        cancel_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Cancel)
        qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
        
        # Settings should not be saved
        mock_settings_manager.set.assert_not_called()

    def test_license_status_change_updates_ui(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test that license status changes update the UI in real-time."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Initially should be disabled for free user
        assert not dialog.download_dir_button.isEnabled()
        
        # Simulate license status change to pro
        mock_license_manager.is_pro = True
        
        # Trigger the status change signal
        signal_handler = mock_license_manager.license_status_changed.connect.call_args[0][0]
        signal_handler()
        
        # UI should now be enabled
        assert dialog.download_dir_button.isEnabled()
        assert dialog.audio_format_combo.isEnabled()


@pytest.mark.qt  
class TestSettingsDialogIntegration:
    """Integration tests for settings dialog with real components."""
    
    def test_settings_dialog_with_real_managers(self, qtbot):
        """Test settings dialog with real license and settings managers."""
        from app.services.license_manager import LicenseManager
        from app.services.settings_manager import SettingsManager
        
        # Create real managers
        license_mgr = LicenseManager()
        settings_mgr = SettingsManager()
        
        # Ensure clean state
        license_mgr.is_pro = False
        
        dialog = SettingsDialog(
            license_manager=license_mgr,
            settings_manager=settings_mgr
        )
        qtbot.addWidget(dialog)
        
        # Dialog should work with real managers
        assert dialog.windowTitle() == "Settings"
        assert isinstance(dialog.license_manager, LicenseManager)
        assert isinstance(dialog.settings_manager, SettingsManager)
        
        # Pro widgets should be disabled for free user
        assert not dialog.download_dir_button.isEnabled()
        assert not dialog.audio_format_combo.isEnabled()

    def test_pro_feature_widget_integration(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test that settings dialog properly inherits from ProFeatureWidget."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Should have ProFeatureWidget capabilities
        assert hasattr(dialog, 'register_pro_widget')
        assert hasattr(dialog, '_pro_widgets')
        assert len(dialog._pro_widgets) > 0  # Pro widgets should be registered
        
        # Pro widgets should be in the list
        pro_widgets = dialog._pro_widgets
        assert dialog.download_dir_button in pro_widgets
        assert dialog.audio_format_combo in pro_widgets