"""Tests for footer widget functionality."""

from unittest.mock import Mock, create_autospec

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from app.custom_widgets.dialogs.feedback_dialog import FeedbackDialog
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.custom_widgets.footer_widget import FooterWidget
from app.services.license_manager import LicenseManager


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_license_manager():
    """Mock license manager for testing."""
    mock = Mock(spec=LicenseManager)
    mock.is_pro = False
    return mock


@pytest.mark.qt
class TestFooterWidget:
    """Test cases for FooterWidget functionality."""

    def test_footer_widget_initialization(self, qt_app, mock_license_manager):
        """Test footer widget initializes correctly."""
        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.objectName() == "footerWidget"
        assert widget.license_manager is mock_license_manager
        _ = widget.status_label
        _ = widget.get_pro_button
        _ = widget.feedback_button

    def test_footer_widget_layout(self, qt_app, mock_license_manager):
        """Test footer widget layout structure."""
        widget = FooterWidget(license_manager=mock_license_manager)

        layout = widget.layout()
        assert layout is not None
        assert (
            layout.count() == 5
        )  # status_label, stretch, get_pro_button, stretch, feedback_button

    def test_status_label_free_user(self, qt_app, mock_license_manager):
        """Test status label shows 'MBD Free' for non-Pro users."""
        mock_license_manager.is_pro = False

        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.status_label.text() == "MBD Free"
        assert widget.status_label.objectName() == "statusLabel"

    def test_status_label_pro_user(self, qt_app, mock_license_manager):
        """Test status label shows 'MBD Pro' for Pro users."""
        mock_license_manager.is_pro = True

        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.status_label.text() == "MBD Pro"

    def test_feedback_button_properties(self, qt_app, mock_license_manager):
        """Test feedback button properties."""
        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.feedback_button.text() == "Feedback?"
        assert widget.feedback_button.objectName() == "feedbackButton"

    def test_feedback_button_click_opens_dialog(self, qt_app, mock_license_manager):
        """Test that clicking feedback button opens feedback dialog."""
        stub_dialog = create_autospec(FeedbackDialog, instance=True)
        dialog_calls = []

        def stub_factory(parent):
            dialog_calls.append(parent)
            return stub_dialog

        widget = FooterWidget(
            license_manager=mock_license_manager,
            feedback_dialog_factory=stub_factory,
        )

        # Simulate button click
        widget._show_feedback_dialog()

        # Verify dialog was created and shown
        assert len(dialog_calls) == 1
        assert dialog_calls[0] is widget
        stub_dialog.exec.assert_called_once()

    def test_license_status_change_updates_display(self, qt_app, mock_license_manager):
        """Test that license status changes update the display."""
        mock_license_manager.is_pro = False
        widget = FooterWidget(license_manager=mock_license_manager)

        # Initial state should be Free
        assert widget.status_label.text() == "MBD Free"

        # Simulate Pro upgrade
        mock_license_manager.is_pro = True
        widget._handle_license_status_changed(True)

        assert widget.status_label.text() == "MBD Pro"

        # Simulate downgrade to Free
        mock_license_manager.is_pro = False
        widget._handle_license_status_changed(False)

        assert widget.status_label.text() == "MBD Free"

    def test_license_status_signal_connection(self, qt_app, mock_license_manager):
        """Test that widget connects to license status change signal."""
        widget = FooterWidget(license_manager=mock_license_manager)

        # Verify signal connection was attempted
        mock_license_manager.license_status_changed.connect.assert_called_once()

        # Get the connected slot
        connected_slot = mock_license_manager.license_status_changed.connect.call_args[0][0]
        assert connected_slot == widget._handle_license_status_changed

    def test_footer_widget_default_license_manager(self, qt_app):
        """Test footer widget with default license manager."""
        widget = FooterWidget()

        # Should use the real license manager instance
        from app.services.license_manager import license_manager

        assert widget.license_manager is license_manager

    def test_widget_object_names(self, qt_app, mock_license_manager):
        """Test that all child widgets have proper object names for styling."""
        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.objectName() == "footerWidget"
        assert widget.status_label.objectName() == "statusLabel"
        assert widget.get_pro_button.objectName() == "getMBDProButton"
        assert widget.feedback_button.objectName() == "feedbackButton"

    def test_get_pro_button_properties(self, qt_app, mock_license_manager):
        """Test Get Pro button properties."""
        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.get_pro_button.text() == "Get MBD Pro"
        assert widget.get_pro_button.objectName() == "getMBDProButton"

    def test_get_pro_button_visibility_free_user(self, qt_app, mock_license_manager):
        """Test Get Pro button is visible for free users."""
        mock_license_manager.is_pro = False

        widget = FooterWidget(license_manager=mock_license_manager)
        widget.show()  # Widget needs to be shown for visibility to work

        assert widget.get_pro_button.isVisible() == True

    def test_get_pro_button_visibility_pro_user(self, qt_app, mock_license_manager):
        """Test Get Pro button is hidden for Pro users."""
        mock_license_manager.is_pro = True

        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.get_pro_button.isVisible() == False

    def test_get_pro_button_click_opens_dialog(self, qt_app, mock_license_manager):
        """Test that clicking Get Pro button opens Get Pro dialog."""
        stub_dialog = create_autospec(GetProDialog, instance=True)
        stub_dialog.exec.return_value = False  # Dialog cancelled
        dialog_calls = []

        def stub_factory(parent):
            dialog_calls.append(parent)
            return stub_dialog

        widget = FooterWidget(
            license_manager=mock_license_manager,
            get_pro_dialog_factory=stub_factory,
        )

        # Simulate button click
        widget._show_get_pro_dialog()

        # Verify dialog was created and shown
        assert len(dialog_calls) == 1
        assert dialog_calls[0] is widget
        stub_dialog.exec.assert_called_once()

    def test_license_status_change_updates_pro_button_visibility(
        self, qt_app, mock_license_manager
    ):
        """Test that license status changes update Pro button visibility."""
        mock_license_manager.is_pro = False
        widget = FooterWidget(license_manager=mock_license_manager)
        widget.show()  # Widget needs to be shown for visibility to work

        # Initial state should show Pro button for free user
        assert widget.get_pro_button.isVisible() == True

        # Simulate Pro upgrade
        mock_license_manager.is_pro = True
        widget._handle_license_status_changed(True)

        assert widget.get_pro_button.isVisible() == False

        # Simulate downgrade to Free
        mock_license_manager.is_pro = False
        widget._handle_license_status_changed(False)

        assert widget.get_pro_button.isVisible() == True


@pytest.mark.qt
class TestFooterWidgetInteraction:
    """Test footer widget user interactions."""

    def test_feedback_button_keyboard_interaction(self, qt_app, mock_license_manager):
        """Test feedback button can be activated via keyboard."""
        stub_dialog = create_autospec(FeedbackDialog, instance=True)
        dialog_calls = []

        def stub_factory(parent):
            dialog_calls.append(parent)
            return stub_dialog

        widget = FooterWidget(
            license_manager=mock_license_manager,
            feedback_dialog_factory=stub_factory,
        )

        # Set focus to feedback button
        widget.feedback_button.setFocus()

        # Simulate space key press (should activate button)
        QTest.keyClick(widget.feedback_button, Qt.Key.Key_Space)

        # Verify dialog was opened
        assert len(dialog_calls) == 1
        assert dialog_calls[0] is widget
        stub_dialog.exec.assert_called_once()

    def test_multiple_status_changes(self, qt_app, mock_license_manager):
        """Test multiple rapid status changes."""
        mock_license_manager.is_pro = False
        widget = FooterWidget(license_manager=mock_license_manager)

        # Test multiple status changes
        for i in range(5):
            is_pro = i % 2 == 0
            mock_license_manager.is_pro = is_pro
            widget._handle_license_status_changed(is_pro)

            expected_text = "MBD Pro" if is_pro else "MBD Free"
            assert widget.status_label.text() == expected_text
