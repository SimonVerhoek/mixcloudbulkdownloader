from pathlib import Path

from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from app.consts.settings import DEFAULT_CHECK_UPDATES_ON_STARTUP, SETTING_CHECK_UPDATES_ON_STARTUP
from app.consts.ui import MAIN_WINDOW_MIN_HEIGHT, MAIN_WINDOW_MIN_WIDTH
from app.custom_widgets.central_widget import CentralWidget
from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.custom_widgets.dialogs.settings_dialog import SettingsDialog
from app.custom_widgets.dialogs.update_dialog import UpdateDialog
from app.custom_widgets.footer_widget import FooterWidget
from app.qt_logger import log_ui
from app.services.license_manager import license_manager
from app.services.settings_manager import settings
from app.services.update_service import update_service
from app.threads.startup_verification_thread import StartupVerificationThread
from app.threads.update_check_thread import UpdateCheckThread
from app.utils.cleanup import PartialFileCleanup
from app.utils.ffmpeg import verify_ffmpeg_availability


class MainWindow(QMainWindow):
    """Main application window for Mixcloud Bulk Downloader.

    This is the top-level window that contains all the application UI
    and handles window-level operations like menus and window properties.
    """

    def __init__(self) -> None:
        """Initialize the main window with UI components and application settings."""
        super().__init__()

        # import services
        self.settings = settings
        self.license_manager = license_manager

        # Initialize update check thread
        self.update_check_thread: UpdateCheckThread | None = None

        # Create main container widget with vertical layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create central widget and footer
        widget = CentralWidget(license_manager=self.license_manager)
        self.central_widget = widget
        self.footer_widget = FooterWidget(license_manager=self.license_manager)

        # Add to layout
        main_layout.addWidget(widget)
        main_layout.addWidget(self.footer_widget)

        main_widget.setLayout(main_layout)

        self.setWindowTitle("Mixcloud Bulk Downloader")
        self.setMinimumSize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)

        # Create menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        # Add Settings menu item
        file_menu.addAction("Settings...", self._show_settings_dialog)

        # Add Check for Updates menu item
        file_menu.addAction("Check for Updates...", self.start_update_check)
        file_menu.addSeparator()

        # Add Get MBD Pro menu item (only shown for non-Pro users)
        self.get_mbd_pro_action = file_menu.addAction("Get MBD Pro...", self._show_get_pro_dialog)
        file_menu.addSeparator()

        file_menu.addAction("Exit", QApplication.quit)

        self.setCentralWidget(main_widget)

        # Connect to license status changes
        self.license_manager.license_status_changed.connect(self._handle_license_status_changed)

        # Initialize threading settings with defaults
        self.settings.initialize_threading_settings(self.license_manager.is_pro)

        # Initialize Pro UI state
        self.refresh_pro_ui_elements()

        # Perform startup license verification
        self.startup_license_verification()

        # Check for updates on startup if enabled
        self.startup_update_check()

        # Clean up partial files from previous runs
        self.cleanup_partial_files()

        # Configure application behavior
        app_instance = QGuiApplication.instance()
        if app_instance:
            app_instance.setQuitOnLastWindowClosed(True)
            app_instance.setApplicationDisplayName("Mixcloud Bulk Downloader")
            app_instance.processEvents()

    def _show_settings_dialog(self) -> None:
        """Display the settings configuration dialog.

        Creates and shows a modal settings dialog that allows users to
        configure application preferences. The dialog is centered on the
        main window and uses OS-native styling.
        """
        settings_dialog = SettingsDialog(parent=self)
        settings_dialog.exec()

    def _show_get_pro_dialog(self) -> None:
        """Show the Get Pro dialog from the menu."""
        dialog = GetProDialog(self)
        result = dialog.exec()
        if result:  # Dialog accepted (successful verification)
            self.refresh_pro_ui_elements()

    def refresh_pro_ui_elements(self) -> None:
        """Refresh Pro UI elements based on current license status."""
        self.update_menu_items()

    def update_menu_items(self) -> None:
        """Update menu items visibility based on Pro status."""
        is_pro = self.license_manager.is_pro

        # Show/hide Get MBD Pro menu item based on Pro status
        if hasattr(self, "get_mbd_pro_action"):
            self.get_mbd_pro_action.setVisible(not is_pro)

    def startup_license_verification(self) -> None:
        """Perform startup license verification in background thread."""
        self.verification_thread = StartupVerificationThread(self.license_manager, self)
        self.verification_thread.start()

    def startup_update_check(self) -> None:
        """Check for updates on startup if enabled in settings."""
        if self.settings.get(SETTING_CHECK_UPDATES_ON_STARTUP, DEFAULT_CHECK_UPDATES_ON_STARTUP):
            self.start_update_check()

    def start_update_check(self) -> None:
        """Start update check in background thread."""
        # Prevent multiple simultaneous checks
        if self.update_check_thread and self.update_check_thread.isRunning():
            return

        self.update_check_thread = UpdateCheckThread(update_service)
        self.update_check_thread.update_available.connect(self._show_update_dialog)
        self.update_check_thread.no_update_available.connect(self._handle_no_update_available)
        self.update_check_thread.error_signal.connect(self._handle_update_error)
        self.update_check_thread.start()

    def _show_update_dialog(
        self, current_version: str, latest_version: str, download_url: str, release_notes: str
    ) -> None:
        """Show update dialog when an update is available.

        Args:
            current_version: Current application version
            latest_version: Latest available version
            download_url: URL to download the update
            release_notes: Release notes/changelog
        """
        dialog = UpdateDialog(
            current_version, latest_version, download_url, release_notes, update_service, self
        )
        dialog.exec()

    def _handle_no_update_available(self) -> None:
        """Handle case when no update is available."""
        # Only show message for manual checks (when user clicked menu)
        # Startup checks should be silent when no update is available
        pass

    def _handle_update_error(self, error_message: str) -> None:
        """Handle update check errors.

        Args:
            error_message: Error description
        """
        # Only show error dialog for manual checks
        # Startup checks should log errors but not show dialogs
        ErrorDialog(self, f"Update check failed: {error_message}", "Update Error")

    def cleanup_partial_files(self) -> None:
        """Clean up partial download and conversion files from previous runs."""
        try:
            # Get default download directory or use home directory as fallback
            default_download_dir = self.settings.get(
                "default_download_directory", str(Path.home() / "Downloads")
            )
            download_dir = Path(default_download_dir)

            if download_dir.exists():
                # Clean up files older than 60 minutes (1 hour)
                stats = PartialFileCleanup.cleanup_partial_files(
                    directory=download_dir, max_age_minutes=60
                )

                total_cleaned = stats["downloading"] + stats["converting"]
                if total_cleaned > 0:
                    log_ui(
                        f"Cleaned up {total_cleaned} partial files from previous runs "
                        f"({stats['downloading']} downloading, {stats['converting']} converting)",
                        "INFO",
                    )

                # Also clean up fragment files
                fragment_count = PartialFileCleanup.cleanup_fragment_files(directory=download_dir)
                if fragment_count > 0:
                    log_ui(f"Cleaned up {fragment_count} fragment files", "INFO")
        except Exception as e:
            # Don't let cleanup errors affect startup
            log_ui(f"Warning: Could not clean up partial files: {e}", "WARNING")

    def _handle_license_status_changed(self, is_pro: bool) -> None:
        """Handle changes in license status.

        Args:
            is_pro: Whether user now has Pro status
        """
        # Refresh UI elements based on new Pro status
        self.refresh_pro_ui_elements()

        # Check FFmpeg availability for Pro users after verification
        if is_pro:
            self._verify_ffmpeg_availability()

    def _verify_ffmpeg_availability(self) -> None:
        """Verify FFmpeg availability for Pro users and show appropriate messaging."""
        ffmpeg_available = verify_ffmpeg_availability()

        if ffmpeg_available:
            log_ui("FFmpeg executable found and available for audio conversion", "INFO")
        else:
            log_ui("FFmpeg executable not found - audio conversion may not be available", "WARNING")

            # Show user-friendly dialog about audio conversion limitations
            ErrorDialog(
                self,
                message="Audio conversion may not be available due to missing FFmpeg.\n\n"
                "Some audio formats may not be accessible. If you experience issues "
                "with downloads, please contact support for assistance.",
            )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle application close event with proper cleanup."""
        try:
            # Stop any running verification threads
            if hasattr(self, "verification_thread") and self.verification_thread.isRunning():
                self.verification_thread.terminate()
                self.verification_thread.wait(1000)  # Wait up to 1 second

            # Stop update check thread (following verification_thread pattern)
            if (
                hasattr(self, "update_check_thread")
                and self.update_check_thread
                and self.update_check_thread.isRunning()
            ):
                self.update_check_thread.stop()  # Use stop() method instead of terminate()

            # Disable keyring operations during shutdown to prevent crash
            if hasattr(self, "license_manager") and hasattr(self.license_manager, "settings"):
                # Mark settings as shutting down to prevent keyring access
                self.license_manager.settings._shutting_down = True

        except Exception:
            # Ignore any errors during cleanup to ensure app can exit
            pass
        finally:
            # Always accept the close event
            event.accept()
