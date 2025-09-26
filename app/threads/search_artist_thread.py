"""Thread for searching Mixcloud users/artists."""

from PySide6.QtCore import QThread, Signal

from app.consts.messages import ERROR_NO_SEARCH_PHRASE
from app.data_classes import MixcloudUser
from app.qt_logger import log_error, log_thread
from app.services.api_service import MixcloudAPIService, api_service


class SearchArtistThread(QThread):
    """Thread for searching Mixcloud users/artists.

    This thread uses MixcloudAPIService to search for users based on a search phrase
    and emits results as they are found.

    Attributes:
        phrase: Search term to look for
        api_service: Service for API operations with dependency injection
        error_signal: Signal emitted when an error occurs
        new_result: Signal emitted for each user found
    """

    error_signal = Signal(str)
    new_result = Signal(MixcloudUser)

    phrase: str = ""

    def __init__(self, api_service: MixcloudAPIService = api_service) -> None:
        """Initialize search thread with optional service injection.

        Args:
            api_service: Service for API operations.
        """
        super().__init__()
        self.api_service = api_service

    def show_suggestions(self, phrase: str) -> None:
        """Search for users and emit results.

        Args:
            phrase: Search term to look for users
        """
        users, error = self.api_service.search_users(phrase)
        if error:
            log_error(f"User search error: {error}", "CRITICAL")
            self.error_signal.emit(error)
            return

        for user in users:
            if self.isInterruptionRequested():
                return
            self.new_result.emit(user)

    def run(self) -> None:
        """Main thread execution method for searching users."""
        if not self.phrase:
            log_error(ERROR_NO_SEARCH_PHRASE, "CRITICAL")
            self.error_signal.emit(ERROR_NO_SEARCH_PHRASE)
            return

        log_thread(f"Starting user search for phrase: {self.phrase}", "INFO")
        self.show_suggestions(phrase=self.phrase)

    def stop(self) -> None:
        """Stop the search thread."""
        self.requestInterruption()
        self.wait()
