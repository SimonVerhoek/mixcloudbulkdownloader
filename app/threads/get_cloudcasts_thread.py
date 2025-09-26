"""Thread for fetching cloudcasts from a user's profile."""

from PySide6.QtCore import QThread, Signal

from app.consts.messages import ERROR_NO_USER_PROVIDED
from app.data_classes import Cloudcast, MixcloudUser
from app.qt_logger import log_error, log_thread
from app.services.api_service import MixcloudAPIService, api_service


class GetCloudcastsThread(QThread):
    """Thread for fetching cloudcasts from a user's profile.

    This thread uses the MixcloudAPIService to retrieve all cloudcasts for a given user,
    handling pagination automatically.

    Attributes:
        user: MixcloudUser whose cloudcasts to fetch
        api_service: Service for API operations with dependency injection
        error_signal: Signal emitted when an error occurs
        interrupt_signal: Signal emitted when operation is interrupted
        new_result: Signal emitted for each cloudcast found
    """

    error_signal = Signal(str)
    interrupt_signal = Signal()
    new_result = Signal(Cloudcast)

    user: MixcloudUser | None = None

    def __init__(self, api_service: MixcloudAPIService = api_service) -> None:
        """Initialize cloudcasts thread with optional service injection.

        Args:
            api_service: Service for API operations.
        """
        super().__init__()
        self.api_service = api_service

    def _query_cloudcasts(self, user: MixcloudUser, url: str = "") -> None:
        """Query cloudcasts from API, handling pagination recursively.

        Args:
            user: The user whose cloudcasts to fetch
            url: API URL to query (if empty, generates from username)
        """
        if self.isInterruptionRequested():
            return

        if not url:
            cloudcasts, error, next_url = self.api_service.get_user_cloudcasts(user.username)
        else:
            cloudcasts, error, next_url = self.api_service.get_next_cloudcasts_page(url)

        if error:
            log_error(f"Cloudcasts query error: {error}", "CRITICAL")
            self.error_signal.emit(error)
            return

        # Emit each cloudcast as a result
        for cloudcast in cloudcasts:
            if self.isInterruptionRequested():
                return
            self.new_result.emit(cloudcast)

        # Handle pagination - recursively fetch next page if available
        if next_url and not self.isInterruptionRequested():
            self._query_cloudcasts(user, next_url)

    def run(self) -> None:
        """Main thread execution method for fetching cloudcasts."""
        if not self.user:
            log_error(ERROR_NO_USER_PROVIDED, "CRITICAL")
            self.error_signal.emit(ERROR_NO_USER_PROVIDED)
            return

        log_thread(f"Starting cloudcast fetch for user: {self.user.username}", "INFO")
        self._query_cloudcasts(user=self.user)

    def stop(self) -> None:
        """Stop the cloudcast fetching thread."""
        self.requestInterruption()
        self.interrupt_signal.emit()
        self.wait()
