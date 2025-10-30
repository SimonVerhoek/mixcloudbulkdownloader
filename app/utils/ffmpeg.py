"""FFmpeg utility functions for cross-platform executable detection."""

import platform
from pathlib import Path


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
        return base / "windows" / "ffmpeg.exe"
    elif system == "darwin":  # macOS
        return base / "macos" / "ffmpeg"
    else:
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
        return base / "windows" / "ffprobe.exe"
    elif system == "darwin":  # macOS
        return base / "macos" / "ffprobe"
    else:
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
