"""Threading classes for background operations in Mixcloud Bulk Downloader."""

from PySide6.QtCore import QThread, Signal

from app.consts import ERROR_NO_SEARCH_PHRASE, ERROR_NO_USER_PROVIDED
from app.data_classes import Cloudcast, MixcloudUser
from app.services.api_service import MixcloudAPIService
from app.services.download_service import DownloadService


# from .logging import logging
# logger = logging.getLogger(__name__)


class DownloadThread(QThread):
    """Thread for downloading cloudcasts in the background.

    This thread handles the actual downloading of selected cloudcasts using
    the DownloadService, providing progress updates through Qt signals.

    Attributes:
        urls: List of cloudcast URLs to download
        download_dir: Directory path where files should be saved
        download_service: Service for handling downloads with dependency injection
        progress_signal: Signal emitted with (item_name, progress_info)
        interrupt_signal: Signal emitted when download is interrupted
        error_signal: Signal emitted when an error occurs
    """

    urls: list[str] = []
    download_dir: str | None = None

    progress_signal = Signal(str, str)
    interrupt_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, download_service: DownloadService | None = None) -> None:
        """Initialize download thread with optional service injection.

        Args:
            download_service: Service for handling downloads. If None, creates default.
        """
        super().__init__()
        self.download_service = download_service or DownloadService()

        # Set up service callbacks to emit signals
        self.download_service.set_progress_callback(self.progress_signal.emit)
        self.download_service.set_error_callback(self.error_signal.emit)

    def run(self) -> None:
        """Main thread execution method for downloading cloudcasts."""
        try:
            self.download_service.download_cloudcasts(self.urls, self.download_dir)
        except Exception as e:
            self.error_signal.emit(str(e))

    def stop(self) -> None:
        """Stop the download thread and emit interrupt signal."""
        self.download_service.cancel_downloads()
        self.terminate()
        self.interrupt_signal.emit()
        self.wait()


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

    def __init__(self, api_service: MixcloudAPIService | None = None) -> None:
        """Initialize cloudcasts thread with optional service injection.

        Args:
            api_service: Service for API operations. If None, creates default.
        """
        super().__init__()
        self.api_service = api_service or MixcloudAPIService()

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
            self.error_signal.emit(ERROR_NO_USER_PROVIDED)
            return

        self._query_cloudcasts(user=self.user)

    def stop(self) -> None:
        """Stop the cloudcast fetching thread."""
        self.requestInterruption()
        self.interrupt_signal.emit()
        self.wait()


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

    def __init__(self, api_service: MixcloudAPIService | None = None) -> None:
        """Initialize search thread with optional service injection.

        Args:
            api_service: Service for API operations. If None, creates default.
        """
        super().__init__()
        self.api_service = api_service or MixcloudAPIService()

    def show_suggestions(self, phrase: str) -> None:
        """Search for users and emit results.

        Args:
            phrase: Search term to look for users
        """
        users, error = self.api_service.search_users(phrase)
        if error:
            self.error_signal.emit(error)
            return

        for user in users:
            if self.isInterruptionRequested():
                return
            self.new_result.emit(user)

    def run(self) -> None:
        """Main thread execution method for searching users."""
        if not self.phrase:
            self.error_signal.emit(ERROR_NO_SEARCH_PHRASE)
            return

        self.show_suggestions(phrase=self.phrase)

    def stop(self) -> None:
        """Stop the search thread."""
        self.requestInterruption()
        self.wait()
