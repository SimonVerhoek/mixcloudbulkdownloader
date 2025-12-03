"""Generic HTTP client base class for API interactions."""

from abc import ABC
from datetime import datetime, timezone
from typing import Any, Literal

import httpx

from app.qt_logger import log_api


class RateLimitError(Exception):
    """Custom exception for API rate limit errors with detailed information.

    Contains rate limit details from response headers for better error reporting.
    """

    def __init__(
        self, message: str, limit: int | None = None, reset_time: int | None = None
    ) -> None:
        """Initialize rate limit error with optional header data.

        Args:
            message: Error message
            limit: Rate limit value from x-ratelimit-limit header
            reset_time: Reset time in UTC epoch seconds from x-ratelimit-reset header
        """
        super().__init__(message)
        self.limit = limit
        self.reset_time = reset_time
        self.reset_time_utc = None

        if reset_time:
            try:
                # Convert epoch time to human-readable UTC time
                dt = datetime.fromtimestamp(reset_time, tz=timezone.utc)
                self.reset_time_utc = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, OSError):
                # Handle invalid timestamp values
                self.reset_time_utc = f"Invalid timestamp: {reset_time}"


class HTTPClientBase(ABC):
    """Abstract base class for HTTP API clients.

    Provides common HTTP request functionality that can be inherited by
    specific API client implementations.

    Subclasses must implement the prefetch_data method to define any
    initialization data loading behavior.
    """

    def __init__(self, base_url: str) -> None:
        """Initialize the HTTP client.

        Args:
            base_url (str): The base URL of the API server.
        """
        self._client = httpx.Client(base_url=base_url)

    def _request(
        self,
        method: Literal["GET", "POST"],
        path: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict[str, Any] | None:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method to use ("GET" or "POST").
            path: API endpoint path.
            params: Query parameters for GET requests.
            json: JSON body for POST requests.

        Returns:
            Response data as a dictionary, or None if request failed.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        req_params = {}
        if method == "GET" and params:
            req_params = {"params": params}
        elif method == "POST":
            req_params = {"json": json}

        resp = self._client.request(method=method, url=path, **req_params)

        try:
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            # Check if this is a GitHub rate limit error (403)
            if e.response.status_code == 403:
                # Look for rate limit in error message or URL
                error_str = str(e)
                if "rate limit" in error_str.lower() or "api.github.com" in error_str.lower():
                    # Extract rate limit headers
                    headers = e.response.headers
                    limit = None
                    reset_time = None

                    # Parse x-ratelimit-limit header
                    if "x-ratelimit-limit" in headers:
                        try:
                            limit = int(headers["x-ratelimit-limit"])
                        except ValueError:
                            pass

                    # Parse x-ratelimit-reset header
                    if "x-ratelimit-reset" in headers:
                        try:
                            reset_time = int(headers["x-ratelimit-reset"])
                        except ValueError:
                            pass

                    # Create enhanced log message
                    if limit and reset_time:
                        dt = datetime.fromtimestamp(reset_time, tz=timezone.utc)
                        reset_time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        log_message = f"GitHub rate limit exceeded ({limit} requests/hour), resets at {reset_time_str}"
                    elif limit:
                        log_message = f"GitHub rate limit exceeded ({limit} requests/hour), reset time unavailable"
                    elif reset_time:
                        dt = datetime.fromtimestamp(reset_time, tz=timezone.utc)
                        reset_time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        log_message = f"GitHub rate limit exceeded, resets at {reset_time_str}"
                    else:
                        log_message = "GitHub rate limit exceeded, no header details available"

                    # Log with enhanced information
                    log_api(log_message, "WARNING")

                    # Raise custom exception
                    raise RateLimitError("Rate limit exceeded", limit, reset_time) from e

            # Re-raise other HTTP errors as-is
            raise

    def _get(self, path: str, params: dict | None = None):
        """Make a GET request to the API.

        Args:
            path: API endpoint path.
            params: Query parameters.

        Returns:
            Response data as a dictionary.
        """
        return self._request(method="GET", path=path, params=params)

    def _post(self, path: str, json: dict | None = None):
        """Make a POST request to the API.

        Args:
            path: API endpoint path.
            json: JSON request body.

        Returns:
            Response data as a dictionary.
        """
        return self._request(method="POST", path=path, json=json)

    def stream(self, method: str, path: str, follow_redirects: bool = False, **kwargs):
        """Make a streaming HTTP request.

        Args:
            method: HTTP method to use
            path: URL or path to request
            follow_redirects: Whether to follow HTTP redirects
            **kwargs: Additional arguments to pass to httpx.stream()

        Returns:
            httpx streaming response context manager
        """
        return self._client.stream(method, path, follow_redirects=follow_redirects, **kwargs)

    def close(self) -> None:
        """Close the HTTP client and clean up resources.

        Should be called when the client is no longer needed to properly
        close network connections.
        """
        self._client.close()
