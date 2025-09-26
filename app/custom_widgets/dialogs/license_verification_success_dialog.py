"""License verification success dialog."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from app.consts.license import LICENSE_VERIFICATION_SUCCESS
from app.consts.ui import (
    LICENSE_SUCCESS_DIALOG_HEIGHT,
    LICENSE_SUCCESS_DIALOG_WIDTH,
)


class LicenseVerificationSuccessDialog(QDialog):
    """Dialog displayed when license verification is successful.

    This dialog congratulates the user on their successful Pro upgrade
    and provides a clear call-to-action to start using Pro features.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the license verification success dialog.

        Args:
            parent: Parent widget for the dialog.
        """
        super().__init__(parent)

        self.setWindowTitle("Welcome to MBD Pro!")
        self.setModal(True)
        self.setObjectName("licenseSuccessDialog")

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the dialog user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Success icon and title
        title_label = QLabel("🎉 Congratulations!")
        title_label.setObjectName("successTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Welcome message
        message_label = QLabel(LICENSE_VERIFICATION_SUCCESS)
        message_label.setObjectName("message")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)

        # Additional instructions
        instructions_label = QLabel(
            "Your Pro features are now active! You can now enjoy:\n\n"
            "• Unlimited bulk downloads\n"
            "• Premium audio formats\n"
            "• Custom download directories\n\n"
            "Happy Bulk downloading!"
        )
        instructions_label.setObjectName("featureList")
        instructions_label.setWordWrap(True)
        instructions_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(instructions_label)

        # Action button
        self.start_button = QPushButton("Start bulk downloading like a pro")
        self.start_button.setObjectName("primaryButton")
        layout.addWidget(self.start_button)

    def _connect_signals(self) -> None:
        """Connect button signals to their respective handlers."""
        self.start_button.clicked.connect(self._handle_start)

    def _handle_start(self) -> None:
        """Handle the start button click by closing the dialog."""
        self.accept()
