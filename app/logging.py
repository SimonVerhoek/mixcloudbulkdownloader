"""Logging configuration for the Mixcloud Bulk Downloader application."""

import logging
import os
from datetime import datetime
from logging.config import dictConfig

from app.consts import DEFAULT_LOG_DIR, LOG_BACKUP_COUNT, LOG_FILE_PREFIX


# Configuration from environment variables
LOGGING_LEVEL: int = int(os.getenv("LOGGING_LEVEL", logging.INFO))
DEVELOPMENT: bool = os.getenv("DEVELOPMENT") == "True"


def configure_logging(development: bool = False) -> dict:
    """Configure logging for the application.

    Sets up file-based logging with optional console output for development.
    Log files are rotated daily and kept for a limited number of days.

    Args:
        development: If True, also log to console output

    Returns:
        Dictionary containing the complete logging configuration
    """
    log_format = "%(asctime)s %(levelname).8s [%(filename)s:%(lineno)d] %(message)s"
    date_format = "%H:%M:%S"

    # Ensure log directory exists
    if not os.path.exists(DEFAULT_LOG_DIR):
        os.makedirs(DEFAULT_LOG_DIR)

    # Generate log filename with current date
    date_str = datetime.now().date().isoformat()
    log_filename = f"{DEFAULT_LOG_DIR}/{LOG_FILE_PREFIX}{date_str}.log"

    logging_config: dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"standard": {"format": log_format, "datefmt": date_format}},
        "handlers": {
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "when": "midnight",
                "utc": True,
                "backupCount": LOG_BACKUP_COUNT,
                "level": logging.ERROR,
                "filename": log_filename,
                "formatter": "standard",
            }
        },
        "loggers": {"": {"handlers": ["file"], "level": LOGGING_LEVEL}},
    }

    # Add console handler for development mode
    if development:
        logging_config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": LOGGING_LEVEL,
            "stream": "ext://sys.stdout",
        }
        logging_config["loggers"][""]["handlers"].append("console")

    return logging_config


# Apply the logging configuration
dictConfig(configure_logging(development=DEVELOPMENT))
