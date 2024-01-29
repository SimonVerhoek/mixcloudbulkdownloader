import logging
import os
from datetime import datetime
from logging.config import dictConfig


LOGGING_LEVEL = int(os.getenv("LOGGING_LEVEL") or logging.INFO)
DEVELOPMENT = True if os.getenv("DEVELOPMENT") == True else False


def configure_logging(development: bool = False):
    log_format = "%(asctime)s %(levelname).8s [%(filename)s:%(lineno)d] %(message)s"
    date_format = "%H:%M:%S"

    log_dir = "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    date_str = datetime.now().date().isoformat()
    log_filename = f"{log_dir}/error_{date_str}.log"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"standard": {"format": log_format, "datefmt": date_format}},
        "handlers": {
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "when": "midnight",
                "utc": True,
                "backupCount": 2,
                "level": logging.ERROR,
                "filename": log_filename,
                "formatter": "standard",
            }
        },
        "loggers": {"": {"handlers": ["file"], "level": LOGGING_LEVEL}},
    }

    if development:
        logging_config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": LOGGING_LEVEL,
            "stream": "ext://sys.stdout",
        }
        logging_config["loggers"][""]["handlers"].append("console")

    return logging_config


dictConfig(configure_logging(development=DEVELOPMENT))
