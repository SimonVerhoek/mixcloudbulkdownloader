"""Tests for MainWindow credential re-entry prompt logic.

Verifies the behaviour introduced to handle the case where stored credentials
could not be decrypted on startup (e.g. after an OS update that changed the old
volatile salt). The window should show a one-time informational QMessageBox and
then open GetProDialog so the user can re-enter their license.
"""

from collections.abc import Callable
from unittest.mock import MagicMock, Mock, create_autospec

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.main_window import MainWindow
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager
from app.services.update_service import UpdateService
from app.threads.startup_verification_thread import StartupVerificationThread
from app.threads.update_check_thread import UpdateCheckThread


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class StubVerificationThread:
    """Stub for StartupVerificationThread that does not start a real thread."""

    def __init__(self, license_manager, parent=None) -> None:
        """Initialise stub without starting a thread."""
        self.license_manager = license_manager
        self.parent = parent
        self.started = False

    def start(self) -> None:
        """Record that start was called without running anything."""
        self.started = True

    def isRunning(self) -> bool:
        """Always report not running."""
        return False

    def terminate(self) -> None:
        """No-op termination."""

    def wait(self, timeout: int = 0) -> bool:
        """No-op wait."""
        return True


class StubUpdateCheckThread:
    """Stub for UpdateCheckThread that does not start a real thread."""

    def __init__(self, update_service_instance=None) -> None:
        """Initialise stub without starting a thread."""
        self.update_service_instance = update_service_instance
        self.started = False
        # Provide stub signal objects so .connect() calls do not crash
        self.update_available = _StubSignal()
        self.no_update_available = _StubSignal()
        self.error_signal = _StubSignal()

    def start(self) -> None:
        """Record that start was called without running anything."""
        self.started = True

    def isRunning(self) -> bool:
        """Always report not running."""
        return False

    def stop(self) -> None:
        """No-op stop."""


class _StubSignal:
    """Minimal signal stub that records connect() calls but does nothing."""

    def connect(self, slot: Callable) -> None:
        """Accept a slot connection without wiring anything."""

    def emit(self, *args) -> None:
        """Accept an emit call without invoking anything."""


class StubMessageBox:
    """Stub QMessageBox that records exec() calls without showing a dialog."""

    def __init__(self, parent=None) -> None:
        """Initialise stub."""
        self.parent = parent
        self.exec_count = 0
        self._title = ""
        self._text = ""
        self._icon = None
        self._buttons = None

    def setWindowTitle(self, title: str) -> None:
        """Record window title."""
        self._title = title

    def setIcon(self, icon) -> None:
        """Record icon."""
        self._icon = icon

    def setText(self, text: str) -> None:
        """Record text."""
        self._text = text

    def setStandardButtons(self, buttons) -> None:
        """Record buttons."""
        self._buttons = buttons

    def exec(self) -> int:
        """Record that exec was called and return QDialog.Accepted."""
        self.exec_count += 1
        return 1  # QDialog.Accepted


class StubGetProDialog:
    """Stub GetProDialog that records exec() calls without showing a dialog."""

    # Track how many times the class was instantiated
    instance_count = 0

    def __init__(self, parent=None) -> None:
        """Initialise stub."""
        StubGetProDialog.instance_count += 1
        self.parent = parent
        self.exec_count = 0

    def exec(self) -> int:
        """Record that exec was called and return QDialog.Rejected."""
        self.exec_count += 1
        return 0  # QDialog.Rejected

    @classmethod
    def reset(cls) -> None:
        """Reset the instance counter before a test."""
        cls.instance_count = 0


class StubUpdateService:
    """Stub update service that never makes network calls."""

    def check_for_updates(self):
        """Return no update available."""
        return None, ""


class _TestableMainWindow(MainWindow):
    """MainWindow subclass that replaces all GUI/thread side-effects with stubs.

    All factory methods are overridden to return controllable stubs instead of
    real Qt widgets or threads.  This allows tests to exercise the initialisation
    logic without a display, real network calls, or real background threads.
    """

    def __init__(
        self,
        license_manager=None,
        settings=None,
        update_svc=None,
        msgbox_stub: StubMessageBox | None = None,
        pro_dialog_stub_class=None,
    ) -> None:
        """Initialise with pre-configured stubs.

        Args:
            license_manager: Optional license manager stub.
            settings: Optional settings manager stub.
            update_svc: Optional update service stub.
            msgbox_stub: Optional pre-built message box stub.  When *None* a fresh
                ``StubMessageBox`` is created for each call to ``_create_qmessagebox``.
            pro_dialog_stub_class: Optional class to instantiate for ``_create_pro_dialog``.
                Defaults to ``StubGetProDialog``.
        """
        self._msgbox_stub = msgbox_stub
        self._pro_dialog_stub_class = pro_dialog_stub_class or StubGetProDialog
        super().__init__(
            license_manager=license_manager,
            settings=settings,
            update_svc=update_svc,
        )

    def _create_verification_thread(self, lm):
        """Return a stub verification thread instead of a real QThread."""
        return StubVerificationThread(license_manager=lm, parent=self)

    def _create_qmessagebox(self, parent=None):
        """Return the configured stub message box."""
        if self._msgbox_stub is not None:
            return self._msgbox_stub
        return StubMessageBox(parent=parent)

    def _create_pro_dialog(self, parent=None):
        """Return a stub pro dialog."""
        return self._pro_dialog_stub_class(parent=parent)

    def _run_update_check(self, is_startup: bool) -> None:
        """No-op override: prevents real update checks during tests."""


def _make_stub_settings(
    credentials_were_cleared: bool = False,
    check_updates_on_startup: bool = False,
) -> SettingsManager:
    """Create a MagicMock with spec=SettingsManager and sensible defaults.

    Args:
        credentials_were_cleared: Value for ``credentials_were_cleared`` property.
        check_updates_on_startup: Value for ``check_updates_on_startup`` property.

    Returns:
        A ``MagicMock`` spec'd to ``SettingsManager`` with the given defaults.
    """
    stub = MagicMock(spec=SettingsManager)
    stub.credentials_were_cleared = credentials_were_cleared
    stub.check_updates_on_startup = check_updates_on_startup
    stub.default_download_directory = None
    return stub


def _make_stub_license_manager(is_pro: bool = False) -> MagicMock:
    """Create a MagicMock with spec=LicenseManager.

    Args:
        is_pro: Initial ``is_pro`` value.

    Returns:
        A ``MagicMock`` spec'd to ``LicenseManager``.
    """
    stub = MagicMock(spec=LicenseManager)
    stub.is_pro = is_pro
    # Make license_status_changed a stub signal so .connect() calls succeed
    stub.license_status_changed = _StubSignal()
    return stub


@pytest.mark.qt
class TestMainWindowCredentialReentry:
    """Tests for the one-time credential re-entry prompt in MainWindow."""

    def test_no_prompt_when_credentials_ok(self, qt_app):
        """QMessageBox.exec is NOT called when credentials_were_cleared is False."""
        settings = _make_stub_settings(credentials_were_cleared=False)
        license_mgr = _make_stub_license_manager()
        msgbox_stub = StubMessageBox()

        _TestableMainWindow(
            settings=settings,
            license_manager=license_mgr,
            update_svc=StubUpdateService(),
            msgbox_stub=msgbox_stub,
        )

        assert msgbox_stub.exec_count == 0

    def test_prompt_shown_when_credentials_cleared(self, qt_app):
        """QMessageBox.exec is called exactly once when credentials_were_cleared is True."""
        settings = _make_stub_settings(credentials_were_cleared=True)
        license_mgr = _make_stub_license_manager()
        msgbox_stub = StubMessageBox()

        StubGetProDialog.reset()
        _TestableMainWindow(
            settings=settings,
            license_manager=license_mgr,
            update_svc=StubUpdateService(),
            msgbox_stub=msgbox_stub,
        )

        assert msgbox_stub.exec_count == 1

    def test_get_pro_dialog_opened_after_prompt(self, qt_app):
        """GetProDialog is instantiated after the re-entry message box when credentials cleared."""
        settings = _make_stub_settings(credentials_were_cleared=True)
        license_mgr = _make_stub_license_manager()

        StubGetProDialog.reset()
        _TestableMainWindow(
            settings=settings,
            license_manager=license_mgr,
            update_svc=StubUpdateService(),
        )

        assert StubGetProDialog.instance_count >= 1

    def test_no_get_pro_dialog_when_credentials_ok(self, qt_app):
        """GetProDialog is NOT opened from the reentry path when credentials are intact."""
        settings = _make_stub_settings(credentials_were_cleared=False)
        license_mgr = _make_stub_license_manager()

        StubGetProDialog.reset()
        _TestableMainWindow(
            settings=settings,
            license_manager=license_mgr,
            update_svc=StubUpdateService(),
        )

        assert StubGetProDialog.instance_count == 0
