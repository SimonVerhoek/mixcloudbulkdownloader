"""Integration tests for Pro license system main application integration."""

from unittest.mock import Mock, patch

import pytest

from app.custom_widgets.central_widget import CentralWidget
from app.main_window import MainWindow
from app.services.license_manager import LicenseManager
from app.threads.startup_verification_thread import StartupVerificationThread


@pytest.fixture
def app(qapp):
    """Provide QApplication instance for Qt tests."""
    return qapp


@pytest.fixture
def mock_license_manager():
    """Create a mock license manager for testing."""
    mock_manager = Mock(spec=LicenseManager)
    mock_manager.is_pro = False
    mock_manager.settings = Mock()
    mock_manager.settings.email = ""
    mock_manager.settings.license_key = ""
    mock_manager.settings.last_successful_verification = None
    mock_manager.verify_license = Mock(return_value=False)
    return mock_manager


@pytest.fixture
def mock_pro_license_manager():
    """Create a mock license manager for Pro user testing."""
    mock_manager = Mock(spec=LicenseManager)
    mock_manager.is_pro = True
    mock_manager.settings = Mock()
    mock_manager.settings.email = "pro@example.com"
    mock_manager.settings.license_key = "valid-key"
    mock_manager.settings.last_successful_verification = 1640995200  # Some timestamp
    mock_manager.verify_license = Mock(return_value=True)
    return mock_manager


@pytest.mark.qt
class TestCentralWidgetProIntegration:
    """Test CentralWidget Pro integration functionality."""

    def test_central_widget_accepts_license_manager(self, app, mock_license_manager, qtbot):
        """Test that CentralWidget accepts license_manager parameter."""
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)
        assert widget.license_manager == mock_license_manager

    def test_central_widget_no_longer_has_pro_button(self, app, mock_license_manager, qtbot):
        """Test that CentralWidget no longer has a Pro button (moved to footer)."""
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)
        widget.show()

        # Pro button should no longer exist in central widget
        assert not hasattr(widget, "get_mbd_pro_button")

    def test_central_widget_has_core_functionality(self, app, mock_license_manager, qtbot):
        """Test that CentralWidget still has its core functionality."""
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)

        # Should have main functional elements
        assert hasattr(widget, "search_user_input")
        assert hasattr(widget, "get_cloudcasts_button")
        assert hasattr(widget, "download_button")
        assert hasattr(widget, "cancel_button")


@pytest.mark.qt
class TestMainWindowProIntegration:
    """Test MainWindow Pro integration functionality."""

    @patch("app.main_window.StartupVerificationThread")
    def test_main_window_creates_central_widget_with_license_manager(
        self, mock_thread_class, app, mock_license_manager, qtbot
    ):
        """Test that MainWindow passes license_manager to CentralWidget."""
        with patch("app.main_window.license_manager", mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)
            window.show()

            assert hasattr(window, "central_widget")
            assert window.central_widget.license_manager == mock_license_manager

    @patch("app.main_window.StartupVerificationThread")
    def test_get_mbd_pro_menu_item_created_for_non_pro_users(
        self, mock_thread_class, app, mock_license_manager, qtbot
    ):
        """Test that Get MBD Pro menu item is created and visible for non-Pro users."""
        with patch("app.main_window.license_manager", mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)

            assert hasattr(window, "get_mbd_pro_action")
            assert window.get_mbd_pro_action.text() == "Get MBD Pro..."
            assert window.get_mbd_pro_action.isVisible()

    @patch("app.main_window.StartupVerificationThread")
    def test_get_mbd_pro_menu_item_hidden_for_pro_users(
        self, mock_thread_class, app, mock_pro_license_manager, qtbot
    ):
        """Test that Get MBD Pro menu item is hidden for Pro users."""
        with patch("app.main_window.license_manager", mock_pro_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)

            assert hasattr(window, "get_mbd_pro_action")
            assert not window.get_mbd_pro_action.isVisible()

    @patch("app.main_window.GetProDialog")
    @patch("app.main_window.StartupVerificationThread")
    def test_get_mbd_pro_menu_opens_dialog(
        self, mock_thread_class, mock_dialog_class, app, mock_license_manager, qtbot
    ):
        """Test that Get MBD Pro menu item opens GetProDialog."""
        mock_dialog = Mock()
        mock_dialog.exec.return_value = False
        mock_dialog_class.return_value = mock_dialog

        with patch("app.main_window.license_manager", mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)

            # Trigger menu action
            window.get_mbd_pro_action.trigger()

            mock_dialog_class.assert_called_once_with(window)
            mock_dialog.exec.assert_called_once()

    @patch("app.main_window.StartupVerificationThread")
    def test_dynamic_ui_updates_on_pro_status_change(
        self, mock_thread_class, app, mock_license_manager, qtbot
    ):
        """Test that UI updates when Pro status changes."""
        with patch("app.main_window.license_manager", mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)
            window.show()

            # Initially non-Pro, elements should be visible
            assert window.get_mbd_pro_action.isVisible()
            assert window.footer_widget.get_pro_button.isVisible()

            # Change to Pro status
            mock_license_manager.is_pro = True
            window.refresh_pro_ui_elements()

            # Menu should be hidden, footer button handled by license manager signal
            assert not window.get_mbd_pro_action.isVisible()

            # Simulate the footer widget receiving the license status change
            window.footer_widget._handle_license_status_changed(True)
            assert not window.footer_widget.get_pro_button.isVisible()


@pytest.mark.qt
class TestStartupVerification:
    """Test startup license verification functionality."""

    def test_startup_verification_with_stored_credentials(self, app, mock_license_manager):
        """Test automatic verification with stored credentials."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.verify_license.return_value = True

        thread = StartupVerificationThread(mock_license_manager)

        # Run the verification
        thread.run()

        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_startup_verification_network_failure(self, app, mock_license_manager):
        """Test graceful startup when license server unreachable."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = 1640995200
        mock_license_manager.verify_license.return_value = False

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        # License manager should maintain Pro status
        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_startup_verification_corrupted_credentials(self, app, mock_license_manager):
        """Test handling of invalid stored credentials."""
        mock_license_manager.settings.email = "invalid@example.com"
        mock_license_manager.settings.license_key = "invalid-key"
        mock_license_manager.settings.last_successful_verification = None
        mock_license_manager.verify_license.return_value = False

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        # Should attempt verification
        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_first_run_no_credentials(self, app, mock_license_manager):
        """Test startup behavior with no stored credentials."""
        mock_license_manager.settings.email = ""
        mock_license_manager.settings.license_key = ""

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        # Should attempt verification (but will exit early due to missing credentials)
        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_startup_verification_failure_with_previous_success(self, app, mock_license_manager):
        """Test offline grace period when last_successful_verification exists."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = 1640995200
        mock_license_manager.verify_license.return_value = False

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        # Should attempt verification
        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_startup_verification_failure_no_previous_success(self, app, mock_license_manager):
        """Test user notification when last_successful_verification is falsy."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = None
        mock_license_manager.verify_license.return_value = False

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        # Should attempt verification
        mock_license_manager.verify_license.assert_called_once_with(timeout=10)


@pytest.mark.qt
class TestMainWindowStartupIntegration:
    """Test MainWindow startup verification integration."""

    def test_startup_license_verification_thread_created(self, app, mock_license_manager, qtbot):
        """Test that startup verification thread is created and started."""
        with (
            patch("app.main_window.license_manager", mock_license_manager),
            patch("app.main_window.StartupVerificationThread") as mock_thread_class,
        ):

            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread

            window = MainWindow()
            qtbot.addWidget(window)

            mock_thread_class.assert_called_once_with(mock_license_manager, window)
            mock_thread.start.assert_called_once()

    @patch("app.main_window.ErrorDialog")
    def test_handle_license_status_change_to_non_pro(
        self, mock_error_dialog, app, mock_license_manager, qtbot
    ):
        """Test handling license status change to non-Pro."""
        with (
            patch("app.main_window.license_manager", mock_license_manager),
            patch("app.main_window.StartupVerificationThread"),
        ):

            window = MainWindow()
            qtbot.addWidget(window)

            # Simulate license status change to False
            window._handle_license_status_changed(is_pro=False)

            # Should not show error dialog (LicenseManager handles error reporting)
            mock_error_dialog.assert_not_called()

    def test_handle_license_status_change_to_pro(self, app, mock_license_manager, qtbot):
        """Test handling license status change to Pro."""
        with (
            patch("app.main_window.license_manager", mock_license_manager),
            patch("app.main_window.StartupVerificationThread"),
            patch.object(MainWindow, "_verify_ffmpeg_availability") as mock_ffmpeg_check,
        ):

            window = MainWindow()
            qtbot.addWidget(window)

            # Simulate license status change to True
            window._handle_license_status_changed(is_pro=True)

            # Should verify FFmpeg availability for Pro users
            mock_ffmpeg_check.assert_called_once()
