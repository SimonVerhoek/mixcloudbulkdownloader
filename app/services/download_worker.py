"""Download worker implementation using proper PyQt threading patterns.

This module provides DownloadWorker that uses QRunnable with thread-safe
signal emission through CallbackBridge, avoiding Qt threading violations.
"""

import re
import unicodedata
from pathlib import Path

import yt_dlp
from PySide6.QtCore import QRunnable

from app.consts.ui import CANCELLED_ICON, DOWNLOAD_ICON
from app.data_classes import Cloudcast
from app.services.settings_manager import SettingsManager


class DownloadCancelled(Exception):
    """Exception raised when download is cancelled."""

    pass


class DownloadWorker(QRunnable):
    """QRunnable worker for downloading cloudcasts using yt-dlp.

    This class implements the download functionality using proper PyQt patterns:
    - Inherits from QRunnable for thread pool execution
    - Uses CallbackBridge for thread-safe signal emission
    - Follows existing file naming conventions
    - Maintains compatibility with existing progress display patterns
    """

    def __init__(
        self,
        cloudcast: Cloudcast,
        download_dir: str,
        callback_bridge: "CallbackBridge",
        settings_manager: SettingsManager,
    ):
        """Initialize download worker.

        Args:
            cloudcast: Cloudcast to download
            download_dir: Target download directory
            callback_bridge: Thread-safe signal emission bridge
            settings_manager: Settings manager for configuration
        """
        super().__init__()
        self.cloudcast = cloudcast
        self.download_dir = download_dir
        self.callback_bridge = callback_bridge
        self.settings_manager = settings_manager
        self.cancelled = False

        # Set up file paths using existing naming convention
        self.safe_title = self._sanitize_filename(cloudcast.name)
        self.downloading_filename = f"{cloudcast.user.name} - {self.safe_title}.webm.downloading"
        self.final_filename = f"{cloudcast.user.name} - {self.safe_title}.webm"

        self.download_file_path = Path(download_dir) / self.downloading_filename
        self.final_file_path = Path(download_dir) / self.final_filename

    def run(self):
        """Execute the download task."""
        try:
            if self.cancelled:
                raise DownloadCancelled("Download cancelled before start")

            # Generate yt-dlp options
            ydl_opts = self._generate_ydl_opts()

            # Execute download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.cloudcast.url, download=True)

                # Atomically rename from .downloading to final name
                if self.download_file_path.exists():
                    self.download_file_path.rename(self.final_file_path)

                    if not self.cancelled:
                        self.callback_bridge.emit_completed(
                            self.cloudcast.url, str(self.final_file_path), "download"
                        )
                else:
                    raise RuntimeError(f"Download file not found: {self.download_file_path}")

        except DownloadCancelled:
            # Emit cancellation signal and clean up
            self.callback_bridge.emit_progress(
                self.cloudcast.url, f"{CANCELLED_ICON} Cancelled", "download"
            )
            self._cleanup()

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            # Check if this was a user cancellation
            if any(
                phrase in error_msg
                for phrase in [
                    "cancelled by user",
                    "The downloaded file is empty",
                    "No such file or directory",
                ]
            ):
                self.callback_bridge.emit_progress(
                    self.cloudcast.url, f"{CANCELLED_ICON} Cancelled", "download"
                )
            else:
                self.callback_bridge.emit_error(
                    self.cloudcast.url, f"Download failed: {error_msg}", "download"
                )
            self._cleanup()

        except Exception as e:
            self.callback_bridge.emit_error(
                self.cloudcast.url, f"Download failed: {str(e)}", "download"
            )
            self._cleanup()

    def cancel(self):
        """Cancel the download operation."""
        self.cancelled = True
        # Clean up immediately
        self._immediate_cleanup()

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for filesystem compatibility.

        Args:
            name: Raw filename to sanitize

        Returns:
            Sanitized filename safe for filesystem use
        """

        # Unicode normalization
        normalized = unicodedata.normalize("NFKC", name)

        # Convert accented characters to ASCII equivalents
        ascii_normalized = ""
        for char in normalized:
            if ord(char) < 128:
                ascii_normalized += char
            else:
                # Try to decompose and extract base character
                decomposed = unicodedata.normalize("NFD", char)
                for component in decomposed:
                    if ord(component) < 128:
                        ascii_normalized += component
                        break

        # Remove problematic filesystem characters
        cleaned = re.sub(r'[<>"/\\|?*]', "", ascii_normalized)

        # Replace multiple spaces with single space
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _generate_ydl_opts(self) -> dict:
        """Generate yt-dlp options with progress hooks and cancellation support."""

        def progress_hook(progress_data: dict):
            """Handle yt-dlp progress updates."""
            if self.cancelled:
                self._immediate_cleanup()
                raise yt_dlp.utils.DownloadError("Download cancelled by user")

            status = progress_data.get("status", "")
            if status == "downloading":
                percent_str = progress_data.get("_percent_str", "0%")
                speed_str = progress_data.get("_speed_str", "")
                total_str = progress_data.get("_total_bytes_estimate_str", "")

                progress_text = f"{DOWNLOAD_ICON} {percent_str}"
                if speed_str:
                    progress_text += f" at {speed_str}"
                if total_str:
                    progress_text += f" ({total_str})"

                self.callback_bridge.emit_progress(self.cloudcast.url, progress_text, "download")
            elif status == "finished":
                self.callback_bridge.emit_progress(
                    self.cloudcast.url, f"{DOWNLOAD_ICON} Complete", "download"
                )

        class QuietLogger:
            """Custom logger that suppresses yt-dlp output."""

            def debug(self, msg):
                pass

            def info(self, msg):
                pass

            def warning(self, msg):
                pass

            def error(self, msg):
                pass

        return {
            "outtmpl": str(self.download_file_path),
            "progress_hooks": [progress_hook],
            "verbose": False,
            "quiet": True,
            "no_warnings": True,
            "logger": QuietLogger(),
            "format": "bestaudio/best",
            "abort_on_error": True,
            "no_continue": True,
            "retries": 0,
            "fragment_retries": 0,
            "postprocessors": [],
        }

    def _cleanup(self):
        """Clean up partial download files."""
        try:
            # Remove main downloading file
            if self.download_file_path.exists():
                self.download_file_path.unlink()

            # Clean up fragment files
            self._cleanup_fragments()
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors

    def _immediate_cleanup(self):
        """Immediately remove downloading files to stop yt-dlp."""
        try:
            if self.download_file_path.exists():
                self.download_file_path.unlink()
        except (OSError, PermissionError):
            pass

        self._cleanup_fragments()

    def _cleanup_fragments(self):
        """Clean up yt-dlp fragment files."""
        try:
            download_dir = Path(self.download_dir)
            if not download_dir.exists():
                return

            base_name = self.downloading_filename.replace(".webm.downloading", "")

            # Remove fragment files
            for pattern in [
                f"{base_name}*.part",
                f"{base_name}*.part-Frag*",
                f"{base_name}*.webm.part*",
            ]:
                for fragment_file in download_dir.glob(pattern):
                    try:
                        if fragment_file.is_file():
                            fragment_file.unlink()
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
