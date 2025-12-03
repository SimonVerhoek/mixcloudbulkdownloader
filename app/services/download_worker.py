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
from app.qt_logger import log_error_with_traceback
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager
from app.utils.yt_dlp import QuietLogger, get_stable_size_estimate


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
        license_manager: LicenseManager,
    ):
        """Initialize download worker.

        Args:
            cloudcast: Cloudcast to download
            download_dir: Target download directory
            callback_bridge: Thread-safe signal emission bridge
            settings_manager: Settings manager for configuration
            license_manager: License manager for configuration
        """
        super().__init__()
        self.cloudcast = cloudcast
        self.download_dir = download_dir
        self.callback_bridge = callback_bridge
        self.settings_manager = settings_manager
        self.license_manager = license_manager
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

            # Generate yt-dlp options (initially with placeholder path)
            ydl_opts = self._generate_ydl_opts()

            # Execute download with format detection
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First extract format info to determine actual extension
                try:
                    info = ydl.extract_info(self.cloudcast.url, download=False)

                    actual_extension = info.get("ext", "webm")

                    # Update filenames with correct extension
                    self._update_filenames_with_extension(extension=actual_extension)

                    # Update yt-dlp output template with correct path
                    ydl.params["outtmpl"]["default"] = str(self.download_file_path)

                except Exception as format_error:
                    # If format detection fails, fall back to webm and continue
                    log_error_with_traceback(
                        message=f"Format detection failed for {self.cloudcast.url}: {format_error}",
                        level="WARNING",
                    )
                    # Filenames already default to .webm, so continue with those

                # Now perform the actual download
                ydl.download([self.cloudcast.url])

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
                log_error_with_traceback(message=error_msg, level="ERROR")
                self.callback_bridge.emit_error(
                    self.cloudcast.url, f"Download failed: {error_msg}", "download"
                )
            self._cleanup()

        except Exception as e:
            log_error_with_traceback(message=str(e), level="ERROR")
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

    def _update_filenames_with_extension(self, extension: str) -> None:
        """Update filenames with the actual file extension from format detection.

        Args:
            extension: File extension (e.g., 'webm', 'm4a', 'mp3')
        """
        # Fallback to webm if extension is empty or None
        if not extension or not extension.strip():
            extension = "webm"

        # Remove any leading dots and ensure clean extension
        extension = extension.strip().lstrip(".")

        # Update filenames with correct extension
        self.downloading_filename = (
            f"{self.cloudcast.user.name} - {self.safe_title}.{extension}.downloading"
        )
        self.final_filename = f"{self.cloudcast.user.name} - {self.safe_title}.{extension}"

        # Update file paths
        self.download_file_path = Path(self.download_dir) / self.downloading_filename
        self.final_file_path = Path(self.download_dir) / self.final_filename

    def _generate_ydl_opts(self) -> dict:
        """Generate yt-dlp options with progress hooks and cancellation support."""

        # Use utility functions instead of inline definitions
        def progress_hook(progress_data: dict):
            """Handle yt-dlp progress updates with stable size estimates."""
            if self.cancelled:
                self._immediate_cleanup()
                raise yt_dlp.utils.DownloadError("Download cancelled by user")

            status = progress_data.get("status", "")
            if status == "downloading":
                percent_str = progress_data.get("_percent_str", "0%")
                speed_str = progress_data.get("_speed_str", "")
                total_str = progress_data.get("_total_bytes_estimate_str", "")
                bitrate: int | float = progress_data["info_dict"].get("abr")

                # lowest quality abr often has value None, but is actually 64kbps. So just show that instead
                if not bitrate:
                    bitrate = 64

                progress_text = f"{DOWNLOAD_ICON} [{bitrate:.0f}kbps] {percent_str}"
                if speed_str:
                    progress_text += f" at {speed_str}"

                # Add stable size estimate
                if total_str:
                    stable_size = get_stable_size_estimate(total_str)
                    if stable_size:
                        progress_text += f" ({stable_size})"

                self.callback_bridge.emit_progress(self.cloudcast.url, progress_text, "download")

            elif status == "finished":
                self.callback_bridge.emit_progress(
                    self.cloudcast.url, f"{DOWNLOAD_ICON} Complete", "download"
                )

        audio_format = "bestaudio/best" if self.license_manager.is_pro else "worstaudio/worst"

        return {
            "outtmpl": str(self.download_file_path),
            "progress_hooks": [progress_hook],
            "verbose": False,
            "quiet": True,
            "no_warnings": True,
            "logger": QuietLogger(),
            "format": audio_format,
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

            # Extract base name by removing .downloading extension
            # Works with any extension (e.g., .webm.downloading, .m4a.downloading)
            base_name = self.downloading_filename.replace(".downloading", "")
            base_name = base_name.rsplit(".", 1)[0]  # Remove the extension part

            # Remove fragment files - use broader patterns to catch any extension
            for pattern in [
                f"{base_name}*.part",
                f"{base_name}*.part-Frag*",
                f"{base_name}*.*part*",  # Catch any extension with .part
            ]:
                for fragment_file in download_dir.glob(pattern):
                    try:
                        if fragment_file.is_file():
                            fragment_file.unlink()
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
