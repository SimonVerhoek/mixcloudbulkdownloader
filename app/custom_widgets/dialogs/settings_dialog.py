"""Settings dialog for Mixcloud Bulk Downloader user preferences."""

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCursor, QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
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
from app.consts.settings import (
    DEFAULT_CHECK_UPDATES_ON_STARTUP,
    DEFAULT_ENABLE_AUDIO_CONVERSION,
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    PARALLEL_CONVERSIONS_OPTIONS,
    PARALLEL_DOWNLOADS_OPTIONS,
    SETTING_CHECK_UPDATES_ON_STARTUP,
    SETTING_ENABLE_AUDIO_CONVERSION,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    SETTING_MAX_PARALLEL_DOWNLOADS,
)
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
from app.services.system_service import cpu_count
from app.threads.update_check_thread import UpdateCheckThread


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
        self.update_check_thread: UpdateCheckThread | None = None

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
        self._create_update_settings_section(main_layout)
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

    def _create_update_settings_section(self, main_layout: QVBoxLayout) -> None:
        """Create update settings section (not Pro-gated)."""
        # Create horizontal layout for checkbox + button
        update_layout = QHBoxLayout()

        # Update checkbox
        self.update_checkbox = QCheckBox("Check for updates on startup")
        self.update_checkbox.setChecked(DEFAULT_CHECK_UPDATES_ON_STARTUP)
        update_layout.addWidget(self.update_checkbox)

        # Add stretch to push button to the right
        update_layout.addStretch()

        # Check now button
        self.check_now_button = QPushButton("Check now")
        self.check_now_button.clicked.connect(self._check_for_updates_now)
        update_layout.addWidget(self.check_now_button)

        # Add the layout to main layout with some spacing
        main_layout.addLayout(update_layout)
        main_layout.addSpacing(10)

    def _create_pro_features_section(self, main_layout: QVBoxLayout) -> None:
        """Create Pro features section with appropriate gating."""
        self.pro_group = QGroupBox("Pro Features")
        pro_layout = QFormLayout()
        pro_layout.setLabelAlignment(Qt.AlignVCenter)

        # Default Download Directory
        self._create_download_directory_setting(pro_layout)

        # Convert Audio (checkbox + dropdown)
        self._create_audio_conversion_setting(pro_layout)

        # Max Parallel Downloads
        self._create_parallel_downloads_setting(pro_layout)

        # Max Parallel Conversions
        self._create_parallel_conversions_setting(pro_layout)

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

    def _create_audio_conversion_setting(self, layout: QFormLayout) -> None:
        """Create audio conversion checkbox and format dropdown setting."""
        # Create horizontal layout for checkbox + dropdown
        conversion_layout = QHBoxLayout()
        conversion_layout.setContentsMargins(0, 0, 0, 0)

        # Create checkbox for enabling/disabling conversion
        self.enable_conversion_checkbox = QCheckBox("Enable")
        self.enable_conversion_checkbox.setChecked(DEFAULT_ENABLE_AUDIO_CONVERSION)

        # Create dropdown for audio format selection
        self.audio_format_combo = QComboBox()
        # Create list of formats from AUDIO_FORMATS using dot notation
        audio_formats = sorted([fmt.label for fmt in AUDIO_FORMATS.values()])
        self.audio_format_combo.addItems(audio_formats)
        self.audio_format_combo.setCurrentText(AUDIO_FORMATS.mp3.label)  # Default

        # Connect checkbox to dropdown enabled state
        self.enable_conversion_checkbox.toggled.connect(self.audio_format_combo.setEnabled)

        # Set initial dropdown state based on checkbox
        self.audio_format_combo.setEnabled(self.enable_conversion_checkbox.isChecked())

        # Add widgets to layout
        conversion_layout.addWidget(self.enable_conversion_checkbox)
        conversion_layout.addWidget(self.audio_format_combo)

        # Create container widget
        conversion_widget = QWidget()
        conversion_widget.setLayout(conversion_layout)

        # Create label with lock icon if free user
        label_text = "Convert Audio:"
        if not self.license_manager.is_pro:
            label_text += " 🔒"

        layout.addRow(label_text, conversion_widget)

        # Register as Pro features
        self.register_pro_widget(self.enable_conversion_checkbox)
        self.register_pro_widget(self.audio_format_combo)

    def _create_parallel_downloads_setting(self, layout: QFormLayout) -> None:
        """Create max parallel downloads setting."""
        self.parallel_downloads_combo = QComboBox()
        self.parallel_downloads_combo.addItems([str(i) for i in PARALLEL_DOWNLOADS_OPTIONS])
        self.parallel_downloads_combo.setCurrentText(str(DEFAULT_MAX_PARALLEL_DOWNLOADS))

        label_text = "Max Parallel Downloads:"
        if not self.license_manager.is_pro:
            label_text += " 🔒"

        layout.addRow(label_text, self.parallel_downloads_combo)
        self.register_pro_widget(self.parallel_downloads_combo)

    def _create_parallel_conversions_setting(self, layout: QFormLayout) -> None:
        """Create max parallel conversions setting with CPU warning."""
        self.parallel_conversions_combo = QComboBox()
        self.parallel_conversions_combo.addItems([str(i) for i in PARALLEL_CONVERSIONS_OPTIONS])
        self.parallel_conversions_combo.setCurrentText(str(DEFAULT_MAX_PARALLEL_CONVERSIONS))

        label_text = f"Max Parallel Conversions\n(CPU cores available: {cpu_count}):"
        if not self.license_manager.is_pro:
            label_text += " 🔒"

        layout.addRow(label_text, self.parallel_conversions_combo)
        self.register_pro_widget(self.parallel_conversions_combo)

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
        # Load update settings (available to all users)
        check_updates = self.settings_manager.get(
            SETTING_CHECK_UPDATES_ON_STARTUP, DEFAULT_CHECK_UPDATES_ON_STARTUP
        )
        self.update_checkbox.setChecked(check_updates)

        # Load Pro settings if Pro user
        if self.license_manager.is_pro:
            # Load default download directory
            default_dir = self.settings_manager.get("default_download_directory", None)
            if default_dir:
                self._set_directory_text(default_dir)
            else:
                self.download_dir_label.setText("Not set")
                self._full_download_path = None

            # Load audio conversion setting
            conversion_enabled = self.settings_manager.get(
                SETTING_ENABLE_AUDIO_CONVERSION, DEFAULT_ENABLE_AUDIO_CONVERSION
            )
            self.enable_conversion_checkbox.setChecked(conversion_enabled)
            self.audio_format_combo.setEnabled(conversion_enabled)

            # Load default audio format
            audio_format = self.settings_manager.get("default_audio_format", "MP3")
            index = self.audio_format_combo.findText(audio_format)
            if index >= 0:
                self.audio_format_combo.setCurrentIndex(index)

            # Load threading settings
            max_downloads = self.settings_manager.get(
                SETTING_MAX_PARALLEL_DOWNLOADS, DEFAULT_MAX_PARALLEL_DOWNLOADS
            )
            self.parallel_downloads_combo.setCurrentText(str(max_downloads))

            max_conversions = self.settings_manager.get(
                SETTING_MAX_PARALLEL_CONVERSIONS, DEFAULT_MAX_PARALLEL_CONVERSIONS
            )
            self.parallel_conversions_combo.setCurrentText(str(max_conversions))

    @Slot()
    def _save_and_accept(self) -> None:
        """Save settings and close dialog."""
        # Save update settings (available to all users)
        check_updates = self.update_checkbox.isChecked()
        self.settings_manager.set(SETTING_CHECK_UPDATES_ON_STARTUP, check_updates)

        # Save Pro settings if Pro user
        if self.license_manager.is_pro:
            # Save default download directory (use full path, not elided display text)
            if self._full_download_path and self._full_download_path != "Not set":
                self.settings_manager.set("default_download_directory", self._full_download_path)
            else:
                self.settings_manager.set("default_download_directory", None)

            # Save audio conversion setting
            conversion_enabled = self.enable_conversion_checkbox.isChecked()
            self.settings_manager.set(SETTING_ENABLE_AUDIO_CONVERSION, conversion_enabled)

            # Save default audio format
            audio_format = self.audio_format_combo.currentText()
            self.settings_manager.set("default_audio_format", audio_format)

            # Save threading settings
            max_downloads = int(self.parallel_downloads_combo.currentText())
            max_conversions = int(self.parallel_conversions_combo.currentText())

            self.settings_manager.set(SETTING_MAX_PARALLEL_DOWNLOADS, max_downloads)
            self.settings_manager.set(SETTING_MAX_PARALLEL_CONVERSIONS, max_conversions)

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

    def _check_for_updates_now(self) -> None:
        """Trigger immediate update check via MainWindow."""
        # Disable button during check
        self.check_now_button.setEnabled(False)
        self.check_now_button.setText("Checking...")

        # Get main window reference and trigger update check
        main_window = self.parent()
        if hasattr(main_window, "start_update_check"):
            main_window.start_update_check()

        # Re-enable button (this is immediate, actual check happens in background)
        self.check_now_button.setEnabled(True)
        self.check_now_button.setText("Check now")

    def closeEvent(self, event) -> None:
        """Handle dialog close event with thread cleanup."""
        if self.update_check_thread and self.update_check_thread.isRunning():
            self.update_check_thread.stop()

        super().closeEvent(event)
