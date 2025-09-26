"""Settings dialog for Mixcloud Bulk Downloader user preferences."""

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCursor, QFontMetrics
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.consts.audio import AUDIO_FORMATS
from app.consts.ui import (
    SETTINGS_DIALOG_HEIGHT,
    SETTINGS_DIALOG_MIN_HEIGHT,
    SETTINGS_DIALOG_MIN_WIDTH,
    SETTINGS_DIALOG_WIDTH,
)
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.custom_widgets.pro_feature_widget import ProFeatureWidget
from app.services.license_manager import LicenseManager, license_manager
from app.services.settings_manager import SettingsManager, settings


class SettingsDialog(ProFeatureWidget, QDialog):
    """Settings configuration dialog for the application.

    This dialog provides a user interface for configuring application
    settings including Pro-only features like default download directory
    and audio format preferences. Uses consistent Pro feature gating.
    """

    def __init__(
        self,
        license_manager: LicenseManager = license_manager,
        settings_manager: SettingsManager = settings,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the settings dialog with UI components.

        Args:
            license_manager: License manager for Pro status checking
            settings_manager: Settings manager for persistence
            parent: Parent widget for the dialog. If None, dialog is top-level.
        """
        # Initialize QDialog first, then ProFeatureWidget mixin
        QDialog.__init__(self, parent)
        ProFeatureWidget.__init__(self, license_manager, parent)

        self.settings_manager = settings_manager
        self._full_download_path = None  # Store the full path separately from display

        self._setup_dialog()
        self._setup_ui()
        self._load_current_settings()

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
        main_layout = QVBoxLayout()

        # Create settings sections
        self._create_pro_features_section(main_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)

        # Set object names for proper styling
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setObjectName("primaryButton")
        if cancel_button:
            cancel_button.setObjectName("secondaryButton")

        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def _create_pro_features_section(self, main_layout: QVBoxLayout) -> None:
        """Create Pro features section with appropriate gating."""
        self.pro_group = QGroupBox("Pro Features")
        pro_layout = QFormLayout()
        pro_layout.setLabelAlignment(Qt.AlignVCenter)

        # Default Download Directory
        self._create_download_directory_setting(pro_layout)

        # Default Audio Format
        self._create_audio_format_setting(pro_layout)

        self.pro_group.setLayout(pro_layout)

        # Configure group box for free users
        if not self.license_manager.is_pro:
            self._setup_pro_group_for_free_users()

        main_layout.addWidget(self.pro_group)

    def _setup_pro_group_for_free_users(self) -> None:
        """Configure the Pro Features group box for free users with tooltip and clickable cursor."""
        # Set tooltip for the entire group box
        self.pro_group.setToolTip("🔒 Upgrade to MBD Pro to unlock these features")

        # Set cursor to indicate clickable
        self.pro_group.setCursor(QCursor(Qt.PointingHandCursor))

        # Make the group box clickable
        self.pro_group.mousePressEvent = lambda event: self._show_upgrade_dialog()

    def _create_download_directory_setting(self, layout: QFormLayout) -> None:
        """Create default download directory setting."""
        dir_layout = QHBoxLayout()

        self.download_dir_label = QLabel("Not set")
        self.download_dir_label.setWordWrap(False)  # Prevent text wrapping
        self.download_dir_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )  # Allow text selection
        # Elide long paths with "..." in the middle to keep them on one line
        self.download_dir_label.setTextFormat(Qt.PlainText)
        self.download_dir_button = QPushButton("Browse...")
        self.download_dir_button.clicked.connect(self._browse_download_directory)

        dir_layout.addWidget(self.download_dir_label, 1)  # Stretch to fill space
        dir_layout.addWidget(self.download_dir_button)

        dir_widget = QWidget()
        dir_widget.setLayout(dir_layout)

        # Create label with lock icon if free user
        label_text = "Default Download Directory:"
        if not self.license_manager.is_pro:
            label_text += " 🔒"

        layout.addRow(label_text, dir_widget)

        # Register as Pro feature
        self.register_pro_widget(self.download_dir_button)
        self.register_pro_widget(self.download_dir_label)

    def _create_audio_format_setting(self, layout: QFormLayout) -> None:
        """Create default audio format setting."""
        self.audio_format_combo = QComboBox()
        # Create list of formats from AUDIO_FORMATS using dot notation
        audio_formats = sorted([fmt.label for fmt in AUDIO_FORMATS.values()])
        self.audio_format_combo.addItems(audio_formats)
        self.audio_format_combo.setCurrentText(AUDIO_FORMATS.mp3.label)  # Default

        # Create label with lock icon if free user
        label_text = "Default Audio Format:"
        if not self.license_manager.is_pro:
            label_text += " 🔒"

        layout.addRow(label_text, self.audio_format_combo)

        # Register as Pro feature
        self.register_pro_widget(self.audio_format_combo)

    @Slot()
    def _browse_download_directory(self) -> None:
        """Open directory picker for default download location."""
        if not self.license_manager.is_pro:
            return

        current_dir = self.settings_manager.get("default_download_directory", str(Path.home()))

        directory = QFileDialog.getExistingDirectory(
            self, "Select Default Download Directory", current_dir
        )

        if directory:
            self._set_directory_text(directory)

    def _load_current_settings(self) -> None:
        """Load current settings from settings manager."""
        # Load Pro settings if Pro user
        if self.license_manager.is_pro:
            # Load default download directory
            default_dir = self.settings_manager.get("default_download_directory", None)
            if default_dir:
                self._set_directory_text(default_dir)
            else:
                self.download_dir_label.setText("Not set")
                self._full_download_path = None

            # Load default audio format
            audio_format = self.settings_manager.get("default_audio_format", "MP3")
            index = self.audio_format_combo.findText(audio_format)
            if index >= 0:
                self.audio_format_combo.setCurrentIndex(index)

    @Slot()
    def _save_and_accept(self) -> None:
        """Save settings and close dialog."""
        # Save Pro settings if Pro user
        if self.license_manager.is_pro:
            # Save default download directory (use full path, not elided display text)
            if self._full_download_path and self._full_download_path != "Not set":
                self.settings_manager.set("default_download_directory", self._full_download_path)
            else:
                self.settings_manager.set("default_download_directory", None)

            # Save default audio format
            audio_format = self.audio_format_combo.currentText()
            self.settings_manager.set("default_audio_format", audio_format)

        # Sync settings to disk
        self.settings_manager.sync()

        self.accept()

    def _set_directory_text(self, directory: str) -> None:
        """Set directory text with eliding to prevent wrapping."""
        # Store the full path for saving to settings
        self._full_download_path = directory

        # Use QFontMetrics to calculate available width and elide text if needed
        font_metrics = QFontMetrics(self.download_dir_label.font())
        # Get available width (subtract some padding for the button)
        available_width = self.download_dir_label.width() - 20

        # If width is not available yet (during init), just set the text normally
        if available_width <= 0:
            self.download_dir_label.setText(directory)
            return

        # Elide text in the middle for long paths
        elided_text = font_metrics.elidedText(directory, Qt.ElideMiddle, available_width)
        self.download_dir_label.setText(elided_text)

        # Store the full path as tooltip for reference
        self.download_dir_label.setToolTip(directory)

    def _show_upgrade_dialog(self) -> None:
        """Show upgrade dialog when user clicks lock icon."""
        dialog = GetProDialog(self)
        dialog.exec()
