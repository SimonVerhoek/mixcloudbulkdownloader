"""Conversion worker implementation using proper PyQt threading patterns.

This module provides ConversionWorker that uses QRunnable with thread-safe
signal emission through CallbackBridge for FFmpeg audio format conversion.
"""

import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QRunnable

from app.consts.audio import AUDIO_FORMATS
from app.consts.ui import CANCELLED_ICON, CONVERSION_ICON
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager
from app.utils.ffmpeg import get_ffmpeg_path


class ConversionCancelled(Exception):
    """Exception raised when conversion is cancelled."""

    pass


class ConversionWorker(QRunnable):
    """QRunnable worker for converting audio files using FFmpeg.

    This class implements audio format conversion using proper PyQt patterns:
    - Inherits from QRunnable for thread pool execution
    - Uses CallbackBridge for thread-safe signal emission
    - Follows existing file naming conventions (.converting extension)
    - Maintains compatibility with existing progress display patterns
    """

    def __init__(
        self,
        cloudcast_url: str,
        input_file: str,
        target_format: str,
        download_dir: str,
        callback_bridge: "CallbackBridge",
        settings_manager: SettingsManager,
        license_manager: LicenseManager,
    ):
        """Initialize conversion worker.

        Args:
            cloudcast_url: Original cloudcast URL (task identifier)
            input_file: Path to input file to convert
            target_format: Target audio format (e.g., "mp3", "flac")
            download_dir: Target directory for conversion
            callback_bridge: Thread-safe signal emission bridge
            settings_manager: Settings manager for configuration
            license_manager: License manager for Pro feature access
        """
        super().__init__()
        self.cloudcast_url = cloudcast_url
        self.input_file = input_file
        self.target_format = target_format
        self.download_dir = download_dir
        self.callback_bridge = callback_bridge
        self.settings_manager = settings_manager
        self.license_manager = license_manager
        self.cancelled = False
        self.ffmpeg_process = None

        # Set up file paths using temporary subdirectory approach to fix FFmpeg format detection
        input_path = Path(input_file)
        base_name = input_path.stem
        self.final_filename = f"{base_name}.{target_format}"

        # Create temp subdirectory for conversion to avoid FFmpeg format confusion
        self.temp_dir = Path(download_dir) / ".converting"
        self.converting_file_path = self.temp_dir / self.final_filename
        self.final_file_path = Path(download_dir) / self.final_filename

    def run(self):
        """Execute the conversion task."""
        try:
            if self.cancelled:
                raise ConversionCancelled("Conversion cancelled before start")

            # Verify Pro license
            if not self.license_manager.is_pro:
                raise ValueError("Audio conversion requires Pro license")

            # Get FFmpeg path
            ffmpeg_path = get_ffmpeg_path()
            if not ffmpeg_path:
                raise ValueError("FFmpeg not found - audio conversion unavailable")

            # Validate input and output before starting conversion
            self._validate_conversion_prerequisites(ffmpeg_path)

            # Build and execute FFmpeg command
            cmd = self._build_ffmpeg_command(str(ffmpeg_path))

            # Log the full FFmpeg command for debugging
            from app.qt_logger import log_api

            log_api(f"Starting FFmpeg conversion: {' '.join(cmd)}")
            log_api(f"Input file: {self.input_file}")
            log_api(f"Output file: {self.converting_file_path}")
            log_api(f"Target format: {self.target_format}")

            # Use stderr=subprocess.STDOUT so progress info (from stderr) appears in stdout
            self.ffmpeg_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )

            duration = None

            # Parse FFmpeg output for progress
            for line in self.ffmpeg_process.stdout:
                if self.cancelled:
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait()
                    raise ConversionCancelled("Conversion cancelled during progress")

                line = line.strip()

                # Parse duration from FFmpeg output
                if "duration" in line.lower():
                    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
                    if duration_match:
                        h, m, s = duration_match.groups()
                        duration = int(h) * 3600 + int(m) * 60 + float(s)

                # Parse progress
                elif line.startswith("out_time_ms="):
                    self._parse_progress(line, duration)

            # Wait for process completion (stderr already redirected to stdout)
            self.ffmpeg_process.wait()
            retcode = self.ffmpeg_process.returncode
            self.ffmpeg_process = None

            if retcode != 0:
                # Log detailed error information for debugging
                from app.qt_logger import log_error

                log_error(f"FFmpeg conversion failed with exit code {retcode}")

                # Note: stderr was redirected to stdout, so error details were already processed

                # Parse and provide user-friendly error message
                error_message = self._parse_ffmpeg_error(
                    "", retcode
                )  # No stderr available since redirected
                raise RuntimeError(error_message)

            # Atomically move from temp directory to final location
            if self.converting_file_path.exists():
                # Move the converted file from temp directory to final location
                self.converting_file_path.rename(self.final_file_path)

                # Clean up original input file after successful conversion
                self._cleanup_original_file()

                # Clean up temp directory if empty
                self._cleanup_temp_directory()

                if not self.cancelled:
                    self.callback_bridge.emit_completed(
                        self.cloudcast_url, str(self.final_file_path), "conversion"
                    )
            else:
                raise RuntimeError(f"Converted file not found: {self.converting_file_path}")

        except ConversionCancelled:
            # Emit cancellation signal and clean up
            self.callback_bridge.emit_progress(
                self.cloudcast_url, f"{CANCELLED_ICON} Cancelled", "conversion"
            )
            self._cleanup_partial_conversion()

        except Exception as e:
            self.callback_bridge.emit_error(
                self.cloudcast_url, f"Conversion failed: {str(e)}", "conversion"
            )
            self._cleanup_partial_conversion()

    def cancel(self):
        """Cancel the conversion operation."""
        self.cancelled = True

        # Terminate FFmpeg process if running
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                # Wait briefly for graceful termination
                self.ffmpeg_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if termination doesn't work
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
            finally:
                self.ffmpeg_process = None

        # Clean up partial conversion
        self._cleanup_partial_conversion()

    def _build_ffmpeg_command(self, ffmpeg_path: str) -> list[str]:
        """Build FFmpeg command with proper codec and options.

        Args:
            ffmpeg_path: Path to FFmpeg executable

        Returns:
            FFmpeg command as list of strings
        """
        format_info = AUDIO_FORMATS.get(self.target_format)
        if not format_info:
            raise ValueError(f"Unsupported audio format: {self.target_format}")

        cmd = [
            ffmpeg_path,
            "-y",  # Overwrite output files
            "-i",
            self.input_file,  # Input file
            "-vn",  # No video
            "-c:a",
            format_info.codec,  # Audio codec
        ]

        # Add bitrate for lossy formats
        if not format_info.is_lossless:
            cmd.extend(["-b:a", "192k"])

        # Add progress output
        cmd.extend(["-progress", "pipe:1", "-nostats"])

        # Output file (with .converting extension)
        cmd.append(str(self.converting_file_path))

        return cmd

    def _parse_progress(self, line: str, duration: float | None) -> None:
        """Parse FFmpeg progress output and emit progress signal.

        Args:
            line: FFmpeg progress line starting with "out_time_ms="
            duration: Total duration in seconds if known
        """
        try:
            ms_str = line.split("=")[1]
            if ms_str.lower() == "n/a":
                return

            seconds = int(ms_str) / 1_000_000

            if duration and duration > 0:
                percent = min(100, (seconds / duration) * 100)
                progress_text = f"{CONVERSION_ICON} {self.target_format.upper()} {percent:.1f}%"
            else:
                progress_text = f"{CONVERSION_ICON} {self.target_format.upper()}..."

            self.callback_bridge.emit_progress(self.cloudcast_url, progress_text, "conversion")

        except (ValueError, IndexError):
            # Ignore malformed progress lines
            pass

    def _cleanup_original_file(self) -> None:
        """Remove original input file after successful conversion.

        This method safely removes the original .webm file after FFmpeg has
        completed and the conversion has been successfully renamed.
        """
        try:
            input_path = Path(self.input_file)

            # Safety checks before deletion
            if not input_path.exists():
                return

            if input_path.resolve() == self.final_file_path.resolve():
                return  # Don't delete if same file

            # Verify converted file exists and has content
            if not self.final_file_path.exists():
                return

            if self.final_file_path.stat().st_size == 0:
                return  # Don't delete if conversion is empty

            # Perform the cleanup
            input_path.unlink()

        except (OSError, PermissionError):
            # Ignore cleanup errors - not critical
            pass

    def _cleanup_partial_conversion(self):
        """Clean up partial conversion files and temp directory."""
        try:
            # Remove the conversion file if it exists
            if self.converting_file_path.exists():
                self.converting_file_path.unlink()

            # Clean up temp directory if it's empty
            self._cleanup_temp_directory()
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors

    def _cleanup_temp_directory(self):
        """Clean up temporary conversion directory if empty."""
        try:
            if self.temp_dir.exists() and self.temp_dir.is_dir():
                # Only remove if directory is empty
                if not any(self.temp_dir.iterdir()):
                    self.temp_dir.rmdir()
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors - temp dir will be cleaned up later

    def _validate_conversion_prerequisites(self, ffmpeg_path: Path) -> None:
        """Validate input and output requirements before starting conversion.

        Args:
            ffmpeg_path: Path to FFmpeg executable

        Raises:
            ValueError: If validation fails with specific error details
        """
        input_path = Path(self.input_file)

        # Validate input file
        if not input_path.exists():
            raise ValueError(f"Input file does not exist: {self.input_file}")

        if not input_path.is_file():
            raise ValueError(f"Input path is not a file: {self.input_file}")

        if input_path.stat().st_size == 0:
            raise ValueError(f"Input file is empty: {self.input_file}")

        # Validate input file is readable
        try:
            with open(input_path, "rb") as f:
                f.read(1)  # Try to read first byte
        except (PermissionError, OSError) as e:
            raise ValueError(f"Cannot read input file: {self.input_file} - {e}")

        # Validate main output directory
        main_output_dir = self.final_file_path.parent
        if not main_output_dir.exists():
            raise ValueError(f"Output directory does not exist: {main_output_dir}")

        if not main_output_dir.is_dir():
            raise ValueError(f"Output path is not a directory: {main_output_dir}")

        # Create and validate temporary conversion directory
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            raise ValueError(f"Cannot create temp conversion directory: {self.temp_dir} - {e}")

        # Test write permissions in temp directory
        temp_test_file = self.temp_dir / f".write_test_{hash(self.cloudcast_url)}"
        try:
            temp_test_file.write_text("test")
            temp_test_file.unlink()
        except (PermissionError, OSError) as e:
            raise ValueError(f"Cannot write to temp conversion directory: {self.temp_dir} - {e}")

        # Validate FFmpeg executable
        if not ffmpeg_path.exists():
            raise ValueError(f"FFmpeg executable not found: {ffmpeg_path}")

        if not ffmpeg_path.is_file():
            raise ValueError(f"FFmpeg path is not a file: {ffmpeg_path}")

        from app.qt_logger import log_api

        log_api(f"Conversion prerequisites validated successfully")
        log_api(f"Input file size: {input_path.stat().st_size} bytes")
        log_api(f"Output directory: {main_output_dir}")

    def _parse_ffmpeg_error(self, stderr: str, exit_code: int) -> str:
        """Parse FFmpeg error output to provide user-friendly error messages.

        Args:
            stderr: FFmpeg stderr output
            exit_code: FFmpeg process exit code

        Returns:
            User-friendly error message
        """
        import re

        # Common FFmpeg error patterns and their user-friendly messages
        error_patterns = {
            r"No such file or directory": "Input file not found or output directory doesn't exist",
            r"Permission denied": "Permission denied - check file/directory permissions",
            r"Invalid argument": "Invalid file path or unsupported format",
            r"No space left on device": "Not enough disk space for conversion",
            r"does not contain any stream": "Input file contains no audio stream to convert",
            r"Unknown encoder": "Audio codec not supported by this FFmpeg version",
            r"could not open codec": "Failed to initialize audio codec",
            r"Invalid data found": "Input file appears to be corrupted",
            r"Output file.*already exists": "Output file already exists (unexpected)",
            r"Resource temporarily unavailable": "System resources exhausted",
        }

        # Check for known error patterns
        stderr_lower = stderr.lower()
        for pattern, message in error_patterns.items():
            if re.search(pattern, stderr_lower, re.IGNORECASE):
                return f"Conversion failed: {message} (FFmpeg exit code {exit_code})"

        # Exit code specific messages
        exit_code_messages = {
            234: "Invalid file path or permissions issue",
            1: "General conversion error - check input file format",
            2: "Invalid command arguments",
            126: "Permission denied executing FFmpeg",
            127: "FFmpeg executable not found",
            -2: "Process interrupted",
            -9: "Process killed (out of memory?)",
        }

        if exit_code in exit_code_messages:
            base_message = exit_code_messages[exit_code]
        else:
            base_message = "Unknown conversion error"

        # Include relevant stderr snippet if available
        if stderr.strip():
            # Extract last meaningful error line
            stderr_lines = [line.strip() for line in stderr.split("\n") if line.strip()]
            if stderr_lines:
                last_error = stderr_lines[-1][:100]  # Limit length
                return f"Conversion failed: {base_message} - {last_error} (exit code {exit_code})"

        return f"Conversion failed: {base_message} (exit code {exit_code})"
