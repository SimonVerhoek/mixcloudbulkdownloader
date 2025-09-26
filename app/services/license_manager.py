"""License management for Mixcloud Bulk Downloader Pro features."""

import time
from typing import Any

import httpx
from PySide6.QtCore import QObject, Signal

from app.consts.license import (
    DEFAULT_LICENSE_BACKOFF_RATE,
    DEFAULT_LICENSE_RETRY_COUNT,
    DEFAULT_LICENSE_TIMEOUT,
    LICENSE_SERVER_URL,
    LOG_LICENSE_HTTP_ERROR,
    LOG_LICENSE_PARSE_ERROR,
    LOG_LICENSE_TIMEOUT,
    OFFLINE_GRACE_PERIOD_DAYS,
    STRIPE_CHECKOUT_URI,
    USER_FEEDBACK_BEARER_TOKEN,
)
from app.qt_logger import log_api, log_error
from app.services.settings_manager import settings


class LicenseManager(QObject):
    """Manages license verification and pro status for the application.

    This singleton class handles all license-related operations including:
    - License verification against remote server
    - Pro status management
    - Integration with settings for credential storage
    - Offline grace period handling
    - Qt signals for license status changes
    """

    # Signal emitted when license status changes (is_pro: bool)
    license_status_changed = Signal(bool)

    def __init__(self) -> None:
        """Initialize the license manager with settings reference."""
        super().__init__()
        self.settings = settings  # Use the singleton instance
        self._is_pro = False  # Private attribute to track changes

        # Initialize Pro status for offline users with valid credentials
        self._initialize_pro_status()

    @property
    def is_pro(self) -> bool:
        """Get the current Pro license status."""
        return self._is_pro

    @is_pro.setter
    def is_pro(self, value: bool) -> None:
        """Set the Pro license status and emit signal if changed."""
        if self._is_pro != value:
            self._is_pro = value
            self.license_status_changed.emit(value)

    def _initialize_pro_status(self) -> None:
        """Initialize Pro status based on stored credentials and verification history.

        This method is called during initialization to give immediate Pro access
        to users who have valid stored credentials AND evidence of previous successful
        verification. This ensures offline users get Pro features immediately at startup
        while maintaining security for first-time users.
        """
        # Check if we have valid stored credentials
        email = self.settings.email
        license_key = self.settings.license_key
        last_verification = self.settings.last_successful_verification

        if email and license_key and last_verification > 0.0:
            # Give immediate Pro access for stored credentials with verification history
            # This indicates the license was successfully verified at least once before
            self._is_pro = True
            log_api(
                message="Initialized with Pro status due to stored credentials and verification history",
                level="INFO",
            )

    def _send_request_to_licensing_server(
        self,
        method: str,
        uri: str,
        url_params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: int = DEFAULT_LICENSE_TIMEOUT,
        max_retries: int = DEFAULT_LICENSE_RETRY_COUNT,
        backoff_rate: float = DEFAULT_LICENSE_BACKOFF_RATE,
        headers: dict[str, Any] | None = None,
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
            headers: HTTP headers to include in the request.

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
                    if headers is not None:
                        request_kwargs["headers"] = headers

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
        max_retries: int = DEFAULT_LICENSE_RETRY_COUNT,
        backoff_rate: float = DEFAULT_LICENSE_BACKOFF_RATE,
        timeout: int = DEFAULT_LICENSE_TIMEOUT,
    ) -> bool:
        """Verify license credentials against the license server.

        Args:
            max_retries: Maximum number of retry attempts.
            backoff_rate: Exponential backoff multiplier for retries.
            timeout: Request timeout in seconds.

        Returns:
            bool: True if license is valid, False otherwise.
        """
        email = self.settings.email
        license_key = self.settings.license_key

        if not email or not license_key:
            log_api(
                message=f"No license credentials found. Pro status is set to <{self.is_pro}>",
                level="INFO",
            )
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

        # If request failed completely, check if we're within the offline grace period
        if response_data is None:
            if self.check_offline_status():
                log_api(
                    message=f"License server unreachable - Pro status remains <{self.is_pro}> (within grace period)",
                    level="WARNING",
                )
                return self.is_pro
            else:
                log_api(
                    message=f"License server unreachable and outside grace period - revoking Pro status",
                    level="WARNING",
                )
                self.is_pro = False
                return False

        # Process successful response
        is_valid = response_data.get("valid", False)
        product_name = response_data.get("product_name")

        if is_valid and product_name == "mixcloud_bulk_downloader":
            log_api(
                message=f"License server acknowledged pro status for {product_name}", level="INFO"
            )
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

    def get_checkout_url(self) -> str:
        """Get checkout URL from payment server.

        Makes a GET request to the Stripe checkout URI to retrieve the actual
        checkout URL and checkout ID from the payment server.

        Returns:
            Checkout URL string if successful.

        Raises:
            Exception: If request fails or response is invalid.
        """
        # Make GET request to the checkout URI using existing method
        response_data = self._send_request_to_licensing_server(
            method="GET",
            uri=STRIPE_CHECKOUT_URI,
            timeout=DEFAULT_LICENSE_TIMEOUT,
        )

        # Handle case where request completely failed
        if response_data is None:
            raise Exception("Failed to connect to payment server")

        # Extract required fields from response
        try:
            checkout_url = response_data["checkout_url"]
            checkout_id = response_data["checkout_id"]
        except KeyError as e:
            raise Exception(f"Invalid response from payment server: missing {e}")

        # Log the checkout ID for tracking
        log_api(message=f"Retrieved checkout URL with ID: {checkout_id}", level="INFO")

        return checkout_url

    def submit_feedback(self, feedback_text: str, email: str | None = None) -> None:
        """Submit user feedback to license server.

        Args:
            feedback_text: The user's feedback message
            email: Optional email address for response

        Raises:
            Exception: If request fails or server unreachable
        """
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {USER_FEEDBACK_BEARER_TOKEN}",
            "Content-Type": "application/json",
        }

        # Prepare payload
        payload = {
            "feedback_text": feedback_text,
            "email": email,
            "product_name": "mixcloud_bulk_downloader",
        }

        # Use existing infrastructure
        response_data = self._send_request_to_licensing_server(
            method="POST", uri="/public/user_feedback", payload=payload, headers=headers
        )

        # Handle failure
        if response_data is None:
            raise Exception("Failed to connect to feedback server")

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
