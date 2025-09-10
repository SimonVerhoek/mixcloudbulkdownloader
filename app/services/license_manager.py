"""License management for Mixcloud Bulk Downloader Pro features."""

import time
from typing import Any

import httpx

from app.consts import (
    DEFAULT_LICENSE_BACKOFF_RATE,
    DEFAULT_LICENSE_RETRY_COUNT,
    DEFAULT_LICENSE_TIMEOUT,
    LICENSE_SERVER_URL,
    LOG_LICENSE_HTTP_ERROR,
    LOG_LICENSE_PARSE_ERROR,
    LOG_LICENSE_TIMEOUT,
    OFFLINE_GRACE_PERIOD_DAYS,
)
from app.qt_logger import log_api, log_error
from app.services.settings_manager import settings


class LicenseManager:
    """Manages license verification and pro status for the application.

    This singleton class handles all license-related operations including:
    - License verification against remote server
    - Pro status management
    - Integration with settings for credential storage
    - Offline grace period handling
    """

    def __init__(self) -> None:
        """Initialize the license manager with settings reference."""
        self.settings = settings  # Use the singleton instance
        self.is_pro = False  # Attribute set by verify_license(), not computed

    def _send_request_to_licensing_server(
        self,
        method: str,
        uri: str,
        url_params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: int = DEFAULT_LICENSE_TIMEOUT,
        max_retries: int = DEFAULT_LICENSE_RETRY_COUNT,
        backoff_rate: float = DEFAULT_LICENSE_BACKOFF_RATE,
    ) -> dict[str, Any] | None:
        """Send HTTP request to license server with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            uri: URI path relative to LICENSE_SERVER_URL.
            url_params: URL query parameters.
            payload: JSON payload for request body.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            backoff_rate: Exponential backoff multiplier for retries.

        Returns:
            Dict containing response JSON data, or None if all attempts failed.
        """
        # Cast timeout to httpx.Timeout inside the method
        http_timeout = httpx.Timeout(timeout=timeout)

        # Construct full URL
        full_url = f"{LICENSE_SERVER_URL}{uri}"

        # Attempt request with retry logic
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=http_timeout) as client:
                    # Send request using generic client.request method
                    request_kwargs = {"params": url_params} if url_params else {}
                    if payload is not None:
                        request_kwargs["json"] = payload

                    response = client.request(method=method.upper(), url=full_url, **request_kwargs)

                    response.raise_for_status()

                    # Parse and validate response
                    response_data = response.json()

                    # Validate required fields
                    if not isinstance(response_data, dict):
                        log_error(
                            message=LOG_LICENSE_PARSE_ERROR.format(
                                error="Response is not a JSON object"
                            )
                        )
                        continue

                    return response_data

            except httpx.TimeoutException as e:
                last_exception = e
                log_error(message=LOG_LICENSE_TIMEOUT.format(timeout=timeout))

            except httpx.HTTPStatusError as e:
                last_exception = e
                log_error(
                    message=LOG_LICENSE_HTTP_ERROR.format(
                        status_code=e.response.status_code, response_text=str(e)
                    )
                )

            except httpx.RequestError as e:
                last_exception = e
                log_error(message=f"License server network error: {e}")

            except (ValueError, KeyError) as e:
                last_exception = e
                log_error(message=LOG_LICENSE_PARSE_ERROR.format(error=str(e)))

            except Exception as e:
                last_exception = e
                log_error(message=f"Unexpected license server error: {e}")

            # If this was the last attempt, break
            if attempt >= max_retries:
                break

            # Calculate delay for exponential backoff
            delay = backoff_rate**attempt
            log_api(
                message=f"License server request attempt {attempt + 1}/{max_retries + 1} failed, retrying in {delay:.1f}s...",
                level="WARNING",
            )
            time.sleep(delay)

        # All retry attempts failed
        log_error(
            message=f"License server request failed after {max_retries + 1} attempts. Last error: {last_exception}"
        )
        return None

    def verify_license(
        self,
        email: str | None = None,
        license_key: str | None = None,
        max_retries: int = DEFAULT_LICENSE_RETRY_COUNT,
        backoff_rate: float = DEFAULT_LICENSE_BACKOFF_RATE,
        timeout: int = DEFAULT_LICENSE_TIMEOUT,
    ) -> bool:
        """Verify license credentials against the license server.

        Args:
            email: License email. If None, retrieves from settings.
            license_key: License key. If None, retrieves from settings.
            max_retries: Maximum number of retry attempts.
            backoff_rate: Exponential backoff multiplier for retries.
            timeout: Request timeout in seconds.

        Returns:
            bool: True if license is valid, False otherwise.
        """
        # If not provided, get from settings
        if email is None:
            email = self.settings.email
        if license_key is None:
            license_key = self.settings.license_key

        if not email or not license_key:
            self.is_pro = False
            return False

        # Prepare request data
        request_payload = {"email": email, "license_key": license_key}

        # Send request using the generic _send_request_to_licensing_server method
        response_data = self._send_request_to_licensing_server(
            method="POST",
            uri="/public/license/verify",
            payload=request_payload,
            timeout=timeout,
            max_retries=max_retries,
            backoff_rate=backoff_rate,
        )

        # If request failed completely, check offline status
        if response_data is None:
            if self.check_offline_status():
                log_api(message="Maintaining pro status due to offline grace period", level="INFO")
                # Keep current is_pro status (don't change it)
                return self.is_pro
            else:
                log_api(
                    message="license outside grace period or never verified. Disabling pro...",
                    level="WARNING",
                )
                # Outside grace period or never verified - disable pro features
                self.is_pro = False
                return False

        # Process successful response
        is_valid = response_data.get("valid", False)
        product_name = response_data.get("product_name")

        if is_valid and product_name == "mixcloud_bulk_downloader":
            log_api(message=f"acknowledged pro status for {product_name}", level="INFO")
            # Successful verification
            self.is_pro = True
            self.update_verification_timestamp()
            return True
        else:
            # Invalid license or wrong product
            error_msg = response_data.get("error", "Invalid license")
            log_api(
                message=f"License verification failed: {error_msg}. No pro status granted",
                level="WARNING",
            )
            self.is_pro = False
            return False

    def check_offline_status(self) -> bool:
        """Check if pro status should remain valid during offline period.

        Returns:
            bool: True if within offline grace period, False otherwise.

        Note:
            This method checks the last successful verification timestamp
            and determines if we're still within the offline grace period.
        """
        last_verification = self.settings.last_successful_verification
        if last_verification == 0.0:
            # Never successfully verified
            return False

        current_time = time.time()
        grace_period_seconds = OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60

        return (current_time - last_verification) <= grace_period_seconds

    def update_verification_timestamp(self) -> None:
        """Update the last successful verification timestamp to current time."""
        self.settings.last_successful_verification = time.time()

    def get_license_status_info(self) -> dict[str, Any]:
        """Get comprehensive license status information for debugging/UI.

        Returns:
            dict: Dictionary containing license status details.
        """
        return {
            "is_pro": self.is_pro,
            "email": self.settings.email,
            "has_license_key": bool(self.settings.license_key),
            "last_verification": self.settings.last_successful_verification,
            "within_offline_period": self.check_offline_status(),
            "offline_grace_days": OFFLINE_GRACE_PERIOD_DAYS,
        }


# Create module-level singleton instance
license_manager = LicenseManager()
