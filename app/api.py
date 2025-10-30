"""API functions for interacting with Mixcloud services."""

import httpx

from app.consts.api import ERROR_API_REQUEST_FAILED, MIXCLOUD_API_URL
from app.qt_logger import log_api, log_error


def search_user_API_url(phrase: str) -> str:
    """Generate API URL for searching users by phrase.

    Args:
        phrase: Search term to look for users

    Returns:
        Complete API URL for user search
    """
    return f"{MIXCLOUD_API_URL}/search/?q={phrase}&type=user"


def user_cloudcasts_API_url(username: str) -> str:
    """Generate API URL for fetching user's cloudcasts.

    Args:
        username: Mixcloud username

    Returns:
        Complete API URL for user's cloudcasts
    """
    return f"{MIXCLOUD_API_URL}/{username}/cloudcasts/"


def get_mixcloud_API_data(url: str) -> tuple[dict, str]:
    """Fetch data from Mixcloud API.

    Args:
        url: API endpoint URL to fetch from

    Returns:
        Tuple of (response_data, error_message).
        If successful, error_message is empty string.
        If failed, response_data may be None and error_message contains details.
    """
    response = None
    error = ""

    try:
        log_api(f"Making API request to: {url}", "DEBUG")
        req = httpx.get(url=url)
        response = req.json()
        log_api(f"API request successful for: {url}", "INFO")
    except (httpx.RequestError, httpx.HTTPStatusError, httpx.TimeoutException) as e:
        error = ERROR_API_REQUEST_FAILED
        log_error(f"{error}: {e}", "CRITICAL")

    if response and "error" in response:
        error_type = response["error"]["type"]
        error_msg = response["error"]["message"]
        error = f"{error_type}: {error_msg}"
        log_error(error, "CRITICAL")

    return response, error
