"""Thread for downloading application updates with progress tracking."""

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.qt_logger import log_error_with_traceback, log_thread
from app.services.update_service import UpdateService


class UpdateDownloadThread(QThread):
    """Thread for downloading update files with thread-safe progress signals.

    This thread downloads application updates using httpx streaming with real-time
    progress tracking and platform-specific file reveal functionality.

    Attributes:
        download_progress: Signal emitted with download progress (0-100)
        download_finished: Signal emitted with downloaded file path
        error_occurred: Signal emitted with error message
    """

    download_progress = Signal(int)  # 0-100 progress
    download_finished = Signal(str)  # file path
    error_occurred = Signal(str)  # error message

    def __init__(
        self, download_url: str, target_path: str, update_service: UpdateService, parent=None
    ) -> None:
        """Initialize download thread with download parameters.

        Args:
            download_url: URL to download the update file from
            target_path: Full path where the file should be saved
            update_service: Service instance for HTTP operations
            parent: Parent QObject
        """
        super().__init__(parent)
        self.download_url = download_url
        self.target_path = Path(target_path)
        self.update_service = update_service

    def run(self) -> None:
        """Main thread execution method for downloading updates."""
        log_thread(f"Starting download: {self.target_path.name}", "INFO")

        try:
            log_thread(f"Download target: {self.target_path}", "INFO")

            # Ensure target directory exists
            self.target_path.parent.mkdir(parents=True, exist_ok=True)

            with self.update_service.stream(
                "GET", self.download_url, follow_redirects=True
            ) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                log_thread(f"File size: {total_size} bytes", "INFO")

                with open(self.target_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        if self.isInterruptionRequested():  # Handle cancellation
                            log_thread("Download cancelled by user", "INFO")
                            # Clean up partial file
                            if self.target_path.exists():
                                self.target_path.unlink()
                            return

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                self.download_progress.emit(progress)  # Thread-safe signal

            log_thread(f"Download completed: {self.target_path}", "INFO")
            self.download_finished.emit(str(self.target_path))  # Thread-safe signal

        except Exception as e:
            log_error_with_traceback(f"Download error: {e}")
            self.error_occurred.emit(str(e))  # Thread-safe signal

    def reveal_file(self, file_path: str) -> None:
        """Reveal downloaded file in system file manager.

        Args:
            file_path: Path to the file to reveal
        """
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", file_path], check=True)
            elif sys.platform.startswith("win"):
                subprocess.run(["explorer", "/select,", file_path], check=True)
        except subprocess.CalledProcessError as e:
            log_error_with_traceback(f"Failed to reveal file: {e}")
            # Don't emit error signal here as this is a non-critical failure

    def stop(self) -> None:
        """Stop the download thread with timeout to prevent hanging."""
        self.requestInterruption()
        if not self.wait(5000):  # 5 second timeout
            log_thread("Download thread did not stop within 5 seconds, terminating...", "WARNING")
            self.terminate()
            self.wait(1000)  # Wait 1 more second for termination
