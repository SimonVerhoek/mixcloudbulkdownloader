"""Settings dialog for Mixcloud Bulk Downloader user preferences."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from app.consts import (
    SETTINGS_DIALOG_HEIGHT,
    SETTINGS_DIALOG_MIN_HEIGHT,
    SETTINGS_DIALOG_MIN_WIDTH,
    SETTINGS_DIALOG_WIDTH,
)


class SettingsDialog(QDialog):
    """Settings configuration dialog for the application.

    This dialog provides a user interface for configuring application
    settings. Currently displays a placeholder overlay with test content.
    The dialog uses OS-native styling and follows platform conventions.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the settings dialog with UI components.

        Args:
            parent: Parent widget for the dialog. If None, dialog is top-level.
        """
        super().__init__(parent)

        self._setup_dialog()
        self._setup_ui()

    def _setup_dialog(self) -> None:
        """Configure dialog window properties and behavior."""
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(SETTINGS_DIALOG_WIDTH, SETTINGS_DIALOG_HEIGHT)
        self.setMinimumSize(SETTINGS_DIALOG_MIN_WIDTH, SETTINGS_DIALOG_MIN_HEIGHT)

        # Center the dialog on the parent window or screen
        if self.parent():
            self.move(self.parent().geometry().center() - self.rect().center())

    def _setup_ui(self) -> None:
        """Create and configure the dialog's user interface elements."""
        layout = QVBoxLayout()

        # Temporary placeholder content
        placeholder_label = QLabel("test test test")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setObjectName("placeholderLabel")

        layout.addWidget(placeholder_label)
        self.setLayout(layout)
