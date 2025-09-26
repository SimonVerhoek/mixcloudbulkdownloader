"""Download service for cloudcast downloads with dependency injection."""

import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Callable

import yt_dlp
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from app.consts.audio import AUDIO_FORMATS
from app.consts.messages import ERROR_NO_DOWNLOAD_DIR, PROGRESS_DONE, PROGRESS_UNKNOWN
from app.qt_logger import log_error_with_traceback, log_thread, log_ui
from app.services.license_manager import LicenseManager, license_manager
from app.services.settings_manager import SettingsManager, settings


class DownloadService:
    """Service for downloading cloudcasts with injectable callbacks for testing."""

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
        license_manager: LicenseManager = license_manager,
        settings_manager: SettingsManager = settings,
    ) -> None:
        """Initialize download service with optional callbacks.

        Args:
            progress_callback: Called with (item_name, progress_info) during downloads
            error_callback: Called with error message when errors occur
            license_manager: License manager for Pro status checking
            settings_manager: Settings manager for preference persistence
        """
        self.progress_callback = progress_callback
        self.error_callback = error_callback
        self.license_manager = license_manager
        self.settings_manager = settings_manager
        self._is_cancelled = False

    def download_cloudcasts(
        self, urls: list[str], directory: str | None = None, parent_widget: QWidget | None = None
    ) -> None:
        """Download cloudcasts to specified directory with intelligent format detection.

        Args:
            urls: List of cloudcast URLs to download
            directory: Target directory for downloads. If None, uses Pro default or shows picker.
            parent_widget: Parent widget for dialogs

        Raises:
            ValueError: If directory cannot be determined
        """
        # Handle different directory input cases
        if directory is None:
            # None means use Pro features to get directory
            directory = self.get_download_directory_with_default_prompt(parent_widget)
        elif directory == "":
            # Empty string is invalid input - fail immediately
            error_msg = ERROR_NO_DOWNLOAD_DIR
            if self.error_callback:
                self.error_callback(error_msg)
            raise ValueError(error_msg)

        # Final check if directory is still not available
        if not directory:
            error_msg = f"{ERROR_NO_DOWNLOAD_DIR} (directory value: {repr(directory)})"
            log_error_with_traceback(f"Directory selection failed: {error_msg}", "ERROR")
            if self.error_callback:
                self.error_callback(error_msg)
            raise ValueError(error_msg)

        self._is_cancelled = False

        try:
            if self.license_manager.is_pro:
                # Pro user logic: format detection and conversion
                # Get audio format preference for Pro users
                audio_format = self.get_audio_format()

                # Check format availability for each URL and group by compatibility
                urls_with_native_format = []
                urls_needing_conversion = []

                # Create a temporary yt-dlp instance for format detection
                temp_opts = {"verbose": False}

                with yt_dlp.YoutubeDL(temp_opts) as temp_ydl:
                    for url in urls:
                        if self._is_cancelled:
                            return

                        try:
                            # Extract format info without downloading
                            info_dict = temp_ydl.extract_info(url, download=False)
                            formats = info_dict.get("formats", [])

                            if self._has_native_format(formats, audio_format):
                                urls_with_native_format.append(url)
                            else:
                                urls_needing_conversion.append(url)

                        except Exception as e:
                            # If format detection fails, assume conversion needed
                            error_msg = f"Format detection failed for URL '{url}': {str(e)}"
                            log_error_with_traceback(error_msg, "WARNING")

                            if self.error_callback:
                                self.error_callback(f"Format detection failed for {url}: {str(e)}")
                            urls_needing_conversion.append(url)

                # Download URLs with native format support
                if urls_with_native_format and not self._is_cancelled:
                    native_opts = self._generate_ydl_opts(
                        directory, audio_format, has_native_format=True
                    )
                    with yt_dlp.YoutubeDL(native_opts) as ydl:
                        ydl.download(urls_with_native_format)

                # Download URLs requiring format conversion
                if urls_needing_conversion and not self._is_cancelled:
                    conversion_opts = self._generate_ydl_opts(
                        directory, audio_format, has_native_format=False
                    )
                    with yt_dlp.YoutubeDL(conversion_opts) as ydl:
                        for url in urls_needing_conversion:
                            info = ydl.extract_info(url, download=True)
                            raw_file = ydl.prepare_filename(info)

                            # Get the format specification for the target format
                            format_spec = AUDIO_FORMATS.get(audio_format)
                            mp3_file = os.path.splitext(raw_file)[0] + format_spec.extension
                            self.convert_audio(
                                input_path=raw_file,
                                output_path=mp3_file,
                                target_format=audio_format,
                            )
            else:
                # Free user logic: simple native download without conversion
                native_opts = self._generate_ydl_opts(directory)  # No audio_format argument
                with yt_dlp.YoutubeDL(native_opts) as ydl:
                    ydl.download(urls)

        except Exception as e:
            # Log with full stack trace for debugging, but provide directory context
            error_msg = f"Download failed in directory '{directory}': {str(e)}"
            log_error_with_traceback(error_msg, "CRITICAL")

            if self.error_callback and not self._is_cancelled:
                self.error_callback(f"Download failed: {str(e)}")
            raise

    def download_single_cloudcast(
        self, url: str, directory: str | None = None, parent_widget: QWidget | None = None
    ) -> None:
        """Download a single cloudcast.

        Args:
            url: Cloudcast URL to download
            directory: Target directory for download
            parent_widget: Parent widget for dialogs
        """
        self.download_cloudcasts([url], directory, parent_widget)

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
            base_filename = Path(filename).name

            # Remove file extension (e.g., .webm, .mp3, etc.)
            if "." in base_filename:
                item_name = base_filename.rsplit(".", 1)[0]
            else:
                item_name = base_filename

            # Remove temporary filename parts if present
            tmpfilename = progress_data.get("tmpfilename", "")
            if tmpfilename:
                tmp_base = Path(tmpfilename).name
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

    def get_download_directory(self, parent_widget: QWidget | None = None) -> str | None:
        """Get download directory, using default if Pro user has set one.

        Args:
            parent_widget: Parent widget for file dialog

        Returns:
            Selected directory path or None if cancelled
        """
        if self.license_manager.is_pro:
            # Check if Pro user has a default download directory set
            default_dir = self.settings_manager.get("default_download_directory", None)
            if default_dir and Path(default_dir).exists():
                return default_dir

        # Fallback to directory picker dialog
        return self._show_directory_picker(parent_widget)

    def get_download_directory_with_default_prompt(
        self, parent_widget: QWidget | None = None
    ) -> str | None:
        """Get download directory with smart default setting for Pro users.

        Args:
            parent_widget: Parent widget for dialogs

        Returns:
            Selected directory path or None if cancelled
        """
        if self.license_manager.is_pro:
            # Check if Pro user has a default download directory set
            default_dir = self.settings_manager.get("default_download_directory", None)
            if default_dir and Path(default_dir).exists():
                return default_dir

            # No default set - get directory and ask to save as default
            chosen_dir = self._show_directory_picker(parent_widget)
            if chosen_dir:
                self._prompt_save_as_default(chosen_dir, parent_widget)
            return chosen_dir

        # Free users get normal directory picker
        return self._show_directory_picker(parent_widget)

    def _show_directory_picker(self, parent_widget: QWidget | None = None) -> str | None:
        """Show directory picker dialog.

        Args:
            parent_widget: Parent widget for dialog

        Returns:
            Selected directory path or None if cancelled
        """
        directory = QFileDialog.getExistingDirectory(
            parent_widget, "Select Download Directory", str(Path.home())
        )
        return directory if directory else None

    def _prompt_save_as_default(self, directory: str, parent_widget: QWidget | None) -> None:
        """Show dialog asking if user wants to save directory as default.

        Args:
            directory: Directory path to potentially save as default
            parent_widget: Parent widget for dialog
        """
        reply = QMessageBox.question(
            parent_widget,
            "Save as Default",
            f"Would you like to save this location as your default download folder?\n\n{directory}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Save the directory as the default for future downloads
            self.settings_manager.set("default_download_directory", directory)

    def get_audio_format(self) -> str:
        """Get audio format preference for Pro users.

        Returns:
            Audio format preference (lowercase)
        """
        if self.license_manager.is_pro:
            # Get the saved audio format preference, defaulting to MP3
            format_setting = self.settings_manager.get("default_audio_format", "MP3")
            return format_setting.lower()  # yt-dlp expects lowercase
        return "mp3"

    def _has_native_format(self, formats: list, desired_format: str) -> bool:
        """Check if desired audio format is natively available in the provided formats.

        Args:
            formats: List of format dictionaries from yt-dlp extract_info
            desired_format: Target audio format extension (e.g., 'mp3', 'm4a')

        Returns:
            True if desired format is natively available, False otherwise
        """
        return any(f.get("ext") == desired_format and f.get("acodec") != "none" for f in formats)

    def _generate_ydl_opts(
        self, directory: str, audio_format: str | None = None, has_native_format: bool = False
    ) -> dict:
        """Generate yt-dlp options based on format availability.

        Args:
            directory: Target download directory
            audio_format: Desired audio format (lowercase). If None, uses native format only.
            has_native_format: Whether the desired format is natively available

        Returns:
            Dictionary of yt-dlp options configured for the format scenario
        """
        base_opts = {
            "outtmpl": f"{directory}/%(uploader_id)s - %(title)s.%(ext)s",
            "progress_hooks": [self._track_progress],
            "verbose": False,
        }

        # For free users (audio_format is None), return basic options only
        if audio_format is None:
            return base_opts

        # For Pro users, add format-specific configuration
        # Add FFmpeg location for all operations
        try:
            ffmpeg_path = str(self._get_ffmpeg_path())
            base_opts["ffmpeg_location"] = ffmpeg_path
        except (RuntimeError, OSError):
            # If FFmpeg path can't be determined, let yt-dlp use system FFmpeg
            log_ui("FFmpeg path can't be determined, let yt-dlp use system FFmpeg", "WARNING")
            pass

        if has_native_format:
            # Use native format directly
            base_opts["format"] = f"bestaudio[ext={audio_format}]"
        else:
            # Use best available format and convert with FFmpeg
            base_opts["format"] = "bestaudio/best"
            # Unfortunately, FFmpeg does not output progress. To be able to track progress, FFmpeg is called through
            # subprocess instead. Postprocessors should remain empty here.
            base_opts["postprocessors"] = []
            base_opts["nopopstoverwrites"] = False

        return base_opts

    def _get_ffmpeg_path(self):
        base = Path(__file__).parent.parent / "resources" / "ffmpeg"
        system = platform.system().lower()

        if system == "windows":
            return base / "windows" / "ffmpeg.exe"
        elif system == "darwin":  # macOS
            return base / "macos" / "ffmpeg"
        else:
            raise RuntimeError(f"Unsupported OS: {system}")

    def verify_ffmpeg_availability(self) -> bool:
        """Verify that FFmpeg is available for audio conversion.

        Returns:
            True if FFmpeg executable is found and accessible, False otherwise
        """
        try:
            ffmpeg_path = self._get_ffmpeg_path()
            ffmpeg_path_obj = Path(ffmpeg_path)

            # Check if the file exists and is executable
            return ffmpeg_path_obj.exists() and ffmpeg_path_obj.is_file()

        except (RuntimeError, OSError):
            # Handle unsupported OS or other path-related errors
            return False

    def convert_audio(
        self, input_path: str, output_path: str, target_format: str, bitrate_k: int = 192
    ) -> None:
        """Convert an audio file to a different format using ffmpeg, supporting multiple formats.

        Args:
            input_path: Path to the source file.
            output_path: Path to the converted file.
            target_format: Target format key from FILE_FORMATS.
            bitrate_k: Bitrate for lossy formats in kBs.

        Returns:
            Path to the converted file.
        """
        item_name = os.path.splitext(Path(input_path).name)[0]
        log_thread(f"Converting {item_name} to {target_format}...")

        ffmpeg_path = self._get_ffmpeg_path()

        fmt_info = AUDIO_FORMATS.get(target_format)
        codec = fmt_info.codec
        is_lossless: bool = fmt_info.is_lossless

        cmd = [ffmpeg_path, "-y", "-i", input_path, "-vn", "-c:a", codec]

        if not is_lossless:
            cmd += ["-b:a", str(bitrate_k)]  # set bitrate only for lossy formats

        cmd += ["-progress", "pipe:1", "-nostats", output_path]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        duration: float | None = None

        for line in process.stdout:
            line = line.strip()

            if "duration" in line.lower():
                # Look for the Duration line
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
                if m:
                    h, m_, s = m.groups()
                    duration = int(h) * 3600 + int(m_) * 60 + float(s)
            elif "progress=end" in line:
                if self.progress_callback:
                    self.progress_callback(item_name, "Conversion finished!")

            elif line.startswith("out_time_ms=") and self.progress_callback:
                ms = line.split("=")[1]

                # upon starting, the 1st returned out_time_ns is often N/A. Simply ignore this line
                if ms.lower() == "n/a":
                    continue

                seconds = int(ms) / 1_000_000
                if duration:
                    percent = min(100, (seconds / duration) * 100)
                    progress_message = f"Converting to {fmt_info.label}... {percent:.2f}%"
                else:
                    progress_message = f"Converting to {fmt_info.label}..."  # fallback

                self.progress_callback(item_name, progress_message)

        retcode = process.wait()
        if retcode != 0:
            raise RuntimeError(f"FFmpeg failed with code {retcode}")


# Create module-level singleton instance
download_service = DownloadService()
