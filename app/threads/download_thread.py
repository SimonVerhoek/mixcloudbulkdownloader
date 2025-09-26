"""Download thread for background cloudcast downloading."""

from PySide6.QtCore import QThread, Signal

from app.qt_logger import log_error, log_error_with_traceback, log_thread
from app.services.download_service import DownloadService, download_service


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
        completion_signal: Signal emitted when all downloads complete successfully
    """

    urls: list[str] = []
    download_dir: str | None = None

    progress_signal = Signal(str, str)
    interrupt_signal = Signal()
    error_signal = Signal(str)
    completion_signal = Signal()

    def __init__(self, download_service: DownloadService = download_service) -> None:
        """Initialize download thread with optional service injection.

        Args:
            download_service: Service for handling downloads.
        """
        super().__init__()
        self.download_service = download_service

        # Set up service callbacks to emit signals
        self.download_service.set_progress_callback(self.progress_signal.emit)
        self.download_service.set_error_callback(self.error_signal.emit)

    def run(self) -> None:
        """Main thread execution method for downloading cloudcasts."""
        log_thread(f"Starting download of {len(self.urls)} cloudcasts", "INFO")
        try:
            self.download_service.download_cloudcasts(self.urls, self.download_dir)
            log_thread("Download completed successfully", "INFO")
            self.completion_signal.emit()
        except Exception as e:
            log_error_with_traceback(f"Download thread error: {str(e)}", "CRITICAL")
            self.error_signal.emit(str(e))

    def stop(self) -> None:
        """Stop the download thread and emit interrupt signal."""
        log_thread("Stopping download thread...", "INFO")
        self.download_service.cancel_downloads()
        self.terminate()
        self.interrupt_signal.emit()
        self.wait()
        log_thread("Download thread stopped", "INFO")
