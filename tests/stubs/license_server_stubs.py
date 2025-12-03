"""License server test stubs and mock server responses."""

from typing import Any
from unittest.mock import Mock

import httpx


class FakeLicenseServerClient:
    """Fake HTTP client that simulates license server responses."""

    def __init__(self) -> None:
        """Initialize fake license server client."""
        self.request_count = 0
        self.last_url = ""
        self.last_data = {}
        self.last_headers = {}

        # Response configuration
        self.should_raise_network_error = False
        self.should_raise_http_error = False
        self.should_raise_timeout_error = False
        self.http_status_code = 500
        self.network_error_message = "Network connection failed"
        self.timeout_error_message = "Request timed out"

        # License validation responses
        self.valid_licenses: set[tuple[str, str]] = set()  # (email, license_key) pairs
        self.custom_responses: dict[tuple[str, str], dict[str, Any]] = {}

        # Default valid license for testing
        self.valid_licenses.add(("test@example.com", "valid-license-123"))

    def request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] = None,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        timeout: httpx.Timeout = None,
    ) -> "FakeLicenseServerResponse":
        """Simulate HTTP request to license server.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            json: JSON payload
            headers: Request headers
            params: URL parameters
            timeout: Request timeout

        Returns:
            Fake license server response

        Raises:
            httpx.RequestError: When should_raise_network_error is True
            httpx.TimeoutException: When should_raise_timeout_error is True
            httpx.HTTPStatusError: When should_raise_http_error is True
        """
        return self._handle_request(method, url, json=json, headers=headers, params=params)

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any] = None,
        headers: dict[str, str] = None,
        timeout: httpx.Timeout = None,
    ) -> "FakeLicenseServerResponse":
        """Simulate HTTP POST request to license server."""
        return self._handle_request("POST", url, json=json, headers=headers)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        timeout: httpx.Timeout = None,
    ) -> "FakeLicenseServerResponse":
        """Simulate HTTP GET request to license server."""
        return self._handle_request("GET", url, headers=headers, params=params)

    def _handle_request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] = None,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
    ) -> "FakeLicenseServerResponse":
        """Handle HTTP request to license server.

        Args:
            method: HTTP method
            url: Request URL
            json: JSON payload
            headers: Request headers
            params: URL parameters

        Returns:
            Fake license server response

        Raises:
            httpx.RequestError: When should_raise_network_error is True
            httpx.TimeoutException: When should_raise_timeout_error is True
            httpx.HTTPStatusError: When should_raise_http_error is True
        """
        self.request_count += 1
        self.last_url = url
        self.last_data = json or {}
        self.last_headers = headers or {}

        if self.should_raise_network_error:
            raise httpx.RequestError(self.network_error_message)

        if self.should_raise_timeout_error:
            raise httpx.TimeoutException(self.timeout_error_message)

        if self.should_raise_http_error:
            response = FakeLicenseServerResponse({}, status_code=self.http_status_code)
            raise httpx.HTTPStatusError(
                f"HTTP {self.http_status_code}", request=Mock(), response=response
            )

        # Process license verification request
        if "license/verify" in url and json:
            email = json.get("email", "")
            license_key = json.get("license_key", "")

            # Check for custom response first
            if (email, license_key) in self.custom_responses:
                response_data = self.custom_responses[(email, license_key)]
                return FakeLicenseServerResponse(response_data)

            # Check valid licenses
            if (email, license_key) in self.valid_licenses:
                response_data = {
                    "valid": True,
                    "product_name": "mixcloud_bulk_downloader",
                    "product_title": "Mixcloud Bulk Downloader Pro",
                    "expires_at": None,
                    "error": None,
                }
                return FakeLicenseServerResponse(response_data)
            else:
                # Invalid license
                response_data = {
                    "valid": False,
                    "product_name": None,
                    "product_title": None,
                    "expires_at": None,
                    "error": "Invalid license credentials",
                }
                return FakeLicenseServerResponse(response_data)

        # Process feedback submission request
        elif "public/user_feedback" in url and json:
            # Validate required fields
            feedback_text = json.get("feedback_text", "")
            email = json.get("email")
            product_name = json.get("product_name", "")

            if not feedback_text:
                response_data = {"error": "feedback_text is required"}
                return FakeLicenseServerResponse(response_data, status_code=400)

            if not product_name:
                response_data = {"error": "product_name is required"}
                return FakeLicenseServerResponse(response_data, status_code=400)

            # Check for proper authorization header
            auth_header = self.last_headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                response_data = {"error": "Missing or invalid authorization header"}
                return FakeLicenseServerResponse(response_data, status_code=401)

            # Success response
            response_data = {
                "success": True,
                "message": "Feedback received successfully",
                "feedback_id": "test-feedback-123",
            }
            return FakeLicenseServerResponse(response_data)

        # Process checkout URL request (GET)
        elif "checkout" in url and method == "GET":
            # Simulate checkout URL generation
            response_data = {
                "checkout_url": "https://checkout.stripe.com/test-checkout-session-123",
                "checkout_id": "test-checkout-123",
            }
            return FakeLicenseServerResponse(response_data)

        # Default response for unknown endpoints
        return FakeLicenseServerResponse({"error": "Unknown endpoint"}, status_code=404)

    def close(self) -> None:
        """Simulate client closure."""
        pass

    # Test configuration methods
    def add_valid_license(self, email: str, license_key: str) -> None:
        """Add a valid license for testing."""
        self.valid_licenses.add((email, license_key))

    def remove_valid_license(self, email: str, license_key: str) -> None:
        """Remove a valid license from testing."""
        self.valid_licenses.discard((email, license_key))

    def set_custom_response(
        self, email: str, license_key: str, response_data: dict[str, Any]
    ) -> None:
        """Set a custom response for specific credentials."""
        self.custom_responses[(email, license_key)] = response_data

    def set_network_error(
        self, should_error: bool = True, message: str = "Network connection failed"
    ) -> None:
        """Configure network error simulation."""
        self.should_raise_network_error = should_error
        self.network_error_message = message

    def set_timeout_error(
        self, should_error: bool = True, message: str = "Request timed out"
    ) -> None:
        """Configure timeout error simulation."""
        self.should_raise_timeout_error = should_error
        self.timeout_error_message = message

    def set_http_error(self, should_error: bool = True, status_code: int = 500) -> None:
        """Configure HTTP error simulation."""
        self.should_raise_http_error = should_error
        self.http_status_code = status_code

    def reset(self) -> None:
        """Reset stub state for new test."""
        self.request_count = 0
        self.last_url = ""
        self.last_data = {}
        self.last_headers = {}
        self.should_raise_network_error = False
        self.should_raise_http_error = False
        self.should_raise_timeout_error = False
        self.http_status_code = 500
        self.valid_licenses = {("test@example.com", "valid-license-123")}
        self.custom_responses.clear()


class FakeLicenseServerResponse:
    """Fake license server HTTP response."""

    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        """Initialize fake response.

        Args:
            json_data: JSON data to return
            status_code: HTTP status code
        """
        self._json_data = json_data
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        """Return JSON data."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise exception for HTTP errors."""
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=Mock(), response=self)


class StubLicenseServer:
    """High-level license server stub for integration testing."""

    def __init__(self) -> None:
        """Initialize license server stub."""
        self.client = FakeLicenseServerClient()

    def add_valid_license(
        self, email: str, license_key: str, product_title: str = "Mixcloud Bulk Downloader Pro"
    ) -> None:
        """Add a valid license to the server.

        Args:
            email: License email
            license_key: License key
            product_title: Product title for response
        """
        self.client.add_valid_license(email, license_key)
        # Optionally customize the response
        if product_title != "Mixcloud Bulk Downloader Pro":
            self.client.set_custom_response(
                email,
                license_key,
                {
                    "valid": True,
                    "product_name": "mixcloud_bulk_downloader",
                    "product_title": product_title,
                    "expires_at": None,
                    "error": None,
                },
            )

    def simulate_server_error(self, error_type: str = "http", **kwargs) -> None:
        """Simulate various server errors.

        Args:
            error_type: Type of error - "network", "timeout", "http"
            **kwargs: Additional error configuration
        """
        if error_type == "network":
            self.client.set_network_error(True, kwargs.get("message", "Network error"))
        elif error_type == "timeout":
            self.client.set_timeout_error(True, kwargs.get("message", "Timeout error"))
        elif error_type == "http":
            self.client.set_http_error(True, kwargs.get("status_code", 500))

    def simulate_malformed_response(self, email: str, license_key: str) -> None:
        """Simulate malformed JSON response."""
        # This will be caught as a JSON parsing error by the actual client
        self.client.set_custom_response(email, license_key, {"malformed": "response"})

    def set_feedback_auth_token(self, token: str) -> None:
        """Set the expected bearer token for feedback requests.

        Args:
            token: Bearer token to expect in Authorization header
        """
        # This is handled by the client checking the Authorization header
        pass

    def simulate_feedback_validation_error(self, error_type: str = "missing_text") -> None:
        """Simulate feedback validation errors.

        Args:
            error_type: Type of validation error - "missing_text", "missing_product"
        """
        # These are handled automatically by the client validation logic
        pass

    def set_checkout_response(self, checkout_url: str, checkout_id: str) -> None:
        """Customize checkout URL response.

        Args:
            checkout_url: Custom checkout URL to return
            checkout_id: Custom checkout ID to return
        """
        # For now, the client returns fixed test values
        # In the future, this could be made configurable
        pass

    def get_request_history(self) -> dict[str, Any]:
        """Get history of requests made to the server."""
        return {
            "request_count": self.client.request_count,
            "last_url": self.client.last_url,
            "last_data": self.client.last_data,
            "last_headers": self.client.last_headers,
        }

    def reset(self) -> None:
        """Reset server state for new test."""
        self.client.reset()


class StubLicenseManager:
    """Stub license manager for testing without network dependencies.

    Provides a mock implementation of LicenseManager that can be configured
    for different test scenarios without making actual HTTP requests.
    """

    def __init__(self) -> None:
        """Initialize stub license manager."""
        # License status properties
        self._is_pro = False
        self.email = None
        self.license_key = None
        self.last_successful_verification = 0.0

        # Configurable behaviors
        self.should_verify_fail = False
        self.verify_failure_reason = "Invalid license"
        self.should_get_checkout_fail = False
        self.checkout_failure_reason = "Payment server error"
        self.should_submit_feedback_fail = False
        self.feedback_failure_reason = "Feedback server error"

        # Response data for successful operations
        self.checkout_url = "https://checkout.stripe.com/test-session-123"
        self.checkout_id = "test-checkout-123"

        # Call history for assertions
        self.verify_calls = 0
        self.checkout_calls = 0
        self.feedback_calls = []

    @property
    def is_pro(self) -> bool:
        """Get current Pro status."""
        return self._is_pro

    @is_pro.setter
    def is_pro(self, value: bool) -> None:
        """Set Pro status."""
        self._is_pro = value

    def verify_license(
        self, max_retries: int = 3, backoff_rate: float = 2.0, timeout: int = 30
    ) -> bool:
        """Mock license verification.

        Args:
            max_retries: Maximum retry attempts (ignored in stub)
            backoff_rate: Backoff multiplier (ignored in stub)
            timeout: Request timeout (ignored in stub)

        Returns:
            bool: True if verification succeeds, False if configured to fail
        """
        self.verify_calls += 1

        if self.should_verify_fail:
            self._is_pro = False
            return False

        self._is_pro = True
        self.last_successful_verification = 1234567890.0  # Fixed timestamp for testing
        return True

    def check_offline_status(self) -> bool:
        """Mock offline status check.

        Returns:
            bool: True if has previous verification, False otherwise
        """
        return self.last_successful_verification > 0.0

    def update_verification_timestamp(self) -> None:
        """Mock timestamp update."""
        self.last_successful_verification = 1234567890.0

    def get_checkout_url(self) -> str:
        """Mock checkout URL retrieval.

        Returns:
            str: Checkout URL if successful

        Raises:
            Exception: If configured to fail
        """
        self.checkout_calls += 1

        if self.should_get_checkout_fail:
            raise Exception(self.checkout_failure_reason)

        return self.checkout_url

    def submit_feedback(self, feedback_text: str, email: str | None = None) -> None:
        """Mock feedback submission.

        Args:
            feedback_text: User feedback message
            email: Optional email for response

        Raises:
            Exception: If configured to fail
        """
        self.feedback_calls.append({"feedback_text": feedback_text, "email": email})

        if self.should_submit_feedback_fail:
            raise Exception(self.feedback_failure_reason)

    def get_license_status_info(self) -> dict[str, Any]:
        """Mock license status information.

        Returns:
            dict: License status details for testing
        """
        return {
            "is_pro": self._is_pro,
            "email": self.email,
            "has_license_key": bool(self.license_key),
            "last_verification": self.last_successful_verification,
            "within_offline_period": self.check_offline_status(),
            "offline_grace_days": 7,  # Fixed value for testing
        }

    # Test configuration methods
    def configure_as_pro_user(
        self, email: str = "test@example.com", license_key: str = "valid-license-123"
    ) -> None:
        """Configure stub as a Pro user with valid credentials."""
        self._is_pro = True
        self.email = email
        self.license_key = license_key
        self.last_successful_verification = 1234567890.0
        self.should_verify_fail = False

    def configure_as_free_user(self) -> None:
        """Configure stub as a free user without Pro status."""
        self._is_pro = False
        self.email = None
        self.license_key = None
        self.last_successful_verification = 0.0

    def configure_verify_failure(self, reason: str = "Invalid license") -> None:
        """Configure license verification to fail."""
        self.should_verify_fail = True
        self.verify_failure_reason = reason

    def configure_checkout_failure(self, reason: str = "Payment server error") -> None:
        """Configure checkout URL retrieval to fail."""
        self.should_get_checkout_fail = True
        self.checkout_failure_reason = reason

    def configure_feedback_failure(self, reason: str = "Feedback server error") -> None:
        """Configure feedback submission to fail."""
        self.should_submit_feedback_fail = True
        self.feedback_failure_reason = reason

    def reset(self) -> None:
        """Reset stub state for new test."""
        self._is_pro = False
        self.email = None
        self.license_key = None
        self.last_successful_verification = 0.0
        self.should_verify_fail = False
        self.should_get_checkout_fail = False
        self.should_submit_feedback_fail = False
        self.verify_calls = 0
        self.checkout_calls = 0
        self.feedback_calls.clear()
