"""Qt-free logging module for the Mixcloud Bulk Downloader application.

This module owns all logging configuration and exports convenience functions.
It has no Qt imports, making it safe to use in any layer of the application
including pure business logic, services, and data layers.

Usage:
    from app.logger import log_api, log_error, configure

    # Called once at startup (by QtLogger.__init__)
    configure(log_file=Path("/path/to/mbd.log"))

    # Call anywhere in the application
    log_api("Making request to Mixcloud API")
    log_error("Something went wrong")
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Named loggers for each application domain
_logger_ui = logging.getLogger("app.ui")
_logger_api = logging.getLogger("app.api")
_logger_download = logging.getLogger("app.download")
_logger_thread = logging.getLogger("app.thread")
_logger_error = logging.getLogger("app.error")

# Map level strings to logging module constants
_LEVEL_MAP: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "FATAL": logging.FATAL,
}

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_log_directory() -> Path:
    """Get platform-appropriate log directory.

    Returns:
        Path to the platform-specific log directory (created if it does not exist).
    """
    if sys.platform == "darwin":  # macOS
        log_dir = Path.home() / "Library" / "Logs" / "MixcloudBulkDownloader"
    elif sys.platform == "win32":  # Windows
        app_data = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        log_dir = Path(app_data) / "MixcloudBulkDownloader" / "logs"
    else:  # Linux and other Unix-like systems
        xdg_data_home = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        log_dir = Path(xdg_data_home) / "MixcloudBulkDownloader" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def configure(log_file: Path) -> None:
    """Configure the root logger with file rotation and optional console output.

    Attaches a ``RotatingFileHandler`` (5 MB max, 5 backups) to ``logging.root``
    and, when the ``DEVELOPMENT`` environment variable is ``"True"``, also adds a
    ``StreamHandler`` for console output.

    This function is idempotent: calling it more than once will not duplicate
    handlers because it checks for existing ``RotatingFileHandler`` instances.

    Args:
        log_file: Absolute path to the log file.  The parent directory must
            already exist (``get_log_directory()`` guarantees this).
    """
    root_logger = logging.getLogger()

    # Avoid adding duplicate handlers when called multiple times
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            return

    root_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Rotating file handler — 5 MB per file, keep 5 backups
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    level_str = os.getenv("LOGGING_LEVEL", "INFO").upper()
    file_level = _LEVEL_MAP.get(level_str, logging.INFO)
    file_handler.setLevel(file_level)
    root_logger.addHandler(file_handler)

    # Console output in development mode
    if os.getenv("DEVELOPMENT") == "True":
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(stream_handler)


# ---------------------------------------------------------------------------
# Convenience functions — mirrors the previous app.qt_logger public API
# ---------------------------------------------------------------------------


def log_ui(message: str, level: str = "INFO") -> None:
    """Log UI-related message.

    Args:
        message: The message to log.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    _logger_ui.log(
        level=_LEVEL_MAP.get(level, logging.INFO),
        msg=message,
        stacklevel=2,
    )


def log_api(message: str, level: str = "INFO") -> None:
    """Log API-related message.

    Args:
        message: The message to log.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    _logger_api.log(
        level=_LEVEL_MAP.get(level, logging.INFO),
        msg=message,
        stacklevel=2,
    )


def log_download(message: str, level: str = "INFO") -> None:
    """Log download-related message.

    Args:
        message: The message to log.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    _logger_download.log(
        level=_LEVEL_MAP.get(level, logging.INFO),
        msg=message,
        stacklevel=2,
    )


def log_thread(message: str, level: str = "INFO") -> None:
    """Log thread-related message.

    Args:
        message: The message to log.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    _logger_thread.log(
        level=_LEVEL_MAP.get(level, logging.INFO),
        msg=message,
        stacklevel=2,
    )


def log_error(message: str, level: str = "ERROR") -> None:
    """Log error message.

    Args:
        message: The message to log.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    _logger_error.log(
        level=_LEVEL_MAP.get(level, logging.ERROR),
        msg=message,
        stacklevel=2,
    )


def log_error_with_traceback(message: str, level: str = "ERROR") -> None:
    """Log error message capturing the current exception traceback.

    Must be called from within an ``except`` block for ``exc_info`` to be
    populated automatically.

    Args:
        message: The message to log.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    _logger_error.log(
        level=_LEVEL_MAP.get(level, logging.ERROR),
        msg=message,
        exc_info=True,
        stacklevel=2,
    )


def log_exception(message: str, exc_info=None, level: str = "ERROR") -> None:
    """Log exception with stack trace.

    Args:
        message: The message to log.
        exc_info: Exception info tuple ``(type, value, traceback)``.  When
            ``None`` the current exception context (``sys.exc_info()``) is used.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    if exc_info is None:
        exc_info = sys.exc_info()

    _logger_error.log(
        level=_LEVEL_MAP.get(level, logging.ERROR),
        msg=message,
        exc_info=exc_info,
        stacklevel=2,
    )
