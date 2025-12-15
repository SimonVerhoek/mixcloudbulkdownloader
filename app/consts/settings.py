"""Settings configuration, keyring, and environment variable constants."""

from environs import env

from app.services.system_service import cpu_count


# Load environment variables
try:
    env.read_env()
except (OSError, FileNotFoundError):
    # In bundled apps, no .env file exists
    pass

# Development flag
DEVELOPMENT: bool = env.bool("DEVELOPMENT", default=False)

# Custom settings path override
CUSTOM_SETTINGS_PATH: str = env.str("CUSTOM_SETTINGS_PATH", default="")

# Auto-update settings
AUTO_UPDATE_SHOW_PRERELEASE: bool = env.bool("AUTO_UPDATE_SHOW_PRERELEASE", default=False)


# Threading settings - Pro only
DEFAULT_MAX_PARALLEL_DOWNLOADS: int = 3
DEFAULT_MAX_PARALLEL_CONVERSIONS: int = 2

# Audio conversion settings - Pro only
DEFAULT_ENABLE_AUDIO_CONVERSION: bool = False

# Setting keys
SETTING_MAX_PARALLEL_DOWNLOADS: str = "max_parallel_downloads"
SETTING_MAX_PARALLEL_CONVERSIONS: str = "max_parallel_conversions"
SETTING_ENABLE_AUDIO_CONVERSION: str = "enable_audio_conversion"

# Threading dropdown options
PARALLEL_DOWNLOADS_OPTIONS: list[int] = [1, 2, 3, 4, 5, 6, 7, 8]
PARALLEL_CONVERSIONS_OPTIONS: list[int] = [
    i for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] if i < cpu_count
]


# Keyring configuration
KEYRING_SERVICE_NAME: str = "mixcloud-bulk-downloader"
KEYRING_EMAIL_KEY: str = "license_email"
KEYRING_LICENSE_KEY: str = "license_key"


# Update checking settings (startup only, no intervals)
SETTING_CHECK_UPDATES_ON_STARTUP: str = "check_updates_on_startup"
DEFAULT_CHECK_UPDATES_ON_STARTUP: bool = True

# GitHub API constants
GITHUB_API_BASE_URL: str = "https://api.github.com"
GITHUB_REPO_PATH: str = "/repos/SimonVerhoek/mixcloudbulkdownloader"
GITHUB_RELEASES_ENDPOINT: str = f"{GITHUB_REPO_PATH}/releases/latest"
GITHUB_RELEASES_ALL_ENDPOINT: str = f"{GITHUB_REPO_PATH}/releases"

# Platform mappings (corrected for actual release assets)
PLATFORM_FILE_EXTENSIONS: dict[str, str] = {
    "darwin": ".dmg",  # macOS
    "win32": ".zip",  # Windows (no .exe provided)
    "win64": ".zip",  # Windows 64-bit (no .exe provided)
}

# Update error messages
ERROR_UPDATE_CHECK_FAILED: str = "Failed to check for updates"
ERROR_GITHUB_RATE_LIMIT: str = "GitHub rate limit exceeded, try again later"
ERROR_NO_SUITABLE_DOWNLOAD: str = "No suitable download found for your platform"
