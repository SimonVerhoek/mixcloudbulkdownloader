"""Donation dialog widget for requesting user donations after download completion."""

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.consts import STRIPE_DONATION_URL


class DonationDialog(QDialog):
    """Dialog that requests user donations after successful downloads.

    This dialog appears after downloads complete and offers users the option
    to support the project through donations. Users can either donate or
    dismiss the dialog.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the donation dialog.

        Args:
            parent: Parent widget for the dialog
        """
        super().__init__(parent)

        self.setWindowTitle("Support Mixcloud Bulk Downloader")
        self.setModal(True)
        self.setObjectName("donationDialog")

        # Set reasonable constraints but allow dynamic sizing
        self.setMinimumWidth(350)
        self.setMaximumWidth(500)

        self._setup_ui()
        self._connect_signals()

        # Auto-size the dialog to fit content, then fix the size
        self.adjustSize()
        self.setFixedSize(self.size())

    def _setup_ui(self) -> None:
        """Set up the dialog user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Main message
        message_label = QLabel(
            """
            Your downloads have completed successfully!

            If you find this application useful, please consider supporting its development with a donation.
            Your support helps keep the project maintained and improved.
            """
        )
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Set a preferred width to ensure proper text wrapping
        message_label.setMinimumWidth(300)
        layout.addWidget(message_label)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Donate button
        self.donate_button = QPushButton("Donate")
        self.donate_button.setObjectName("donateButton")
        button_layout.addWidget(self.donate_button)

        # No thank you button
        self.no_thanks_button = QPushButton("No thank you")
        self.no_thanks_button.setObjectName("secondaryButton")
        button_layout.addWidget(self.no_thanks_button)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect button signals to their respective handlers."""
        self.donate_button.clicked.connect(self._handle_donate)
        self.no_thanks_button.clicked.connect(self._handle_no_thanks)

    def _handle_donate(self) -> None:
        """Handle the donate button click by opening the donation URL."""
        try:
            webbrowser.open(STRIPE_DONATION_URL)
        except Exception:
            # If opening the browser fails, just close the dialog
            pass
        finally:
            self.accept()

    def _handle_no_thanks(self) -> None:
        """Handle the no thanks button click by dismissing the dialog."""
        self.reject()
