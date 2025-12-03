"""License verification settings, URLs, and Pro feature constants."""

from environs import env


# Environment variables loading
try:
    env.read_env()
    print("Loaded environment variables from .env file")
except (OSError, FileNotFoundError):
    # In bundled apps, no .env file exists
    pass

# License verification settings
DEFAULT_LICENSE_TIMEOUT: int = 30  # seconds
DEFAULT_LICENSE_RETRY_COUNT: int = 3
DEFAULT_LICENSE_BACKOFF_RATE: float = 1.5
OFFLINE_GRACE_PERIOD_DAYS: int = 30

# License server URLs
LICENSE_SERVER_URL: str = env.str("LICENSE_SERVER_URL", default="https://payments.simonic.nl")
STRIPE_CHECKOUT_URI: str = env.str(
    "STRIPE_CHECKOUT_URI",
    default="/public/checkout/product/mixcloud_bulk_downloader/checkout/price_1S97L9Kz6QHWHfkNOu1VgYy3",
)
USER_FEEDBACK_BEARER_TOKEN: str = env.str(
    "USER_FEEDBACK_BEARER_TOKEN", default="EDaPmPUqVBB29aG6PydU8bWS0SFIO*RR$qIU8@yVEo#B1WIdar"
)

# Pro feature descriptions and pricing
PRO_FEATURES_LIST: list[str] = [
    "High quality downloads (192kbps)",
    "Convert to your favorite audio format (FLAC, MP3, AAC, WAV and more)",
    "Download and convert even faster in parallel" "Set your default download directory",
    "Priority customer support",
]
PRO_PRICE_TEXT: str = "Get MBD Pro for just $9.99!"

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
LICENSE_CHECKOUT_ERROR: str = (
    "Unable to load checkout page. Please try again or visit our website directly."
)
LICENSE_FEEDBACK_ERROR: str = (
    "Unable to send feedback at this time. Please try again later or contact support directly."
)

# Technical error messages for logging
LOG_LICENSE_HTTP_ERROR: str = "License verification HTTP error: {status_code} - {response_text}"
LOG_LICENSE_TIMEOUT: str = "License verification timeout after {timeout} seconds"
LOG_KEYRING_ERROR: str = "Keyring access error: {error}"
LOG_LICENSE_PARSE_ERROR: str = "Failed to parse license server response: {error}"
