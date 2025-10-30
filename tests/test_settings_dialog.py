"""Tests for the settings dialog and its Pro feature integration."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox

from app.custom_widgets.dialogs.settings_dialog import SettingsDialog
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager
from app.consts.settings import (
    SETTING_MAX_PARALLEL_DOWNLOADS,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
    PARALLEL_DOWNLOADS_OPTIONS,
    PARALLEL_CONVERSIONS_OPTIONS,
)


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
    from tests.conftest import get_valid_threading_test_values
    
    manager = Mock(spec=SettingsManager)
    # Get valid values for current environment
    valid_downloads, valid_conversions = get_valid_threading_test_values()
    
    # Return default values for common settings keys
    def mock_get(key, default=None):
        defaults = {
            "default_download_directory": None,
            "default_audio_format": "MP3",
            SETTING_MAX_PARALLEL_DOWNLOADS: valid_downloads,
            SETTING_MAX_PARALLEL_CONVERSIONS: valid_conversions,
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


@pytest.mark.qt
class TestSettingsDialogThreadingSettings:
    """Test cases for threading settings in settings dialog."""

    def test_threading_settings_widgets_created_pro_user(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test that threading settings widgets are created for Pro users."""
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Threading combo boxes should exist
        assert hasattr(dialog, 'parallel_downloads_combo')
        assert hasattr(dialog, 'parallel_conversions_combo')
        
        # Should be enabled for Pro users
        assert dialog.parallel_downloads_combo.isEnabled()
        assert dialog.parallel_conversions_combo.isEnabled()
        
        # Should be registered as Pro widgets
        assert dialog.parallel_downloads_combo in dialog._pro_widgets
        assert dialog.parallel_conversions_combo in dialog._pro_widgets

    def test_threading_settings_widgets_created_free_user(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test that threading settings widgets are created but disabled for free users."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Threading combo boxes should exist
        assert hasattr(dialog, 'parallel_downloads_combo')
        assert hasattr(dialog, 'parallel_conversions_combo')
        
        # Should be disabled for free users
        assert not dialog.parallel_downloads_combo.isEnabled()
        assert not dialog.parallel_conversions_combo.isEnabled()

    def test_parallel_downloads_combo_options(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test that parallel downloads combo has correct options."""
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        combo = dialog.parallel_downloads_combo
        
        # Should have options matching constants
        assert combo.count() == len(PARALLEL_DOWNLOADS_OPTIONS)
        for i, option in enumerate(PARALLEL_DOWNLOADS_OPTIONS):
            assert combo.itemText(i) == str(option)
        
        # Default should match constant
        assert combo.currentText() == str(DEFAULT_MAX_PARALLEL_DOWNLOADS)

    def test_parallel_conversions_combo_options(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test that parallel conversions combo has correct options.""" 
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        combo = dialog.parallel_conversions_combo
        
        # Should have options matching constants  
        assert combo.count() == len(PARALLEL_CONVERSIONS_OPTIONS)
        for i, option in enumerate(PARALLEL_CONVERSIONS_OPTIONS):
            assert combo.itemText(i) == str(option)
        
        # Default should be a valid option (may not match constant on low-core systems)
        current_text = combo.currentText()
        assert current_text in [str(opt) for opt in PARALLEL_CONVERSIONS_OPTIONS]

    def test_cpu_count_displayed_in_conversions_label(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test that CPU count is displayed in conversions setting label."""
        with patch('app.custom_widgets.dialogs.settings_dialog.cpu_count', 8):
            dialog = SettingsDialog(
                license_manager=pro_license_manager,
                settings_manager=mock_settings_manager
            )
            qtbot.addWidget(dialog)
            
            # Find the label for conversions setting
            form_layout = dialog.pro_group.layout()
            
            # Look for label containing CPU cores text
            found_cpu_text = False
            for i in range(form_layout.rowCount()):
                label_item = form_layout.itemAt(i, form_layout.ItemRole.LabelRole)
                if label_item and hasattr(label_item.widget(), 'text'):
                    label_text = label_item.widget().text()
                    if "CPU cores available: 8" in label_text:
                        found_cpu_text = True
                        break
            
            assert found_cpu_text, "CPU count should be displayed in conversions label"

    def test_threading_settings_load_from_settings_manager(self, qtbot, pro_license_manager):
        """Test that threading settings are loaded from settings manager."""
        from tests.conftest import get_valid_threading_test_values
        
        # Get valid test values for current environment
        valid_downloads, valid_conversions = get_valid_threading_test_values()
        
        # Mock settings manager with specific threading values
        mock_settings = Mock(spec=SettingsManager)
        mock_settings.get.side_effect = lambda key, default=None: {
            "default_download_directory": None,
            "default_audio_format": "MP3",
            SETTING_MAX_PARALLEL_DOWNLOADS: valid_downloads,
            SETTING_MAX_PARALLEL_CONVERSIONS: valid_conversions,
        }.get(key, default)
        mock_settings.set = Mock()
        mock_settings.sync = Mock()
        
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings
        )
        qtbot.addWidget(dialog)
        
        # Threading settings should be loaded correctly
        assert dialog.parallel_downloads_combo.currentText() == str(valid_downloads)
        assert dialog.parallel_conversions_combo.currentText() == str(valid_conversions)

    def test_threading_settings_save_to_settings_manager(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test that threading settings are saved to settings manager."""
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Get available options for current environment
        downloads_options = [dialog.parallel_downloads_combo.itemText(i) for i in range(dialog.parallel_downloads_combo.count())]
        conversions_options = [dialog.parallel_conversions_combo.itemText(i) for i in range(dialog.parallel_conversions_combo.count())]
        
        # Change to valid values (ensure they exist in the combo)
        new_downloads = downloads_options[-1] if len(downloads_options) > 1 else downloads_options[0]  # Use last or first option
        new_conversions = conversions_options[-1] if len(conversions_options) > 1 else conversions_options[0]  # Use last or first option
        
        dialog.parallel_downloads_combo.setCurrentText(new_downloads)
        dialog.parallel_conversions_combo.setCurrentText(new_conversions)
        
        # Click OK button
        ok_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)
        
        # Threading settings should be saved
        from unittest.mock import call
        expected_calls = [
            call(SETTING_MAX_PARALLEL_DOWNLOADS, int(new_downloads)),
            call(SETTING_MAX_PARALLEL_CONVERSIONS, int(new_conversions)),
        ]
        mock_settings_manager.set.assert_has_calls(expected_calls, any_order=True)

    def test_threading_settings_not_saved_for_free_users(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test that threading settings are not saved for free users."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Change threading settings (though they should be disabled)
        dialog.parallel_downloads_combo.setCurrentText("6")
        dialog.parallel_conversions_combo.setCurrentText("4")
        
        # Click OK button
        ok_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)
        
        # Threading settings should NOT be saved for free users
        mock_settings_manager.set.assert_not_called()

    def test_threading_labels_show_lock_icon_for_free_users(self, qtbot, mock_license_manager, mock_settings_manager):
        """Test that threading setting labels show lock icon for free users."""
        dialog = SettingsDialog(
            license_manager=mock_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Find labels in form layout
        form_layout = dialog.pro_group.layout()
        
        # Check for lock icons in threading labels
        found_downloads_lock = False
        found_conversions_lock = False
        
        for i in range(form_layout.rowCount()):
            label_item = form_layout.itemAt(i, form_layout.ItemRole.LabelRole)
            if label_item and hasattr(label_item.widget(), 'text'):
                label_text = label_item.widget().text()
                if "Max Parallel Downloads:" in label_text and "🔒" in label_text:
                    found_downloads_lock = True
                elif "Max Parallel Conversions" in label_text and "🔒" in label_text:
                    found_conversions_lock = True
        
        assert found_downloads_lock, "Downloads label should show lock icon for free users"
        assert found_conversions_lock, "Conversions label should show lock icon for free users"

    def test_threading_labels_no_lock_icon_for_pro_users(self, qtbot, pro_license_manager, mock_settings_manager):
        """Test that threading setting labels don't show lock icon for Pro users."""
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings_manager
        )
        qtbot.addWidget(dialog)
        
        # Find labels in form layout
        form_layout = dialog.pro_group.layout()
        
        # Check that lock icons are NOT in threading labels for Pro users
        for i in range(form_layout.rowCount()):
            label_item = form_layout.itemAt(i, form_layout.ItemRole.LabelRole)
            if label_item and hasattr(label_item.widget(), 'text'):
                label_text = label_item.widget().text()
                if "Max Parallel Downloads:" in label_text:
                    assert "🔒" not in label_text, "Downloads label should not show lock icon for Pro users"
                elif "Max Parallel Conversions" in label_text:
                    assert "🔒" not in label_text, "Conversions label should not show lock icon for Pro users"

    def test_threading_settings_use_defaults_when_not_set(self, qtbot, pro_license_manager):
        """Test that threading settings use defaults when not set in settings manager."""
        # Mock settings manager that returns None for threading settings
        mock_settings = Mock(spec=SettingsManager)
        mock_settings.get.side_effect = lambda key, default=None: {
            "default_download_directory": None,
            "default_audio_format": "MP3",
            # Threading settings return defaults when not set
            SETTING_MAX_PARALLEL_DOWNLOADS: default,
            SETTING_MAX_PARALLEL_CONVERSIONS: default,
        }.get(key, default)
        mock_settings.set = Mock()
        mock_settings.sync = Mock()
        
        dialog = SettingsDialog(
            license_manager=pro_license_manager,
            settings_manager=mock_settings
        )
        qtbot.addWidget(dialog)
        
        # Should use defaults that are valid for current environment
        downloads_text = dialog.parallel_downloads_combo.currentText()
        conversions_text = dialog.parallel_conversions_combo.currentText()
        
        # Verify they are valid options
        downloads_options = [dialog.parallel_downloads_combo.itemText(i) for i in range(dialog.parallel_downloads_combo.count())]
        conversions_options = [dialog.parallel_conversions_combo.itemText(i) for i in range(dialog.parallel_conversions_combo.count())]
        
        assert downloads_text in downloads_options
        assert conversions_text in conversions_options
        
        # Should be reasonable defaults
        assert int(downloads_text) >= 1
        assert int(conversions_text) >= 1