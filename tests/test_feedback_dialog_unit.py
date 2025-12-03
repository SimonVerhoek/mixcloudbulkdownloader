"""Unit tests for feedback dialog functionality."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from app.custom_widgets.dialogs.feedback_dialog import FeedbackDialog


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def parent_widget():
    """Create a parent widget for dialog testing."""
    return QWidget()


@pytest.mark.qt
class TestFeedbackDialogUnit:
    """Unit tests for FeedbackDialog functionality."""

    def test_dialog_initialization(self, qt_app, parent_widget):
        """Test dialog initializes with correct properties."""
        dialog = FeedbackDialog(parent_widget)

        assert dialog.parent() is parent_widget
        assert dialog.windowTitle() == "Send Feedback"
        assert dialog.isModal()
        assert dialog.objectName() == "feedbackDialog"

    def test_dialog_minimum_size(self, qt_app, parent_widget):
        """Test dialog has appropriate minimum size."""
        dialog = FeedbackDialog(parent_widget)

        min_size = dialog.minimumSize()
        assert min_size.width() == 400
        assert min_size.height() == 300

    def test_widget_object_names(self, qt_app, parent_widget):
        """Test that widgets have correct object names for styling."""
        dialog = FeedbackDialog(parent_widget)

        assert dialog.feedback_text.objectName() == "feedbackText"
        assert dialog.email_field.objectName() == "emailField"
        assert dialog.cancel_button.objectName() == "cancelButton"
        assert dialog.send_button.objectName() == "sendButton"

    def test_send_button_is_default(self, qt_app, parent_widget):
        """Test that send button is the default button."""
        dialog = FeedbackDialog(parent_widget)

        assert dialog.send_button.isDefault()

    def test_feedback_text_placeholder(self, qt_app, parent_widget):
        """Test feedback text field has helpful placeholder text."""
        dialog = FeedbackDialog(parent_widget)

        placeholder = dialog.feedback_text.placeholderText()
        assert len(placeholder) > 0
        assert "describe" in placeholder.lower()
        assert "feedback" in placeholder.lower()

    def test_email_field_placeholder(self, qt_app, parent_widget):
        """Test email field has helpful placeholder text."""
        dialog = FeedbackDialog(parent_widget)

        placeholder = dialog.email_field.placeholderText()
        assert placeholder == "Enter your email if you'd like a response"


@pytest.mark.qt
class TestFeedbackDialogValidation:
    """Test feedback dialog input validation."""

    def test_empty_feedback_shows_warning(self, qt_app, parent_widget):
        """Test warning shown for empty feedback."""
        dialog = FeedbackDialog(parent_widget)

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog._send_feedback()

            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[0] is dialog
            assert "No Feedback" in args[1]

    def test_whitespace_only_feedback_shows_warning(self, qt_app, parent_widget):
        """Test warning shown for whitespace-only feedback."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("   \n\t\r   ")

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog._send_feedback()

            mock_warning.assert_called_once()

    def test_valid_feedback_proceeds_to_api(self, qt_app, parent_widget):
        """Test that valid feedback proceeds to API submission."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("This is valid feedback.")

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager") as mock_lm,
            patch.object(QMessageBox, "warning") as mock_warning,
        ):

            # Mock other parts of _send_feedback to isolate validation testing
            with patch.object(QMessageBox, "information"), patch.object(dialog, "accept"):

                dialog._send_feedback()

                # Warning should not be called for valid input
                mock_warning.assert_not_called()
                # API submission should be attempted
                mock_lm.submit_feedback.assert_called_once_with("This is valid feedback.", None)


@pytest.mark.qt
class TestFeedbackDialogAPISubmission:
    """Test feedback dialog API functionality using license server stub."""

    def test_api_submission_uses_license_manager(self, qt_app, parent_widget):
        """Test that feedback submission uses license manager."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback with spaces and\nnewlines!")
        dialog.email_field.setText("test@example.com")

        with patch("app.custom_widgets.dialogs.feedback_dialog.license_manager") as mock_lm:
            with patch.object(QMessageBox, "information"), patch.object(dialog, "accept"):

                dialog._send_feedback()

                # Verify license manager method was called
                mock_lm.submit_feedback.assert_called_once_with(
                    "Test feedback with spaces and\nnewlines!", "test@example.com"
                )

    def test_api_success_shows_confirmation(self, qt_app, parent_widget):
        """Test success confirmation after API submission."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager"),
            patch.object(QMessageBox, "information") as mock_info,
            patch.object(dialog, "accept") as mock_accept,
        ):

            dialog._send_feedback()

            # Verify confirmation dialog
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert "Feedback Sent" in args[1]
            assert "We've received your message" in args[2]

            # Verify dialog acceptance
            mock_accept.assert_called_once()

    def test_api_failure_shows_error_dialog(self, qt_app, parent_widget):
        """Test error dialog when API fails."""
        dialog = FeedbackDialog(parent_widget)
        feedback_text = "Test feedback for API error"
        dialog.feedback_text.setPlainText(feedback_text)

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager") as mock_lm,
            patch("app.custom_widgets.dialogs.feedback_dialog.ErrorDialog") as mock_error_dialog,
            patch("app.custom_widgets.dialogs.feedback_dialog.log_error_with_traceback"),
        ):

            # Make license manager raise an exception
            mock_lm.submit_feedback.side_effect = Exception("API Error")
            mock_dialog_instance = Mock()
            mock_error_dialog.return_value = mock_dialog_instance

            dialog._send_feedback()

            # Verify ErrorDialog was shown
            mock_error_dialog.assert_called_once()
            args = mock_error_dialog.call_args[0]
            assert args[0] is dialog  # parent
            # Should use LICENSE_FEEDBACK_ERROR constant
            mock_dialog_instance.exec.assert_called_once()

    def test_api_logging_on_success(self, qt_app, parent_widget):
        """Test that successful API submission is logged."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager"),
            patch("app.custom_widgets.dialogs.feedback_dialog.log_ui") as mock_log,
            patch.object(QMessageBox, "information"),
            patch.object(dialog, "accept"),
        ):

            dialog._send_feedback()

            mock_log.assert_called_once()
            assert "feedback submitted successfully via api" in mock_log.call_args[0][0].lower()
            assert mock_log.call_args[0][1] == "INFO"

    def test_api_logging_on_failure(self, qt_app, parent_widget):
        """Test that API failure is logged with traceback."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager") as mock_lm,
            patch(
                "app.custom_widgets.dialogs.feedback_dialog.log_error_with_traceback"
            ) as mock_log,
            patch("app.custom_widgets.dialogs.feedback_dialog.ErrorDialog"),
        ):

            # Make license manager raise an exception
            mock_lm.submit_feedback.side_effect = Exception("Test API error")

            dialog._send_feedback()

            mock_log.assert_called_once()
            assert "Failed to send feedback" in mock_log.call_args[0][0]
            assert "Test API error" in mock_log.call_args[0][0]
            assert mock_log.call_args[0][1] == "ERROR"

    # Note: Bearer token validation is now handled by LicenseManager
    # and will be tested in license manager tests

    def test_email_field_optional(self, qt_app, parent_widget):
        """Test that email field is optional."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")
        # Leave email field empty

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager") as mock_lm,
            patch.object(QMessageBox, "information"),
            patch.object(dialog, "accept"),
        ):

            dialog._send_feedback()

            # Should be called with None for email
            mock_lm.submit_feedback.assert_called_once_with("Test feedback", None)

    def test_email_field_whitespace_treated_as_none(self, qt_app, parent_widget):
        """Test that whitespace-only email is treated as None."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")
        dialog.email_field.setText("   \t\n   ")  # Only whitespace

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager") as mock_lm,
            patch.object(QMessageBox, "information"),
            patch.object(dialog, "accept"),
        ):

            dialog._send_feedback()

            # Should be called with None for email
            mock_lm.submit_feedback.assert_called_once_with("Test feedback", None)

    def test_button_state_during_api_call(self, qt_app, parent_widget):
        """Test that send button is disabled during API call."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")

        # Track button state changes
        button_states = []
        original_set_enabled = dialog.send_button.setEnabled
        original_set_text = dialog.send_button.setText

        def track_enabled(enabled):
            button_states.append(("enabled", enabled))
            original_set_enabled(enabled)

        def track_text(text):
            button_states.append(("text", text))
            original_set_text(text)

        dialog.send_button.setEnabled = track_enabled
        dialog.send_button.setText = track_text

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager"),
            patch.object(QMessageBox, "information"),
            patch.object(dialog, "accept"),
        ):

            dialog._send_feedback()

            # Check button state changes
            assert ("enabled", False) in button_states
            assert ("text", "Sending...") in button_states
            assert ("enabled", True) in button_states
            assert ("text", "Send Feedback") in button_states


@pytest.mark.qt
class TestFeedbackDialogUserInteraction:
    """Test user interaction scenarios."""

    def test_cancel_button_keyboard_activation(self, qt_app, parent_widget):
        """Test cancel button can be activated via keyboard."""
        dialog = FeedbackDialog(parent_widget)

        dialog.reject = Mock()

        # Set focus and press space
        dialog.cancel_button.setFocus()
        QTest.keyClick(dialog.cancel_button, Qt.Key.Key_Space)

        dialog.reject.assert_called_once()

    def test_send_button_keyboard_activation(self, qt_app, parent_widget):
        """Test send button can be activated via keyboard."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager"),
            patch.object(QMessageBox, "information"),
            patch.object(dialog, "accept") as mock_accept,
        ):

            # Set focus and press space
            dialog.send_button.setFocus()
            QTest.keyClick(dialog.send_button, Qt.Key.Key_Space)

            mock_accept.assert_called_once()

    def test_enter_key_activates_default_button(self, qt_app, parent_widget):
        """Test that Enter key activates the default (Send) button."""
        dialog = FeedbackDialog(parent_widget)
        dialog.feedback_text.setPlainText("Test feedback")

        with (
            patch("app.custom_widgets.dialogs.feedback_dialog.license_manager"),
            patch.object(QMessageBox, "information"),
            patch.object(dialog, "accept") as mock_accept,
        ):

            # Set focus to send button and press Enter
            dialog.send_button.setFocus()
            QTest.keyClick(dialog.send_button, Qt.Key.Key_Return)

            mock_accept.assert_called_once()

    def test_escape_key_closes_dialog(self, qt_app, parent_widget):
        """Test that Escape key closes the dialog."""
        dialog = FeedbackDialog(parent_widget)

        dialog.reject = Mock()

        # Press Escape
        QTest.keyClick(dialog, Qt.Key.Key_Escape)

        dialog.reject.assert_called_once()
