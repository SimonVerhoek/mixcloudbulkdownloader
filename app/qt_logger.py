"""Qt-native logging system for the Mixcloud Bulk Downloader application."""

import logging
import os
import sys
import time
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QLoggingCategory,
    QtMsgType,
    qCCritical,
    qCDebug,
    qCInfo,
    qCWarning,
    qInstallMessageHandler,
)


class QtLogger:
    """Singleton Qt-native logger with file rotation support."""

    _instance: Optional["QtLogger"] = None
    _initialized: bool = False

    # Application logging categories (will be initialized in __init__)
    UI_CATEGORY: QLoggingCategory
    API_CATEGORY: QLoggingCategory
    DOWNLOAD_CATEGORY: QLoggingCategory
    THREAD_CATEGORY: QLoggingCategory
    ERROR_CATEGORY: QLoggingCategory

    def __new__(cls) -> "QtLogger":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize Qt logger if not already initialized."""
        if not self._initialized:
            # Initialize categories with INFO level and above (excludes DEBUG)
            self.UI_CATEGORY = QLoggingCategory("app.ui", QtMsgType.QtInfoMsg)
            self.API_CATEGORY = QLoggingCategory("app.api", QtMsgType.QtInfoMsg)
            self.DOWNLOAD_CATEGORY = QLoggingCategory("app.download", QtMsgType.QtInfoMsg)
            self.THREAD_CATEGORY = QLoggingCategory("app.threads", QtMsgType.QtInfoMsg)
            self.ERROR_CATEGORY = QLoggingCategory("app.error", QtMsgType.QtInfoMsg)

            self._setup_logging()
            QtLogger._initialized = True

    def _get_log_directory(self) -> Path:
        """Get platform-appropriate log directory."""
        if sys.platform == "darwin":  # macOS
            log_dir = Path.home() / "Library" / "Logs" / "MixcloudBulkDownloader"
        elif sys.platform == "win32":  # Windows
            app_data = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            log_dir = Path(app_data) / "MixcloudBulkDownloader" / "logs"
        else:  # Linux and other Unix-like systems
            xdg_data_home = os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
            log_dir = Path(xdg_data_home) / "MixcloudBulkDownloader" / "logs"

        # Ensure directory exists
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def _setup_logging(self) -> None:
        """Set up Qt message handler and file rotation."""
        log_dir = self._get_log_directory()
        log_file = log_dir / "mbd.log"

        # Set up rotating file handler
        self._file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=5 * 1024 * 1024,  # 5MB per file
            backupCount=5,  # Keep 5 backup files
            encoding="utf-8",
        )

        # Install Qt message handler
        qInstallMessageHandler(self._qt_message_handler)

    def _qt_message_handler(self, msg_type: QtMsgType, context, message: str) -> None:
        """Handle Qt framework messages and route to file."""
        # Format Qt message types to standard levels
        level_map = {
            QtMsgType.QtDebugMsg: "DEBUG",
            QtMsgType.QtInfoMsg: "INFO",
            QtMsgType.QtWarningMsg: "WARNING",
            QtMsgType.QtCriticalMsg: "CRITICAL",
            QtMsgType.QtFatalMsg: "FATAL",
        }

        level = level_map.get(msg_type, "UNKNOWN")

        # Get context information
        file_name = context.file if context.file else "unknown"
        line_num = context.line if context.line else 0
        category = context.category if context.category else "qt"

        # Format log entry
        log_entry = f"[{level}] {category} ({file_name}:{line_num}) - {message}\n"

        # Write to file using the rotating file handler
        try:
            # Create a basic log record compatible with RotatingFileHandler
            record = logging.LogRecord(
                name=category,
                level=getattr(logging, level, logging.INFO),
                pathname=file_name,
                lineno=line_num,
                msg=message,
                args=(),
                exc_info=None,
            )
            record.created = time.time()

            # Format and write the record
            formatted = log_entry
            record.getMessage = lambda: formatted.rstrip()

            # Use the handler to write (handles rotation)
            if self._file_handler.stream:
                self._file_handler.stream.write(formatted)
                self._file_handler.stream.flush()

                # Check if rollover is needed
                if self._file_handler.shouldRollover(record):
                    self._file_handler.doRollover()

        except Exception as e:
            # Fallback to stderr if file writing fails
            sys.stderr.write(f"LOG ERROR: {log_entry} (File error: {e})\n")

        # Also output to console in development mode
        if os.getenv("DEVELOPMENT") == "True":
            print(log_entry.rstrip())

    @classmethod
    def get_instance(cls) -> "QtLogger":
        """Get the singleton QtLogger instance."""
        return cls()

    def log_ui(self, message: str, level: str = "INFO") -> None:
        """Log UI-related messages."""
        self._log_to_category(self.UI_CATEGORY, message, level)

    def log_api(self, message: str, level: str = "INFO") -> None:
        """Log API-related messages."""
        self._log_to_category(self.API_CATEGORY, message, level)

    def log_download(self, message: str, level: str = "INFO") -> None:
        """Log download-related messages."""
        self._log_to_category(self.DOWNLOAD_CATEGORY, message, level)

    def log_thread(self, message: str, level: str = "INFO") -> None:
        """Log thread-related messages."""
        self._log_to_category(self.THREAD_CATEGORY, message, level)

    def log_error(self, message: str, level: str = "ERROR") -> None:
        """Log error messages."""
        self._log_to_category(self.ERROR_CATEGORY, message, level)

    def log_error_with_traceback(self, message: str, level: str = "ERROR") -> None:
        """Log error messages with full stack trace."""
        tb = traceback.format_exc()
        full_message = f"{message}\nStack trace:\n{tb}"
        self._log_to_category(self.ERROR_CATEGORY, full_message, level)

    def log_exception(self, message: str, exc_info=None, level: str = "ERROR") -> None:
        """Log exception with stack trace. If exc_info is None, uses current exception."""
        if exc_info is None:
            exc_info = sys.exc_info()

        if exc_info[0] is not None:
            tb_lines = traceback.format_exception(*exc_info)
            tb_string = "".join(tb_lines)
            full_message = f"{message}\nException details:\n{tb_string}"
        else:
            full_message = f"{message} (No exception context available)"

        self._log_to_category(self.ERROR_CATEGORY, full_message, level)

    def _log_to_category(self, category: QLoggingCategory, message: str, level: str) -> None:
        """Log message to specified category."""
        # Route to appropriate Qt logging function
        if level == "DEBUG" and category.isDebugEnabled():
            qCDebug(category, message)
        elif level == "INFO" and category.isInfoEnabled():
            qCInfo(category, message)
        elif level == "WARNING" and category.isWarningEnabled():
            qCWarning(category, message)
        elif level in ["ERROR", "CRITICAL", "FATAL"] and category.isCriticalEnabled():
            qCCritical(category, message)


# Global logger instance
def get_logger() -> QtLogger:
    """Get the global QtLogger instance."""
    return QtLogger.get_instance()


# Convenience functions for common logging operations
def log_ui(message: str, level: str = "INFO") -> None:
    """Log UI-related message."""
    get_logger().log_ui(message, level)


def log_api(message: str, level: str = "INFO") -> None:
    """Log API-related message."""
    get_logger().log_api(message, level)


def log_download(message: str, level: str = "INFO") -> None:
    """Log download-related message."""
    get_logger().log_download(message, level)


def log_thread(message: str, level: str = "INFO") -> None:
    """Log thread-related message."""
    get_logger().log_thread(message, level)


def log_error(message: str, level: str = "ERROR") -> None:
    """Log error message."""
    get_logger().log_error(message, level)


def log_error_with_traceback(message: str, level: str = "ERROR") -> None:
    """Log error message with full stack trace."""
    get_logger().log_error_with_traceback(message, level)


def log_exception(message: str, exc_info=None, level: str = "ERROR") -> None:
    """Log exception with stack trace. If exc_info is None, uses current exception."""
    get_logger().log_exception(message, exc_info, level)
