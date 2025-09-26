"""Feedback dialog for user feedback submission."""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.consts.license import LICENSE_FEEDBACK_ERROR
from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.qt_logger import log_error_with_traceback, log_ui
from app.services.license_manager import license_manager


class FeedbackDialog(QDialog):
    """Dialog for collecting and sending user feedback via API.

    Provides a multiline text field for feedback input, optional email field,
    and buttons to cancel or send the feedback via API.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize feedback dialog with text field and buttons.

        Args:
            parent: Parent widget for the dialog
        """
        super().__init__(parent)

        self.setWindowTitle("Send Feedback")
        self.setModal(True)
        self.setObjectName("feedbackDialog")
        self.setMinimumSize(400, 300)

        # Create layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Instructions label
        instructions = QLabel(
            "Tell us about your experience with Mixcloud Bulk Downloader.\n"
            "Your feedback helps us improve the application!"
        )
        instructions.setWordWrap(True)
        instructions.setObjectName("instructionsLabel")

        # Email field
        email_label = QLabel("Email (optional):")
        email_label.setObjectName("emailLabel")

        self.email_field = QLineEdit()
        self.email_field.setObjectName("emailField")
        self.email_field.setPlaceholderText("Enter your email if you'd like a response")

        # Feedback text field
        self.feedback_label = QLabel("Feedback (2000 characters left):")
        self.feedback_label.setObjectName("feedbackLabel")

        self.feedback_text = QTextEdit()
        self.feedback_text.setObjectName("feedbackText")
        self.feedback_text.setPlaceholderText(
            "Please describe any issues, suggestions, or general feedback about the application..."
        )

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self.reject)

        self.send_button = QPushButton("Send Feedback")
        self.send_button.setObjectName("sendButton")
        self.send_button.clicked.connect(self._send_feedback)
        self.send_button.setDefault(True)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.send_button)

        # Add to main layout
        layout.addWidget(instructions)
        layout.addWidget(email_label)
        layout.addWidget(self.email_field)
        layout.addWidget(self.feedback_label)
        layout.addWidget(self.feedback_text)
        layout.addLayout(button_layout)

        # Connect text change signal to update character counter
        self.feedback_text.textChanged.connect(self._update_character_counter)

        self.setLayout(layout)

    def _update_character_counter(self) -> None:
        """Update the character counter in the feedback label."""
        current_text = self.feedback_text.toPlainText()
        current_length = len(current_text)
        max_length = 2000
        remaining = max_length - current_length

        # Update label text
        self.feedback_label.setText(f"Feedback ({remaining} characters left):")

        # Enforce character limit by truncating if necessary
        if current_length > max_length:
            truncated_text = current_text[:max_length]
            # Temporarily disconnect signal to avoid recursion
            self.feedback_text.textChanged.disconnect(self._update_character_counter)
            self.feedback_text.setPlainText(truncated_text)
            # Move cursor to end
            cursor = self.feedback_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.feedback_text.setTextCursor(cursor)
            # Reconnect signal
            self.feedback_text.textChanged.connect(self._update_character_counter)
            # Update counter again with correct value
            self.feedback_label.setText("Feedback (0 characters left):")

    def _send_feedback(self) -> None:
        """Send feedback via API."""
        feedback_text = self.feedback_text.toPlainText().strip()
        email = self.email_field.text().strip() or None

        if not feedback_text:
            QMessageBox.warning(self, "No Feedback", "Please enter your feedback before sending.")
            return

        # Disable send button to prevent double-clicks
        self.send_button.setEnabled(False)
        self.send_button.setText("Sending...")

        try:
            license_manager.submit_feedback(feedback_text, email)

            log_ui("Feedback submitted successfully via API", "INFO")

            # Show confirmation and close dialog
            QMessageBox.information(
                self, "Feedback Sent", "Thank you for your feedback! We've received your message."
            )

            self.accept()

        except Exception as e:
            error_msg = f"Failed to send feedback: {str(e)}"
            log_error_with_traceback(error_msg, "ERROR")

            # Show error dialog
            error_dialog = ErrorDialog(self, LICENSE_FEEDBACK_ERROR, "Feedback Error")
            error_dialog.exec()
        finally:
            # Re-enable send button
            self.send_button.setEnabled(True)
            self.send_button.setText("Send Feedback")
