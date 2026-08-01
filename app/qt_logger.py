"""Qt adapter for routing Qt framework messages into Python's logging system.

This module is intentionally minimal.  It is responsible only for:

1. Calling ``logger.configure()`` to set up the file handler and optional
   console handler once a ``QApplication`` exists.
2. Installing ``qInstallMessageHandler`` so that Qt's own internal messages
   (widget warnings, OpenGL errors, etc.) are captured and written to the
   same log file via the ``qt`` Python logger.

All application-level logging (``log_api``, ``log_ui``, etc.) now lives in
``app.logger`` which has no Qt dependency.  Only ``main.py`` should import
from this module.
"""

import logging

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from app.logger import configure, get_log_directory


# Qt framework message logger — captures Qt's own internal messages
_qt_logger = logging.getLogger("qt")

# Qt message type → Python logging level mapping
_QT_LEVEL_MAP: dict[QtMsgType, int] = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.CRITICAL,
    QtMsgType.QtFatalMsg: logging.FATAL,
}


def _qt_message_handler(msg_type: QtMsgType, context, message: str) -> None:
    """Route Qt framework messages into Python's logging system.

    Args:
        msg_type: Qt message severity.
        context: Qt message context (file, line, category).
        message: The message text emitted by Qt.
    """
    level = _QT_LEVEL_MAP.get(msg_type, logging.INFO)
    _qt_logger.log(level=level, msg=message)


class QtLogger:
    """Initialises the logging system and installs the Qt message handler.

    Must be instantiated once, after ``QApplication`` has been created.
    Subsequent instantiations are no-ops (singleton pattern).
    """

    _initialized: bool = False

    def __new__(cls) -> "QtLogger":
        """Enforce singleton — return the same instance on every call."""
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Set up file logging and install the Qt message handler."""
        if not QtLogger._initialized:
            log_dir = get_log_directory()
            log_file = log_dir / "mbd.log"

            configure(log_file=log_file)
            qInstallMessageHandler(_qt_message_handler)

            QtLogger._initialized = True

    @classmethod
    def get_instance(cls) -> "QtLogger":
        """Return the singleton ``QtLogger`` instance."""
        return cls()


def get_logger() -> QtLogger:
    """Return the global ``QtLogger`` instance.

    Provided for backward compatibility with any code that calls
    ``get_logger()`` from this module.
    """
    return QtLogger.get_instance()
