"""Startup license verification thread."""

from PySide6.QtCore import QThread, Signal

from app.qt_logger import log_error


class StartupVerificationThread(QThread):
    """Thread for performing startup license verification without blocking UI."""

    verification_completed = Signal(bool, bool)  # (success, notify_user)

    def __init__(self, license_manager, parent=None):
        """Initialize the startup verification thread.

        Args:
            license_manager: The license manager instance to use for verification
            parent: Parent QObject
        """
        super().__init__(parent)
        self.license_manager = license_manager

    def run(self):
        """Perform startup license verification in background thread."""
        try:
            # Check if credentials exist
            email = self.license_manager.settings.email
            license_key = self.license_manager.settings.license_key

            if not email or not license_key:
                # No credentials exist - first run experience
                self.verification_completed.emit(False, False)
                return

            # Perform verification
            success = self.license_manager.verify_license(
                email=email, license_key=license_key, timeout=10  # Short timeout for startup
            )

            if success:
                # Verification succeeded
                self.verification_completed.emit(True, False)
            else:
                # Verification failed - check last successful verification
                last_success = self.license_manager.settings.last_successful_verification
                if last_success:
                    # Have previous successful verification - use offline grace period
                    self.license_manager.is_pro = True
                    log_error("Startup license verification failed but using offline grace period")
                    self.verification_completed.emit(False, False)  # Don't notify user
                else:
                    # No previous successful verification - notify user
                    self.license_manager.is_pro = False
                    self.verification_completed.emit(False, True)  # Notify user

        except Exception as e:
            log_error(f"Startup verification thread error: {e}")
            # Handle same as verification failure
            last_success = self.license_manager.settings.last_successful_verification
            if last_success:
                self.license_manager.is_pro = True
                self.verification_completed.emit(False, False)
            else:
                self.license_manager.is_pro = False
                self.verification_completed.emit(False, True)
