"""Constants used throughout the Mixcloud Bulk Downloader application."""

from environs import env


# API URLs
MIXCLOUD_API_URL: str = "https://api.mixcloud.com"

# UI Constants
MAIN_WINDOW_MIN_WIDTH: int = 700
MAIN_WINDOW_MIN_HEIGHT: int = 400

# Tree widget column sizes
TREE_SELECT_COLUMN_WIDTH: int = 50
TREE_TITLE_COLUMN_WIDTH: int = 400
TREE_STATUS_COLUMN_WIDTH: int = 200

# Layout stretch ratios
SEARCH_LABEL_STRETCH: int = 1
SEARCH_INPUT_STRETCH: int = 3
SEARCH_BUTTON_STRETCH: int = 1

# File extensions
AUDIO_EXTENSION: str = ".m4a"

# Known audio/video file extensions for progress tracking
KNOWN_MEDIA_EXTENSIONS: set[str] = {
    ".mp3",
    ".m4a",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".mp4",
    ".avi",
    ".mkv",
    ".webm",
}

# Progress messages
PROGRESS_UNKNOWN: str = "unknown"
PROGRESS_DONE: str = "Done!"

# Error messages
ERROR_NO_DOWNLOAD_DIR: str = "no download directory provided"
ERROR_NO_USER_PROVIDED: str = "no user provided"
ERROR_NO_SEARCH_PHRASE: str = "no search phrase provided"
ERROR_API_REQUEST_FAILED: str = "Failed to query Mixcloud API"

# Qt Logging Configuration
QT_LOG_MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB per log file
QT_LOG_BACKUP_COUNT: int = 5  # Keep 5 backup files
QT_LOG_CATEGORIES: dict[str, str] = {
    "UI": "app.ui",
    "API": "app.api",
    "DOWNLOAD": "app.download",
    "THREAD": "app.threads",
    "ERROR": "app.error",
}

# Environment variables
try:
    env.read_env()
    print("Loaded environment variables from .env file")
except (OSError, FileNotFoundError):
    # In bundled apps, no .env file exists
    pass

STRIPE_DONATION_URL: str = env.str(
    "STRIPE_DONATION_URL", default="https://donate.stripe.com/fZu6oI5KtaOg01McbH2ZO00"
)

# Feature flags (evaluated at import time)
FF_SETTINGS_PANE_ENABLED: bool = env.bool("FF_SETTINGS_PANE_ENABLED", default=False)

# Settings dialog dimensions
SETTINGS_DIALOG_WIDTH: int = 500
SETTINGS_DIALOG_HEIGHT: int = 400
SETTINGS_DIALOG_MIN_WIDTH: int = 400
SETTINGS_DIALOG_MIN_HEIGHT: int = 300
