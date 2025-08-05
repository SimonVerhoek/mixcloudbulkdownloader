"""Download service for cloudcast downloads with dependency injection."""

from typing import Callable

import yt_dlp

from app.consts import AUDIO_EXTENSION, ERROR_NO_DOWNLOAD_DIR, PROGRESS_DONE, PROGRESS_UNKNOWN


class DownloadService:
    """Service for downloading cloudcasts with injectable callbacks for testing."""

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize download service with optional callbacks.

        Args:
            progress_callback: Called with (item_name, progress_info) during downloads
            error_callback: Called with error message when errors occur
        """
        self.progress_callback = progress_callback
        self.error_callback = error_callback
        self._is_cancelled = False

    def download_cloudcasts(self, urls: list[str], directory: str) -> None:
        """Download cloudcasts to specified directory.

        Args:
            urls: List of cloudcast URLs to download
            directory: Target directory for downloads

        Raises:
            ValueError: If directory is not provided
        """
        if not directory:
            error_msg = ERROR_NO_DOWNLOAD_DIR
            if self.error_callback:
                self.error_callback(error_msg)
            raise ValueError(error_msg)

        self._is_cancelled = False

        ydl_opts = {
            "outtmpl": f"{directory}/%(uploader_id)s - %(title)s.%(ext)s",
            "progress_hooks": [self._track_progress],
            "verbose": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)
        except Exception as e:
            if self.error_callback and not self._is_cancelled:
                self.error_callback(f"Download failed: {str(e)}")
            raise

    def download_single_cloudcast(self, url: str, directory: str) -> None:
        """Download a single cloudcast.

        Args:
            url: Cloudcast URL to download
            directory: Target directory for download
        """
        self.download_cloudcasts([url], directory)

    def cancel_downloads(self) -> None:
        """Cancel ongoing downloads."""
        self._is_cancelled = True

    def set_progress_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set the progress callback function.

        Args:
            callback: Function to call with (item_name, progress_info)
        """
        self.progress_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set the error callback function.

        Args:
            callback: Function to call with error messages
        """
        self.error_callback = callback

    def _track_progress(self, progress_data: dict) -> None:
        """Track download progress and call progress callback.

        Args:
            progress_data: Progress dictionary from yt-dlp
        """
        if self._is_cancelled or not self.progress_callback:
            return

        try:
            # Extract clean item name from filename
            filename = progress_data.get("filename", "")
            if not filename:
                return

            # Get just the filename without path and extension
            import os

            base_filename = os.path.basename(filename)

            # Remove file extension (e.g., .webm, .mp3, etc.)
            if "." in base_filename:
                item_name = base_filename.rsplit(".", 1)[0]
            else:
                item_name = base_filename

            # Remove temporary filename parts if present
            tmpfilename = progress_data.get("tmpfilename", "")
            if tmpfilename:
                tmp_base = os.path.basename(tmpfilename)
                item_name = item_name.replace(tmp_base, "").strip()

            # Determine progress status
            progress = PROGRESS_UNKNOWN
            status = progress_data.get("status", "")

            if status == "downloading":
                # Build progress string from available data
                percent = progress_data.get("_percent_str", "?%")
                total_bytes = progress_data.get("_total_bytes_estimate_str", "N/A")
                speed = progress_data.get("_speed_str", "N/A")
                progress = f"{percent} of {total_bytes} at {speed}"
            elif status == "finished":
                progress = PROGRESS_DONE
            elif status == "error":
                progress = "Error occurred"

            self.progress_callback(item_name, progress)

        except Exception:
            # Don't let progress tracking errors break downloads
            if self.progress_callback:
                self.progress_callback("Unknown", PROGRESS_UNKNOWN)

    def create_download_options(self, directory: str, custom_template: str | None = None) -> dict:
        """Create yt-dlp options dictionary.

        Args:
            directory: Target download directory
            custom_template: Optional custom filename template

        Returns:
            Dictionary of yt-dlp options
        """
        template = custom_template or "%(uploader)s - %(title)s.%(ext)s"

        return {
            "outtmpl": f"{directory}/{template}",
            "progress_hooks": [self._track_progress],
            "verbose": False,
        }

    @property
    def is_cancelled(self) -> bool:
        """Check if downloads have been cancelled."""
        return self._is_cancelled
