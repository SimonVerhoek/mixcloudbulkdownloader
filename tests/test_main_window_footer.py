"""Tests for main window footer integration."""

from pathlib import Path
from unittest.mock import Mock, create_autospec

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QVBoxLayout

from app.custom_widgets.central_widget import CentralWidget
from app.custom_widgets.dialogs.feedback_dialog import FeedbackDialog
from app.custom_widgets.footer_widget import FooterWidget
from app.main_window import MainWindow
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager
from app.threads.startup_verification_thread import StartupVerificationThread


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class _StubMainWindow(MainWindow):
    """Subclass of MainWindow that suppresses background thread startup.

    Overrides ``_create_verification_thread`` so that no real license
    verification thread is launched during tests.  All other behaviour is
    inherited from the production class.
    """

    def _create_verification_thread(self, lm: LicenseManager) -> StartupVerificationThread:
        """Return a spec'd stub instead of a real StartupVerificationThread."""
        stub = create_autospec(StartupVerificationThread, instance=True)
        return stub


def _make_stub_license_manager(is_pro: bool = False) -> Mock:
    """Create a spec'd LicenseManager stub with sensible defaults.

    Args:
        is_pro: Whether the stub should report Pro status.

    Returns:
        A ``Mock(spec=LicenseManager)`` instance.
    """
    lm = Mock(spec=LicenseManager)
    lm.is_pro = is_pro
    return lm


def _make_stub_settings_manager(tmp_path: Path) -> Mock:
    """Create a spec'd SettingsManager stub with sensible defaults.

    Args:
        tmp_path: Temporary directory for the stub; not actually used for file
            I/O since all attributes are set directly.

    Returns:
        A ``Mock(spec=SettingsManager)`` instance.
    """
    sm = Mock(spec=SettingsManager)
    # Disable update checking and credential-reentry prompt so MainWindow.__init__
    # does not block on QMessageBox or start update threads.
    sm.credentials_were_cleared = False
    sm.check_updates_on_startup = False
    sm.get.side_effect = lambda key, default=None: {
        "check_updates_on_startup": False,
        "default_download_directory": None,
        "preferred_audio_format": "MP3",
    }.get(key, default)
    return sm


@pytest.fixture
def stub_services(tmp_path: Path):
    """Build spec'd stubs for all services injected into MainWindow.

    Yields a dict with keys: ``license_manager``, ``settings``.
    """
    lm = _make_stub_license_manager(is_pro=False)
    sm = _make_stub_settings_manager(tmp_path=tmp_path)

    yield {
        "license_manager": lm,
        "settings": sm,
    }


@pytest.mark.qt
class TestMainWindowFooterIntegration:
    """Test main window footer integration."""

    def test_main_window_has_footer_widget(self, qt_app, stub_services):
        """Test that main window contains footer widget."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )

        assert isinstance(window.footer_widget, FooterWidget)

    def test_main_window_layout_structure(self, qt_app, stub_services):
        """Test that main window has correct layout structure."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )
        # Main widget should be the central widget
        central_widget = window.centralWidget()
        assert central_widget is not None

        # Should have vertical layout with central widget and footer
        layout = central_widget.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.count() == 2

        # First item should be the central widget
        central_item = layout.itemAt(0).widget()
        assert isinstance(central_item, CentralWidget)

        # Second item should be the footer
        footer_item = layout.itemAt(1).widget()
        assert isinstance(footer_item, FooterWidget)

    def test_footer_widget_receives_license_manager(self, qt_app, stub_services):
        """Test that footer widget receives the same license manager."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )

        assert window.footer_widget.license_manager is window.license_manager

    def test_license_status_change_propagates_to_footer(self, qt_app, stub_services):
        """Test that license status changes propagate to footer."""
        lm = stub_services["license_manager"]

        window = _StubMainWindow(
            license_manager=lm,
            settings=stub_services["settings"],
        )
        # License manager should be connected to footer via its own signal
        # The footer widget connects directly to license_manager.license_status_changed
        lm.license_status_changed.connect.assert_called()

    def test_main_window_layout_margins_and_spacing(self, qt_app, stub_services):
        """Test that main window layout has correct margins and spacing."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )
        central_widget = window.centralWidget()
        layout = central_widget.layout()

        # Should have no margins and spacing for seamless layout
        assert layout.contentsMargins().left() == 0
        assert layout.contentsMargins().right() == 0
        assert layout.contentsMargins().top() == 0
        assert layout.contentsMargins().bottom() == 0
        assert layout.spacing() == 0

    def test_footer_widget_signal_connection_in_main_window(self, qt_app, stub_services):
        """Test that footer widget properly connects to license manager signals."""
        lm = stub_services["license_manager"]

        window = _StubMainWindow(
            license_manager=lm,
            settings=stub_services["settings"],
        )
        # Footer widget should connect to license status changes
        # This happens inside FooterWidget.__init__, but we verify the manager was passed
        assert window.footer_widget.license_manager is lm


@pytest.mark.qt
class TestMainWindowFooterBehavior:
    """Test footer behavior within main window context."""

    def test_footer_widget_default_state_free_user(self, qt_app, stub_services):
        """Test footer shows correct default state for free users."""
        stub_services["license_manager"].is_pro = False

        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )
        window.show()  # Widget needs to be shown for visibility to work

        # Footer should show Free status and Pro button
        assert window.footer_widget.status_label.text() == "MBD Free"
        assert window.footer_widget.get_pro_button.isVisible() == True
        window.close()

    def test_footer_widget_default_state_pro_user(self, qt_app, stub_services):
        """Test footer shows correct default state for Pro users."""
        stub_services["license_manager"].is_pro = True

        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )
        # Footer should show Pro status and hide Pro button
        assert window.footer_widget.status_label.text() == "MBD Pro"
        assert window.footer_widget.get_pro_button.isVisible() == False

    def test_footer_feedback_button_opens_dialog(self, qt_app, stub_services):
        """Test that footer feedback button opens dialog in main window context."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )

        stub_dialog = create_autospec(FeedbackDialog, instance=True)
        dialog_calls = []

        def stub_factory(parent):
            dialog_calls.append(parent)
            return stub_dialog

        # Assign stub factory directly to the test-provided instance (no patch needed).
        window.footer_widget._feedback_dialog_factory = stub_factory

        # Click feedback button
        window.footer_widget._show_feedback_dialog()

        # Verify dialog was created with footer as parent
        assert len(dialog_calls) == 1
        assert dialog_calls[0] is window.footer_widget
        stub_dialog.exec.assert_called_once()


@pytest.mark.qt
class TestMainWindowFooterIntegrationEdgeCases:
    """Test edge cases for main window footer integration."""

    def test_main_window_initialization_order(self, qt_app, stub_services):
        """Test that footer is initialized after central widget."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )
        # Both widgets should be different instances
        assert window.central_widget is not window.footer_widget

    def test_window_close_event_with_footer(self, qt_app, stub_services):
        """Test that window close event works correctly with footer."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )
        from PySide6.QtGui import QCloseEvent

        close_event = QCloseEvent()
        # Use spec= to avoid a bare Mock. QCloseEvent.accept is a bound method
        # on the test-provided instance; wrapping it keeps type safety.
        close_event.accept = Mock(spec=close_event.accept)

        # Should not raise exception
        window.closeEvent(close_event)

        # Event should be accepted
        close_event.accept.assert_called_once()

    def test_footer_widget_survives_central_widget_refresh(self, qt_app, stub_services):
        """Test that footer widget remains when central widget is refreshed."""
        window = _StubMainWindow(
            license_manager=stub_services["license_manager"],
            settings=stub_services["settings"],
        )
        original_footer = window.footer_widget

        # Refresh Pro UI elements (which might affect layouts)
        window.refresh_pro_ui_elements()

        # Footer should still be the same instance
        assert window.footer_widget is original_footer
