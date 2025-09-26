"""Startup license verification thread."""

from PySide6.QtCore import QThread

from app.qt_logger import log_error, log_thread
from app.services.license_manager import LicenseManager


class StartupVerificationThread(QThread):
    """Thread for performing startup license verification without blocking UI."""

    def __init__(self, license_manager: LicenseManager, parent=None):
        """Initialize the startup verification thread.

        Args:
            license_manager: The license manager instance to use for verification
            parent: Parent QObject
        """
        super().__init__(parent)
        self.license_manager = license_manager

    def run(self):
        """Perform startup license verification in background thread."""
        log_thread("Running startup license verification...", level="INFO")
        try:
            # Perform verification
            timeout = 10  # Short timeout for startup
            success = self.license_manager.verify_license(timeout=timeout)

            if success:
                log_thread(f"Startup license verification result: positive", level="INFO")
            else:
                log_thread(f"Startup license verification result: negative", level="INFO")

        except Exception as e:
            log_error(f"Startup verification thread error: {e}")
            # Handle same as verification failure - maintain Pro status for stored credentials
