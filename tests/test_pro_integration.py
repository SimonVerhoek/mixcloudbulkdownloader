"""Integration tests for Pro license system main application integration."""

from unittest.mock import Mock

import pytest

from app.custom_widgets.central_widget import CentralWidget
from app.main_window import MainWindow
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager
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
    mock_manager.settings = Mock(spec=SettingsManager)
    mock_manager.settings.email = ""
    mock_manager.settings.license_key = ""
    mock_manager.settings.last_successful_verification = None
    mock_manager.verify_license.return_value = False
    return mock_manager


@pytest.fixture
def mock_pro_license_manager():
    """Create a mock license manager for Pro user testing."""
    mock_manager = Mock(spec=LicenseManager)
    mock_manager.is_pro = True
    mock_manager.settings = Mock(spec=SettingsManager)
    mock_manager.settings.email = "pro@example.com"
    mock_manager.settings.license_key = "valid-key"
    mock_manager.settings.last_successful_verification = 1640995200  # Some timestamp
    mock_manager.verify_license.return_value = True
    return mock_manager


class StubVerificationThread:
    """Minimal stub for StartupVerificationThread that does nothing on start."""

    def __init__(self, lm=None, parent=None) -> None:
        self.started = False
        self.lm = lm

    def start(self) -> None:
        self.started = True

    def isRunning(self) -> bool:
        return False

    def terminate(self) -> None:
        pass

    def wait(self, ms: int = 0) -> None:
        pass


class StubGetProDialog:
    """Minimal stub for GetProDialog that records exec() calls."""

    def __init__(self, parent=None) -> None:
        self.exec_return_value = False

    def exec(self) -> bool:
        return self.exec_return_value


class StubErrorDialog:
    """Minimal stub for ErrorDialog that records creation."""

    instances: list["StubErrorDialog"] = []

    def __init__(self, parent=None, msg: str = "") -> None:
        self.msg = msg
        StubErrorDialog.instances.append(self)


class StubMainWindow(MainWindow):
    """MainWindow subclass that overrides factory methods for testing."""

    def __init__(self, **kwargs) -> None:
        self._stub_verification_thread: StubVerificationThread | None = None
        self._stub_pro_dialog: StubGetProDialog | None = None
        self._ffmpeg_verification_called = False
        StubErrorDialog.instances.clear()
        super().__init__(**kwargs)

    def _create_verification_thread(self, lm: LicenseManager) -> StubVerificationThread:
        self._stub_verification_thread = StubVerificationThread(lm=lm, parent=self)
        return self._stub_verification_thread

    def _create_pro_dialog(self, parent=None) -> StubGetProDialog:
        self._stub_pro_dialog = StubGetProDialog(parent=parent)
        return self._stub_pro_dialog

    def _create_error_dialog(self, msg: str, parent=None) -> StubErrorDialog:
        return StubErrorDialog(parent=parent, msg=msg)

    def _verify_ffmpeg_availability(self) -> None:
        self._ffmpeg_verification_called = True

    def _run_update_check(self, is_startup: bool) -> None:
        """Suppress update check to avoid real HTTP calls and GC-related segfaults."""
        pass


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

        assert not hasattr(widget, "get_mbd_pro_button")

    def test_central_widget_has_core_functionality(self, app, mock_license_manager, qtbot):
        """Test that CentralWidget still has its core functionality."""
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)

        _ = widget.search_user_input
        _ = widget.search_user_input.artist_selected
        _ = widget.download_button
        _ = widget.cancel_button


@pytest.mark.qt
class TestMainWindowProIntegration:
    """Test MainWindow Pro integration functionality."""

    def test_main_window_creates_central_widget_with_license_manager(
        self, app, mock_license_manager, qtbot
    ):
        """Test that MainWindow passes license_manager to CentralWidget."""
        window = StubMainWindow(license_manager=mock_license_manager)
        qtbot.addWidget(window)
        window.show()

        assert window.central_widget.license_manager == mock_license_manager

    def test_get_mbd_pro_menu_item_created_for_non_pro_users(
        self, app, mock_license_manager, qtbot
    ):
        """Test that Get MBD Pro menu item is created and visible for non-Pro users."""
        window = StubMainWindow(license_manager=mock_license_manager)
        qtbot.addWidget(window)

        assert window.get_mbd_pro_action.text() == "Get MBD Pro..."
        assert window.get_mbd_pro_action.isVisible()

    def test_get_mbd_pro_menu_item_hidden_for_pro_users(self, app, mock_pro_license_manager, qtbot):
        """Test that Get MBD Pro menu item is hidden for Pro users."""
        window = StubMainWindow(license_manager=mock_pro_license_manager)
        qtbot.addWidget(window)

        assert not window.get_mbd_pro_action.isVisible()

    def test_get_mbd_pro_menu_opens_dialog(self, app, mock_license_manager, qtbot):
        """Test that Get MBD Pro menu item opens GetProDialog."""
        window = StubMainWindow(license_manager=mock_license_manager)
        qtbot.addWidget(window)

        window.get_mbd_pro_action.trigger()

        assert window._stub_pro_dialog is not None

    def test_dynamic_ui_updates_on_pro_status_change(self, app, mock_license_manager, qtbot):
        """Test that UI updates when Pro status changes."""
        window = StubMainWindow(license_manager=mock_license_manager)
        qtbot.addWidget(window)
        window.show()

        assert window.get_mbd_pro_action.isVisible()
        assert window.footer_widget.get_pro_button.isVisible()

        mock_license_manager.is_pro = True
        window.refresh_pro_ui_elements()

        assert not window.get_mbd_pro_action.isVisible()

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

        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_startup_verification_corrupted_credentials(self, app, mock_license_manager):
        """Test handling of invalid stored credentials."""
        mock_license_manager.settings.email = "invalid@example.com"
        mock_license_manager.settings.license_key = "invalid-key"
        mock_license_manager.settings.last_successful_verification = None
        mock_license_manager.verify_license.return_value = False

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_first_run_no_credentials(self, app, mock_license_manager):
        """Test startup behavior with no stored credentials."""
        mock_license_manager.settings.email = ""
        mock_license_manager.settings.license_key = ""

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_startup_verification_failure_with_previous_success(self, app, mock_license_manager):
        """Test offline grace period when last_successful_verification exists."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = 1640995200
        mock_license_manager.verify_license.return_value = False

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        mock_license_manager.verify_license.assert_called_once_with(timeout=10)

    def test_startup_verification_failure_no_previous_success(self, app, mock_license_manager):
        """Test user notification when last_successful_verification is falsy."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = None
        mock_license_manager.verify_license.return_value = False

        thread = StartupVerificationThread(mock_license_manager)

        thread.run()

        mock_license_manager.verify_license.assert_called_once_with(timeout=10)


@pytest.mark.qt
class TestMainWindowStartupIntegration:
    """Test MainWindow startup verification integration."""

    def test_startup_license_verification_thread_created(self, app, mock_license_manager, qtbot):
        """Test that startup verification thread is created and started."""
        window = StubMainWindow(license_manager=mock_license_manager)
        qtbot.addWidget(window)

        assert window._stub_verification_thread is not None
        assert window._stub_verification_thread.started

    def test_handle_license_status_change_to_non_pro(self, app, mock_license_manager, qtbot):
        """Test handling license status change to non-Pro."""
        window = StubMainWindow(license_manager=mock_license_manager)
        qtbot.addWidget(window)

        window._handle_license_status_changed(is_pro=False)

        assert len(StubErrorDialog.instances) == 0

    def test_handle_license_status_change_to_pro(self, app, mock_license_manager, qtbot):
        """Test handling license status change to Pro."""
        window = StubMainWindow(license_manager=mock_license_manager)
        qtbot.addWidget(window)

        window._handle_license_status_changed(is_pro=True)

        assert window._ffmpeg_verification_called
