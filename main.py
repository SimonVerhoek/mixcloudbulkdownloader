"""Main application entry point for Mixcloud Bulk Downloader."""

import sys

from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
)

from app.consts import (MAIN_WINDOW_MIN_HEIGHT, MAIN_WINDOW_MIN_WIDTH)
from app.custom_widgets.central_widget import CentralWidget
from app.custom_widgets.dialogs.settings_dialog import SettingsDialog
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.qt_logger import log_ui, QtLogger
from app.services.license_manager import license_manager
from app.services.settings_manager import settings
from app.styles import load_application_styles
from app.threads.startup_verification_thread import StartupVerificationThread


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

        widget = CentralWidget(license_manager=self.license_manager)
        self.central_widget = widget

        self.setWindowTitle("Mixcloud Bulk Downloader")
        self.setMinimumSize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)

        # Create menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        
        # Add Settings menu item (only if feature flag is enabled)
        if self.settings.settings_pane_enabled:
            file_menu.addAction("Settings...", self._show_settings_dialog)
            file_menu.addSeparator()
        
        # Add Get MBD Pro menu item (only shown for non-Pro users)
        self.get_mbd_pro_action = file_menu.addAction("Get MBD Pro...", self._show_get_pro_dialog)
        file_menu.addSeparator()
        
        file_menu.addAction("Exit", QApplication.quit)

        self.setCentralWidget(widget)
        
        # Initialize Pro UI state
        self.refresh_pro_ui_elements()
        
        # Perform startup license verification
        self.startup_license_verification()

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
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec()

    def _show_get_pro_dialog(self) -> None:
        """Show the Get Pro dialog from the menu."""
        dialog = GetProDialog(self)
        result = dialog.exec()
        if result:  # Dialog accepted (successful verification)
            self.refresh_pro_ui_elements()

    def refresh_pro_ui_elements(self) -> None:
        """Refresh Pro UI elements based on current license status."""
        # Update central widget Pro elements
        if hasattr(self, 'central_widget'):
            self.central_widget.refresh_pro_ui_elements()
        
        # Update menu items
        self.update_menu_items()

    def update_menu_items(self) -> None:
        """Update menu items visibility based on Pro status."""
        is_pro = self.license_manager.is_pro
        
        # Show/hide Get MBD Pro menu item based on Pro status
        if hasattr(self, 'get_mbd_pro_action'):
            self.get_mbd_pro_action.setVisible(not is_pro)

    def startup_license_verification(self) -> None:
        """Perform startup license verification in background thread."""
        self.verification_thread = StartupVerificationThread(self.license_manager, self)
        self.verification_thread.verification_completed.connect(self._handle_startup_verification_result)
        self.verification_thread.start()

    def _handle_startup_verification_result(self, success: bool, notify_user: bool) -> None:
        """Handle the result of startup license verification.
        
        Args:
            success: Whether verification was successful
            notify_user: Whether to notify user of verification failure
        """
        from app.custom_widgets.dialogs.error_dialog import ErrorDialog
        
        # Refresh UI elements based on new Pro status
        self.refresh_pro_ui_elements()
        
        # Notify user if needed (first-time verification failure)
        if notify_user:
            ErrorDialog(
                self, 
                message="License verification failed. Some features may be limited. "
                       "Check your internet connection and license credentials."
            )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle application close event with proper cleanup."""
        try:
            # Stop any running verification threads
            if hasattr(self, 'verification_thread') and self.verification_thread.isRunning():
                self.verification_thread.terminate()
                self.verification_thread.wait(1000)  # Wait up to 1 second
            
            # Disable keyring operations during shutdown to prevent crash
            if hasattr(self, 'license_manager') and hasattr(self.license_manager, 'settings'):
                # Mark settings as shutting down to prevent keyring access
                self.license_manager.settings._shutting_down = True
                
        except Exception:
            # Ignore any errors during cleanup to ensure app can exit
            pass
        finally:
            # Always accept the close event
            event.accept()


def main() -> None:
    """Main application entry point."""
    try:
        application = QApplication(sys.argv)
        
        # Initialize Qt logging system after QApplication
        qt_logger = QtLogger()
        log_ui("Application starting up", "INFO")

        # Load application stylesheets
        log_ui("Loading application styles", "INFO")
        load_application_styles(application)

        log_ui("Creating main window", "INFO")
        window = MainWindow()
        window.show()
        window.activateWindow()
        window.raise_()
        
        log_ui("Application ready", "INFO")
        sys.exit(application.exec())
    except Exception as e:
        # Fallback error handling for bundled apps
        import traceback
        error_msg = f"""
            Application startup error: {e}\n
            {traceback.format_exc()}
        """
        
        # Try to write to log file directly if Qt logging fails
        try:
            from pathlib import Path
            log_dir = Path.home() / "Library" / "Logs" / "MixcloudBulkDownloader"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "crash.log", "w") as f:
                f.write(error_msg)
        except:
            pass
            
        # Also output to stderr
        sys.stderr.write(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
