"""Tests for MainWindow credential re-entry prompt logic.

Verifies the behaviour introduced to handle the case where stored credentials
could not be decrypted on startup (e.g. after an OS update that changed the old
volatile salt). The window should show a one-time informational QMessageBox and
then open GetProDialog so the user can re-enter their license.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_services():
    """Mock all services used by MainWindow to prevent real I/O and GUI dialogs."""
    with (
        patch("app.main_window.settings") as mock_settings,
        patch("app.main_window.license_manager") as mock_license_manager,
        patch("app.main_window.StartupVerificationThread") as mock_thread,
        patch("app.main_window.update_service") as mock_update_service,
        patch("app.main_window.UpdateCheckThread") as mock_update_thread,
    ):
        # Configure license manager mock
        mock_license_manager.is_pro = False
        mock_license_manager.license_status_changed = Mock()
        mock_license_manager.license_status_changed.connect = Mock()

        # Set safe defaults on settings mock.
        # Mock attributes must be assigned explicitly to control truthiness.
        mock_settings.credentials_were_cleared = False  # default: no clearing occurred
        mock_settings.check_updates_on_startup = False  # prevent update-check side effects

        # Prevent actual startup verification thread from running
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        # Prevent real GitHub API calls from update service
        mock_update_service.check_for_updates = Mock(return_value=(None, ""))
        mock_update_thread_instance = Mock()
        mock_update_thread.return_value = mock_update_thread_instance

        yield {
            "settings": mock_settings,
            "license_manager": mock_license_manager,
            "thread": mock_thread_instance,
            "update_service": mock_update_service,
            "update_thread": mock_update_thread_instance,
        }


@pytest.mark.qt
class TestMainWindowCredentialReentry:
    """Tests for the one-time credential re-entry prompt in MainWindow."""

    def test_no_prompt_when_credentials_ok(self, qt_app, mock_services):
        """QMessageBox.exec is NOT called when credentials_were_cleared is False."""
        mock_services["settings"].credentials_were_cleared = False
        with patch("app.main_window.QMessageBox") as mock_msgbox_class:
            mock_msgbox_instance = Mock()
            mock_msgbox_class.return_value = mock_msgbox_instance
            MainWindow()
            mock_msgbox_instance.exec.assert_not_called()

    def test_prompt_shown_when_credentials_cleared(self, qt_app, mock_services):
        """QMessageBox.exec is called exactly once when credentials_were_cleared is True."""
        mock_services["settings"].credentials_were_cleared = True
        with (
            patch("app.main_window.QMessageBox") as mock_msgbox_class,
            patch("app.main_window.GetProDialog"),
        ):
            mock_msgbox_instance = Mock()
            mock_msgbox_class.return_value = mock_msgbox_instance
            MainWindow()
            mock_msgbox_instance.exec.assert_called_once()

    def test_get_pro_dialog_opened_after_prompt(self, qt_app, mock_services):
        """GetProDialog is instantiated after the re-entry message box when credentials cleared."""
        mock_services["settings"].credentials_were_cleared = True
        with (
            patch("app.main_window.QMessageBox") as mock_msgbox_class,
            patch("app.main_window.GetProDialog") as mock_get_pro_dialog_class,
        ):
            mock_msgbox_class.return_value = Mock()
            MainWindow()
            mock_get_pro_dialog_class.assert_called()

    def test_no_get_pro_dialog_when_credentials_ok(self, qt_app, mock_services):
        """GetProDialog is NOT opened from the reentry path when credentials are intact."""
        mock_services["settings"].credentials_were_cleared = False
        with patch("app.main_window.GetProDialog") as mock_get_pro_dialog_class:
            MainWindow()
            mock_get_pro_dialog_class.assert_not_called()
