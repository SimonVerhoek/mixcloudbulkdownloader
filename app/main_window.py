from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from app.consts.settings import DEFAULT_CHECK_UPDATES_ON_STARTUP, SETTING_CHECK_UPDATES_ON_STARTUP
from app.consts.ui import MAIN_WINDOW_MIN_HEIGHT, MAIN_WINDOW_MIN_WIDTH
from app.custom_widgets.central_widget import CentralWidget
from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.custom_widgets.dialogs.settings_dialog import SettingsDialog
from app.custom_widgets.dialogs.update_dialog import UpdateDialog
from app.custom_widgets.footer_widget import FooterWidget
from app.logger import log_ui
from app.services.license_manager import LicenseManager, license_manager as _default_license_manager
from app.services.settings_manager import SettingsManager, settings as _default_settings
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

    def __init__(
        self,
        license_manager: LicenseManager | None = None,
        settings: SettingsManager | None = None,
        update_svc=None,
    ) -> None:
        """Initialize the main window with UI components and application settings.

        Args:
            license_manager: Optional license manager instance; falls back to module-level
                singleton when *None*.
            settings: Optional settings manager instance; falls back to module-level
                singleton when *None*.
            update_svc: Optional update service instance; falls back to the module-level
                ``update_service`` singleton when *None*.  Inject a stub in tests to avoid
                real network calls.
        """
        super().__init__()

        self.settings = settings if settings is not None else _default_settings
        self.license_manager = (
            license_manager if license_manager is not None else _default_license_manager
        )
        self._update_svc = update_svc if update_svc is not None else update_service

        # Initialize update check thread
        self.update_check_thread: UpdateCheckThread | None = None

        # Initialize verification thread (set in startup_license_verification)
        self.verification_thread: StartupVerificationThread | None = None

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

        # If stored credentials could not be decrypted (e.g. after an OS update that changed
        # the old volatile salt), prompt the user to re-enter their license once.
        if self.settings.credentials_were_cleared:
            self._prompt_credential_reentry()

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

    def _create_verification_thread(self, lm: LicenseManager) -> StartupVerificationThread:
        """Create a StartupVerificationThread for the given license manager."""
        return StartupVerificationThread(lm, self)

    def _create_pro_dialog(self, parent=None) -> GetProDialog:
        """Create a GetProDialog instance."""
        return GetProDialog(parent=parent)

    def _create_error_dialog(self, msg: str, parent=None) -> ErrorDialog:
        """Create an ErrorDialog instance."""
        return ErrorDialog(parent, msg)

    def _create_qmessagebox(self, parent=None) -> QMessageBox:
        """Create a QMessageBox instance.

        Extracted as a factory method so tests can subclass MainWindow and override
        this method to return a stub, avoiding real dialog display.

        Args:
            parent: Parent widget for the message box.

        Returns:
            A new QMessageBox instance.
        """
        return QMessageBox(parent)

    def _prompt_credential_reentry(self) -> None:
        """Inform the user that stored credentials were cleared and ask them to re-enter.

        This is a one-time prompt shown when previously stored credentials cannot be
        decrypted (for example because the encryption key has changed). The user's
        license is not affected — they simply need to re-enter their details once.
        """
        msg = self._create_qmessagebox(parent=self)
        msg.setWindowTitle("License Re-entry Required")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            "Due to a security improvement in how your license credentials are stored, "
            "you are required to re-enter your license email and key once more to continue.\n"
            "Your license is still valid. If you have forgotten your license key, "
            "please contact me.\n\n"
            "Apologies for the inconvenience!"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        self._show_get_pro_dialog()

    def _show_settings_dialog(self) -> None:
        """Display the settings configuration dialog.

        Creates and shows a modal settings dialog that allows users to
        configure application preferences. The dialog is centered on the
        main window and uses OS-native styling.
        """
        settings_dialog = SettingsDialog(parent=self)
        settings_dialog.check_for_updates_requested.connect(self.start_update_check)
        settings_dialog.exec()

    def _show_get_pro_dialog(self) -> None:
        """Show the Get Pro dialog from the menu."""
        dialog = self._create_pro_dialog(parent=self)
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
        self.get_mbd_pro_action.setVisible(not is_pro)

    def startup_license_verification(self) -> None:
        """Perform startup license verification in background thread."""
        self.verification_thread = self._create_verification_thread(self.license_manager)
        self.verification_thread.start()

    def startup_update_check(self) -> None:
        """Check for updates on startup if enabled in settings."""
        if self.settings.check_updates_on_startup:
            self._run_update_check(is_startup=True)

    def start_update_check(self) -> None:
        """Start an update check triggered manually (File → Check for Updates…)."""
        self._run_update_check(is_startup=False)

    def _run_update_check(self, is_startup: bool) -> None:
        """Internal runner that wires the error signal to the appropriate handler.

        Args:
            is_startup: True when called from startup_update_check; False for manual checks.
        """
        if self.update_check_thread and self.update_check_thread.isRunning():
            return

        self.update_check_thread = UpdateCheckThread(self._update_svc)
        self.update_check_thread.update_available.connect(self._show_update_dialog)
        self.update_check_thread.no_update_available.connect(self._handle_no_update_available)
        error_slot = self._handle_startup_update_error if is_startup else self._handle_update_error
        self.update_check_thread.error_signal.connect(error_slot)
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

    def _handle_startup_update_error(self, error_message: str) -> None:
        """Silently log startup update-check errors; never show a dialog.

        Args:
            error_message: Error description
        """
        log_ui(
            message=f"Startup update check failed (network may be unavailable): {error_message}",
            level="WARNING",
        )

    def _handle_update_error(self, error_message: str) -> None:
        """Show an error dialog for manual update checks (File → Check for Updates…).

        Args:
            error_message: Error description
        """
        ErrorDialog(self, f"Update check failed: {error_message}", "Update Error")

    def cleanup_partial_files(self) -> None:
        """Clean up partial download and conversion files from previous runs."""
        try:
            # Get default download directory or use home directory as fallback
            default_download_dir = self.settings.default_download_directory or str(
                Path.home() / "Downloads"
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
            self._create_error_dialog(
                msg="Audio conversion may not be available due to missing FFmpeg.\n\n"
                "Some audio formats may not be accessible. If you experience issues "
                "with downloads, please contact support for assistance.",
                parent=self,
            )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle application close event with proper cleanup."""
        try:
            # Stop any running verification threads
            if self.verification_thread is not None and self.verification_thread.isRunning():
                self.verification_thread.terminate()
                self.verification_thread.wait(1000)  # Wait up to 1 second

            # Stop update check thread
            if self.update_check_thread is not None and self.update_check_thread.isRunning():
                self.update_check_thread.stop()

            # Disable keyring operations during shutdown to prevent crash
            # Mark settings as shutting down to prevent keyring access
            self.license_manager.settings._shutting_down = True

            # Shut down download workers before window destruction to prevent crashes
            self.central_widget.cloudcasts.download_manager.shutdown()
            QCoreApplication.processEvents()  # drain queued _emit_*_signal events

        except Exception:
            # Ignore any errors during cleanup to ensure app can exit
            pass
        finally:
            # Always accept the close event
            event.accept()
