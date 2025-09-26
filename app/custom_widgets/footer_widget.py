"""Footer widget showing license status and feedback button."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from app.custom_widgets.dialogs.feedback_dialog import FeedbackDialog
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.services.license_manager import LicenseManager, license_manager


class FooterWidget(QWidget):
    """Footer widget displaying Pro status and feedback button.

    Shows the user's license status (Pro/Free) on the left side
    and a feedback button on the right side.
    """

    def __init__(
        self, license_manager: LicenseManager = license_manager, parent: QWidget | None = None
    ) -> None:
        """Initialize footer widget with license status and feedback button.

        Args:
            license_manager: License manager for Pro status checking
            parent: Parent widget
        """
        super().__init__(parent)

        self.license_manager = license_manager
        self.setObjectName("footerWidget")

        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        # License status label (left side)
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self._update_status_text()

        # Get MBD Pro button (center, only shown for non-Pro users)
        self.get_pro_button = QPushButton("Get MBD Pro")
        self.get_pro_button.setObjectName("getMBDProButton")
        self.get_pro_button.clicked.connect(self._show_get_pro_dialog)

        # Feedback button (right side)
        self.feedback_button = QPushButton("Feedback?")
        self.feedback_button.setObjectName("feedbackButton")
        self.feedback_button.clicked.connect(self._show_feedback_dialog)

        # Add to layout with stretches for spacing
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.get_pro_button)
        layout.addStretch()
        layout.addWidget(self.feedback_button)

        self.setLayout(layout)

        # Connect to license status changes
        self.license_manager.license_status_changed.connect(self._handle_license_status_changed)

        # Set initial button visibility
        self._update_pro_button_visibility()

    def _update_status_text(self) -> None:
        """Update the status label text based on license status."""
        status = "MBD Pro" if self.license_manager.is_pro else "MBD Free"
        self.status_label.setText(status)

    def _update_pro_button_visibility(self) -> None:
        """Update Get Pro button visibility based on license status."""
        # Only show Get Pro button for non-Pro users
        self.get_pro_button.setVisible(not self.license_manager.is_pro)

    def _handle_license_status_changed(self, is_pro: bool) -> None:
        """Handle license status changes by updating the display.

        Args:
            is_pro: Whether user now has Pro status
        """
        self._update_status_text()
        self._update_pro_button_visibility()

    def _show_get_pro_dialog(self) -> None:
        """Show the Get Pro dialog."""
        dialog = GetProDialog(self)
        result = dialog.exec()
        if result:  # Dialog accepted (successful verification)
            # Status will be updated automatically via license_status_changed signal
            pass

    def _show_feedback_dialog(self) -> None:
        """Show the feedback dialog."""
        dialog = FeedbackDialog(self)
        dialog.exec()
