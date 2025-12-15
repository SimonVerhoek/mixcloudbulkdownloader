"""FFmpeg utility functions for cross-platform executable detection."""

import platform
from pathlib import Path
from typing import Literal

from app.qt_logger import log_download, log_error_with_traceback


def _get_macos_architecture() -> Literal["arm64", "intel"]:
    """Get macOS architecture for binary selection.

    Returns:
        "arm64" for Apple Silicon, "intel" for x86_64/i386

    Raises:
        RuntimeError: For unrecognized architectures
    """
    arch = platform.machine().lower()
    if arch == "arm64":
        return "arm64"
    elif arch in ("x86_64", "i386"):
        return "intel"
    else:
        log_error_with_traceback(f"Unsupported macOS architecture: {arch}")
        raise RuntimeError(f"Unsupported macOS architecture: {arch}")


def get_ffmpeg_path() -> Path:
    """Get platform-specific FFmpeg executable path.

    Returns:
        Path to FFmpeg executable

    Raises:
        RuntimeError: If running on unsupported platform
    """
    base = Path(__file__).parent.parent / "resources" / "ffmpeg"
    system = platform.system().lower()

    if system == "windows":
        selected_path = base / "windows" / "ffmpeg.exe"
        log_download(f"Detected system: {system}, selected FFmpeg binary: {selected_path}")
        return selected_path
    elif system == "darwin":  # macOS
        arch = _get_macos_architecture()
        selected_path = base / "macos" / arch / "ffmpeg"
        log_download(
            f"Detected system: {system}, architecture: {arch}, selected FFmpeg binary: {selected_path}"
        )
        return selected_path
    else:
        log_error_with_traceback(f"Unsupported OS: {system}")
        raise RuntimeError(f"Unsupported OS: {system}")


def get_ffprobe_path() -> Path:
    """Get platform-specific FFprobe executable path.

    Returns:
        Path to FFprobe executable

    Raises:
        RuntimeError: If running on unsupported platform
    """
    base = Path(__file__).parent.parent / "resources" / "ffmpeg"
    system = platform.system().lower()

    if system == "windows":
        selected_path = base / "windows" / "ffprobe.exe"
        log_download(f"Detected system: {system}, selected FFprobe binary: {selected_path}")
        return selected_path
    elif system == "darwin":  # macOS
        arch = _get_macos_architecture()
        selected_path = base / "macos" / arch / "ffprobe"
        log_download(
            f"Detected system: {system}, architecture: {arch}, selected FFprobe binary: {selected_path}"
        )
        return selected_path
    else:
        log_error_with_traceback(f"Unsupported OS: {system}")
        raise RuntimeError(f"Unsupported OS: {system}")


def verify_ffmpeg_availability() -> bool:
    """Verify that FFmpeg is available for audio conversion.

    Returns:
        True if FFmpeg executable is found and accessible, False otherwise
    """
    try:
        ffmpeg_path = get_ffmpeg_path()
        return ffmpeg_path.exists() and ffmpeg_path.is_file()
    except (RuntimeError, OSError):
        return False
