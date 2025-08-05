"""Constants used throughout the Mixcloud Bulk Downloader application."""

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

# Logging
DEFAULT_LOG_DIR: str = "./logs"
LOG_FILE_PREFIX: str = "error_"
LOG_BACKUP_COUNT: int = 2
