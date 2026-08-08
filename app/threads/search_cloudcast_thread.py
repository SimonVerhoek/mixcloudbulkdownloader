"""Thread for searching Mixcloud cloudcasts."""

from PySide6.QtCore import QThread, Signal

from app.consts.messages import ERROR_NO_SEARCH_PHRASE
from app.data_classes import Cloudcast
from app.logger import log_error, log_thread
from app.services.api_service import MixcloudAPIService, api_service


class SearchCloudcastThread(QThread):
    """Thread for searching Mixcloud cloudcasts.

    This thread uses MixcloudAPIService to search for cloudcasts based on a search phrase
    and emits results as they are found.

    Attributes:
        phrase: Search term to look for
        api_service: Service for API operations with dependency injection
        error_signal: Signal emitted when an error occurs
        new_result: Signal emitted for each cloudcast found
    """

    error_signal = Signal(str)
    new_result = Signal(Cloudcast)

    phrase: str = ""

    def __init__(self, api_service: MixcloudAPIService = api_service) -> None:
        """Initialize search thread with optional service injection.

        Args:
            api_service: Service for API operations.
        """
        super().__init__()
        self.api_service = api_service

    def run(self) -> None:
        """Main thread execution method for searching cloudcasts."""
        if not self.phrase:
            log_error(ERROR_NO_SEARCH_PHRASE, "CRITICAL")
            self.error_signal.emit(ERROR_NO_SEARCH_PHRASE)
            return

        log_thread(f"Starting cloudcast search for phrase: {self.phrase}", "INFO")

        cloudcasts, error = self.api_service.search_cloudcasts(phrase=self.phrase)
        if error:
            log_error(f"Cloudcast search error: {error}", "CRITICAL")
            self.error_signal.emit(error)
            return

        for cloudcast in cloudcasts:
            if self.isInterruptionRequested():
                return
            self.new_result.emit(cloudcast)

    def stop(self) -> None:
        """Stop the search thread."""
        self.requestInterruption()
        self.wait()
