"""Thread for checking application updates from GitHub releases."""

from PySide6.QtCore import QCoreApplication, QThread, Signal

from app.data_classes import GitHubRelease
from app.qt_logger import log_error, log_thread
from app.services.update_service import UpdateService, update_service
from app.utils.version import compare_versions, normalize_version_tag


class UpdateCheckThread(QThread):
    """Thread for checking application updates from GitHub releases.

    This thread uses UpdateService to check for new releases and compares them
    with the current application version to determine if updates are available.

    Attributes:
        update_service: Service for GitHub API operations with dependency injection
        update_available: Signal emitted when an update is found
        no_update_available: Signal emitted when no update is found
        error_signal: Signal emitted when an error occurs
    """

    # Signal parameters: current_version, latest_version, download_url, release_notes
    update_available = Signal(str, str, str, str)
    no_update_available = Signal()
    error_signal = Signal(str)

    def __init__(self, update_service_instance: UpdateService = update_service) -> None:
        """Initialize update check thread with optional service injection.

        Args:
            update_service_instance: Service for GitHub API operations.
        """
        super().__init__()
        self.update_service = update_service_instance

    def run(self) -> None:
        """Main thread execution method for checking updates."""
        log_thread("Starting update check...", "INFO")

        try:
            # Get current version
            current_version = QCoreApplication.applicationVersion()
            log_thread(f"Current version: {current_version}", "INFO")

            # Check for updates
            release, error = self.update_service.check_for_updates()

            if error:
                # Handle rate limiting silently (don't show error dialogs to users)
                if error == "RATE_LIMITED":
                    log_thread("Update check skipped due to GitHub rate limiting", "INFO")
                    return  # Silent return, no error signal

                log_error(f"Update check error: {error}", "CRITICAL")
                self.error_signal.emit(error)
                return

            if not release:
                log_thread("No suitable release found", "INFO")
                self.no_update_available.emit()
                return

            # Compare versions
            latest_version = normalize_version_tag(release.tag_name)
            log_thread(f"Latest version: {latest_version}", "INFO")

            if self.isInterruptionRequested():
                return

            if compare_versions(current_version, latest_version):
                # Update available - get download URL
                download_url = self.update_service.get_platform_asset(release.assets)
                if download_url:
                    log_thread(f"Update available: {current_version} → {latest_version}", "INFO")
                    self.update_available.emit(
                        current_version, latest_version, download_url, release.body
                    )
                else:
                    log_error("No suitable download found for platform", "ERROR")
                    self.error_signal.emit("No suitable download found for your platform")
            else:
                log_thread("Application is up to date", "INFO")
                self.no_update_available.emit()

        except Exception as e:
            log_error(f"Update check thread error: {e}", "CRITICAL")
            self.error_signal.emit(f"Update check failed: {str(e)}")

    def stop(self) -> None:
        """Stop the update check thread."""
        self.requestInterruption()
        self.wait()
