"""Settings configuration, keyring, and environment variable constants."""

from environs import env


# Development flag
DEVELOPMENT: bool = env.bool("DEVELOPMENT", default=False)

# Custom settings path override
CUSTOM_SETTINGS_PATH: str = env.str("CUSTOM_SETTINGS_PATH", default="")


# Keyring configuration
KEYRING_SERVICE_NAME: str = "mixcloud-bulk-downloader"
KEYRING_EMAIL_KEY: str = "license_email"
KEYRING_LICENSE_KEY: str = "license_key"
