"""License verification failure dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from app.consts import (
    LICENSE_FAILURE_DIALOG_HEIGHT,
    LICENSE_FAILURE_DIALOG_WIDTH,
)


class LicenseVerificationFailureDialog(QDialog):
    """Dialog displayed when license verification fails.

    This dialog provides user-friendly error messaging and suggestions
    for resolving verification issues.
    """

    def __init__(
        self, parent: QWidget | None = None, error_message: str = "License verification failed."
    ) -> None:
        """Initialize the license verification failure dialog.

        Args:
            parent: Parent widget for the dialog.
            error_message: Specific error message to display to the user.
        """
        super().__init__(parent)

        self.error_message = error_message

        self.setWindowTitle("License Verification Failed")
        self.setModal(True)
        self.setObjectName("licenseFailureDialog")

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the dialog user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Error icon and title
        title_label = QLabel("❌ Oops!")
        title_label.setObjectName("errorTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Error message
        message_label = QLabel(self.error_message)
        message_label.setObjectName("message")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        # Suggestions
        suggestions_label = QLabel(
            "Here's what you can try:\n\n"
            "• Double-check your email and license key\n"
            "• Make sure you have an active internet connection\n"
            "• Contact support if you continue having issues"
        )
        suggestions_label.setObjectName("suggestions")
        suggestions_label.setWordWrap(True)
        suggestions_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(suggestions_label)

        # Action button
        self.ok_button = QPushButton("Ok")
        self.ok_button.setObjectName("primaryButton")
        layout.addWidget(self.ok_button)

    def _connect_signals(self) -> None:
        """Connect button signals to their respective handlers."""
        self.ok_button.clicked.connect(self._handle_ok)

    def _handle_ok(self) -> None:
        """Handle the ok button click by closing the dialog."""
        self.accept()
