"""License server test stubs and mock server responses."""

from typing import Any
import httpx
from unittest.mock import Mock


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
        
    def post(self, url: str, *, json: dict[str, Any] = None, headers: dict[str, str] = None, timeout: httpx.Timeout = None) -> 'FakeLicenseServerResponse':
        """Simulate HTTP POST request to license server.
        
        Args:
            url: Request URL
            json: JSON payload
            headers: Request headers
            timeout: Request timeout
            
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
                f"HTTP {self.http_status_code}",
                request=Mock(),
                response=response
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
                    "error": None
                }
                return FakeLicenseServerResponse(response_data)
            else:
                # Invalid license
                response_data = {
                    "valid": False,
                    "product_name": None,
                    "product_title": None,
                    "expires_at": None,
                    "error": "Invalid license credentials"
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
        
    def set_custom_response(self, email: str, license_key: str, response_data: dict[str, Any]) -> None:
        """Set a custom response for specific credentials."""
        self.custom_responses[(email, license_key)] = response_data
        
    def set_network_error(self, should_error: bool = True, message: str = "Network connection failed") -> None:
        """Configure network error simulation."""
        self.should_raise_network_error = should_error
        self.network_error_message = message
        
    def set_timeout_error(self, should_error: bool = True, message: str = "Request timed out") -> None:
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
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=Mock(),
                response=self
            )


class StubLicenseServer:
    """High-level license server stub for integration testing."""
    
    def __init__(self) -> None:
        """Initialize license server stub."""
        self.client = FakeLicenseServerClient()
        
    def add_valid_license(self, email: str, license_key: str, 
                         product_title: str = "Mixcloud Bulk Downloader Pro") -> None:
        """Add a valid license to the server.
        
        Args:
            email: License email
            license_key: License key
            product_title: Product title for response
        """
        self.client.add_valid_license(email, license_key)
        # Optionally customize the response
        if product_title != "Mixcloud Bulk Downloader Pro":
            self.client.set_custom_response(email, license_key, {
                "valid": True,
                "product_name": "mixcloud_bulk_downloader",
                "product_title": product_title,
                "expires_at": None,
                "error": None
            })
            
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
        
    def get_request_history(self) -> dict[str, Any]:
        """Get history of requests made to the server."""
        return {
            "request_count": self.client.request_count,
            "last_url": self.client.last_url,
            "last_data": self.client.last_data,
            "last_headers": self.client.last_headers
        }
        
    def reset(self) -> None:
        """Reset server state for new test."""
        self.client.reset()