"""Settings configuration, keyring, and environment variable constants."""

from environs import env

from app.services.system_service import cpu_count


# Development flag
DEVELOPMENT: bool = env.bool("DEVELOPMENT", default=False)

# Custom settings path override
CUSTOM_SETTINGS_PATH: str = env.str("CUSTOM_SETTINGS_PATH", default="")


# Threading settings - Pro only
DEFAULT_MAX_PARALLEL_DOWNLOADS: int = 3
DEFAULT_MAX_PARALLEL_CONVERSIONS: int = 2

# Setting keys
SETTING_MAX_PARALLEL_DOWNLOADS: str = "max_parallel_downloads"
SETTING_MAX_PARALLEL_CONVERSIONS: str = "max_parallel_conversions"

# Threading dropdown options
PARALLEL_DOWNLOADS_OPTIONS: list[int] = [1, 2, 3, 4, 5, 6, 7, 8]
PARALLEL_CONVERSIONS_OPTIONS: list[int] = [
    i for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] if i < cpu_count
]


# Keyring configuration
KEYRING_SERVICE_NAME: str = "mixcloud-bulk-downloader"
KEYRING_EMAIL_KEY: str = "license_email"
KEYRING_LICENSE_KEY: str = "license_key"
