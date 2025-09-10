"""API-related test stubs for HTTP client and API service."""

from typing import Any
import httpx

from app.services.api_service import MixcloudAPIService


class FakeHTTPClient:
    """Fake HTTP client that returns predefined responses."""
    
    def __init__(self) -> None:
        """Initialize fake client with response mapping."""
        self.responses: dict[str, dict[str, Any]] = {
            # User search responses
            "search_user_success": {
                "data": [
                    {
                        "key": "/testuser/",
                        "name": "Test User",
                        "pictures": {"large": "https://example.com/large.jpg"},
                        "url": "https://www.mixcloud.com/testuser/",
                        "username": "testuser"
                    },
                    {
                        "key": "/anotheruser/",
                        "name": "Another User",
                        "pictures": {},
                        "url": "https://www.mixcloud.com/anotheruser/",
                        "username": "anotheruser"
                    }
                ]
            },
            
            # Cloudcast responses
            "cloudcasts_page1": {
                "data": [
                    {
                        "name": "Test Mix 1",
                        "url": "https://www.mixcloud.com/testuser/test-mix-1/"
                    },
                    {
                        "name": "Test Mix 2", 
                        "url": "https://www.mixcloud.com/testuser/test-mix-2/"
                    }
                ],
                "paging": {
                    "next": "https://api.mixcloud.com/testuser/cloudcasts/?offset=20"
                }
            },
            
            "cloudcasts_page2": {
                "data": [
                    {
                        "name": "Test Mix 3",
                        "url": "https://www.mixcloud.com/testuser/test-mix-3/"
                    }
                ]
            },
            
            # Error responses
            "user_not_found": {
                "error": {
                    "type": "NotFound",
                    "message": "User not found"
                }
            },
            
            "api_error": {
                "error": {
                    "type": "InvalidRequest",
                    "message": "Invalid search query"
                }
            }
        }
        
        self.request_count = 0
        self.last_url = ""
        self.should_raise_network_error = False
        self.should_raise_http_error = False
        self.http_status_code = 404
        
    def get(self, url: str) -> 'FakeHTTPResponse':
        """Simulate HTTP GET request.
        
        Args:
            url: Request URL
            
        Returns:
            Fake HTTP response
            
        Raises:
            httpx.RequestError: When should_raise_network_error is True
            httpx.HTTPStatusError: When should_raise_http_error is True
        """
        self.request_count += 1
        self.last_url = url
        
        if self.should_raise_network_error:
            raise httpx.RequestError("Simulated network error")
            
        if self.should_raise_http_error:
            response = FakeHTTPResponse({}, status_code=self.http_status_code)
            raise httpx.HTTPStatusError(
                "HTTP Error", 
                request=None, 
                response=response
            )
        
        # Determine response based on URL patterns
        if "search" in url and "type=user" in url:
            if "q=" in url and "q=&" in url:  # Empty search phrase
                return FakeHTTPResponse({"data": []})
            elif "nonexistent" in url:
                return FakeHTTPResponse(self.responses["user_not_found"])
            elif "error" in url:
                return FakeHTTPResponse(self.responses["user_not_found"])
            else:
                return FakeHTTPResponse(self.responses["search_user_success"])
                
        elif "cloudcasts" in url:
            if "offset=20" in url:
                return FakeHTTPResponse(self.responses["cloudcasts_page2"])
            else:
                return FakeHTTPResponse(self.responses["cloudcasts_page1"])
                
        # Default empty response
        return FakeHTTPResponse({"data": []})
        
    def close(self) -> None:
        """Simulate client closure."""
        pass


class FakeHTTPResponse:
    """Fake HTTP response object."""
    
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
                request=None,
                response=self
            )


class StubMixcloudAPIService(MixcloudAPIService):
    """Stub API service for testing."""
    
    def __init__(self) -> None:
        """Initialize stub with fake HTTP client."""
        fake_client = FakeHTTPClient()
        super().__init__(http_client=fake_client)
        self.fake_client = fake_client
        
    def set_network_error(self, should_error: bool = True) -> None:
        """Configure stub to simulate network errors."""
        self.fake_client.should_raise_network_error = should_error
        
    def set_http_error(self, should_error: bool = True, status_code: int = 404) -> None:
        """Configure stub to simulate HTTP errors."""
        self.fake_client.should_raise_http_error = should_error
        self.fake_client.http_status_code = status_code
        
    @property 
    def request_count(self) -> int:
        """Get number of requests made."""
        return self.fake_client.request_count
        
    @property
    def last_url(self) -> str:
        """Get last requested URL."""
        return self.fake_client.last_url