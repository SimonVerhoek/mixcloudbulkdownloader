"""Thread for fetching a single Mixcloud user or cloudcast by URL."""

from PySide6.QtCore import QThread, Signal

from app.data_classes import Cloudcast, MixcloudUser
from app.logger import log_error, log_thread
from app.services.api_service import MixcloudAPIService, api_service


class FetchByUrlThread(QThread):
    """Thread for resolving a pasted Mixcloud URL to a user or cloudcast.

    Accepts a username and optional slug. When slug is None, fetches the user
    profile; when slug is set, fetches that specific cloudcast. Emits the
    appropriate result signal or error_signal on completion.

    Attributes:
        username: Mixcloud username extracted from the pasted URL.
        slug: Cloudcast slug extracted from the pasted URL, or None for a user URL.
        api_service: Service for API operations with dependency injection.
        user_result: Signal emitted when a user profile is fetched successfully.
        cloudcast_result: Signal emitted when a cloudcast is fetched successfully.
        error_signal: Signal emitted when an error occurs.
    """

    user_result: Signal = Signal(MixcloudUser)
    cloudcast_result: Signal = Signal(Cloudcast)
    error_signal: Signal = Signal(str)

    username: str = ""
    slug: str | None = None

    def __init__(self, api_service: MixcloudAPIService = api_service) -> None:
        """Initialize fetch-by-URL thread with optional service injection.

        Args:
            api_service: Service for API operations.
        """
        super().__init__()
        self.api_service = api_service

    def run(self) -> None:
        """Main thread execution method for fetching a resource by URL."""
        if not self.username:
            error_msg = "No username provided for URL fetch"
            log_error(error_msg, "CRITICAL")
            self.error_signal.emit(error_msg)
            return

        if self.slug is None:
            log_thread(f"Fetching user profile for username: {self.username}", "INFO")
            user, error = self.api_service.get_user(username=self.username)
            if error:
                log_error(f"URL user fetch error: {error}", "CRITICAL")
                self.error_signal.emit(error)
                return
            if user is not None:
                self.user_result.emit(user)
        else:
            log_thread(
                f"Fetching cloudcast for username: {self.username}, slug: {self.slug}", "INFO"
            )
            cloudcast, error = self.api_service.get_cloudcast(
                username=self.username, slug=self.slug
            )
            if error:
                log_error(f"URL cloudcast fetch error: {error}", "CRITICAL")
                self.error_signal.emit(error)
                return
            if cloudcast is not None:
                self.cloudcast_result.emit(cloudcast)

    def stop(self) -> None:
        """Stop the fetch thread."""
        self.requestInterruption()
        self.wait()
