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

# flag to indicate whether
DEVELOPMENT: bool = env.bool("DEVELOPMENT", default=False)

STRIPE_DONATION_URL: str = env.str(
    "STRIPE_DONATION_URL", default="https://donate.stripe.com/fZu6oI5KtaOg01McbH2ZO00"
)

# License server URLs
LICENSE_SERVER_URL: str = env.str("LICENSE_SERVER_URL", default="https://payments.simonic.nl")
STRIPE_CHECKOUT_URL: str = env.str(
    "STRIPE_CHECKOUT_URL", default="https://buy.stripe.com/14A00kdcV4pSbKucbH2ZO01"
)

# Custom settings path override
CUSTOM_SETTINGS_PATH: str = env.str("CUSTOM_SETTINGS_PATH", default="")

# Feature flags (evaluated at import time)
FF_SETTINGS_PANE_ENABLED: bool = env.bool("FF_SETTINGS_PANE_ENABLED", default=False)

# Settings dialog dimensions
SETTINGS_DIALOG_WIDTH: int = 500
SETTINGS_DIALOG_HEIGHT: int = 400
SETTINGS_DIALOG_MIN_WIDTH: int = 400
SETTINGS_DIALOG_MIN_HEIGHT: int = 300

# License dialog dimensions
GET_PRO_DIALOG_WIDTH: int = 600
GET_PRO_DIALOG_HEIGHT: int = 550
LICENSE_SUCCESS_DIALOG_WIDTH: int = 500
LICENSE_SUCCESS_DIALOG_HEIGHT: int = 400
LICENSE_FAILURE_DIALOG_WIDTH: int = 500
LICENSE_FAILURE_DIALOG_HEIGHT: int = 350

# License verification settings
DEFAULT_LICENSE_TIMEOUT: int = 30  # seconds
DEFAULT_LICENSE_RETRY_COUNT: int = 3
DEFAULT_LICENSE_BACKOFF_RATE: float = 1.5
OFFLINE_GRACE_PERIOD_DAYS: int = 30

# Keyring configuration
KEYRING_SERVICE_NAME: str = "mixcloud-bulk-downloader"
KEYRING_EMAIL_KEY: str = "license_email"
KEYRING_LICENSE_KEY: str = "license_key"

# Pro feature descriptions and pricing
PRO_FEATURES_LIST: list[str] = [
    "Enjoy high quality downloads from Mixcloud Premium",
    "Choose your favorite audio format (FLAC, high-quality MP3)",
    "Set your default download directory",
    "Priority customer support",
]
PRO_PRICE_TEXT: str = "Get MBD Pro for just $24.99!"

# User-friendly error messages for dialogs
LICENSE_VERIFICATION_FAILED: str = (
    "We couldn't verify your license. Please check your internet connection and try again."
)
LICENSE_VERIFICATION_SUCCESS: str = (
    "Welcome to MBD Pro! You now have access to all premium features."
)
LICENSE_NETWORK_ERROR: str = "Network error occurred. Please check your internet connection."
LICENSE_INVALID_CREDENTIALS: str = (
    "Invalid license credentials. Please check your email and license key."
)
LICENSE_SERVER_ERROR: str = "License server temporarily unavailable. Please try again later."

# Technical error messages for logging
LOG_LICENSE_HTTP_ERROR: str = "License verification HTTP error: {status_code} - {response_text}"
LOG_LICENSE_TIMEOUT: str = "License verification timeout after {timeout} seconds"
LOG_KEYRING_ERROR: str = "Keyring access error: {error}"
LOG_LICENSE_PARSE_ERROR: str = "Failed to parse license server response: {error}"
