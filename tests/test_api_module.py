"""Tests for app/api.py module functions."""

from unittest.mock import patch

import httpx
import pytest

from app import api
from app.consts.api import ERROR_API_REQUEST_FAILED, MIXCLOUD_API_URL


def make_mock_transport(responses: dict) -> httpx.MockTransport:
    """Create a mock transport that returns pre-defined responses based on URL patterns.

    Args:
        responses: Mapping of URL substring patterns to response configuration dicts.
            Each value may contain "status_code" (int), "json" (dict), or "text" (str).

    Returns:
        An httpx.MockTransport that handles matched URLs.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        for pattern, response_data in responses.items():
            if pattern in url_str:
                if "json" in response_data:
                    return httpx.Response(
                        status_code=response_data.get("status_code", 200),
                        json=response_data["json"],
                    )
                return httpx.Response(
                    status_code=response_data.get("status_code", 200),
                    text=response_data.get("text", ""),
                )
        return httpx.Response(status_code=404, text="Not found")

    return httpx.MockTransport(handler)


class TestAPIURLGeneration:
    """Test API URL generation functions."""

    def test_search_user_API_url(self):
        """Test user search URL generation."""
        phrase = "test user"
        expected_url = f"{MIXCLOUD_API_URL}/search/?q=test user&type=user"

        result = api.search_user_API_url(phrase)

        assert result == expected_url

    def test_search_user_API_url_with_special_characters(self):
        """Test user search URL with special characters."""
        phrase = "user@domain.com"
        expected_url = f"{MIXCLOUD_API_URL}/search/?q=user@domain.com&type=user"

        result = api.search_user_API_url(phrase)

        assert result == expected_url

    def test_search_user_API_url_empty_phrase(self):
        """Test user search URL with empty phrase."""
        phrase = ""
        expected_url = f"{MIXCLOUD_API_URL}/search/?q=&type=user"

        result = api.search_user_API_url(phrase)

        assert result == expected_url

    def test_user_cloudcasts_API_url(self):
        """Test user cloudcasts URL generation."""
        username = "testuser"
        expected_url = f"{MIXCLOUD_API_URL}/testuser/cloudcasts/"

        result = api.user_cloudcasts_API_url(username)

        assert result == expected_url

    def test_user_cloudcasts_API_url_with_special_characters(self):
        """Test cloudcasts URL with special username characters."""
        username = "user-name_123"
        expected_url = f"{MIXCLOUD_API_URL}/user-name_123/cloudcasts/"

        result = api.user_cloudcasts_API_url(username)

        assert result == expected_url


class TestMixcloudAPIData:
    """Test Mixcloud API data fetching."""

    def test_get_mixcloud_API_data_success(self):
        """Test successful API data retrieval."""
        expected_data = {"data": [{"name": "Test"}]}
        transport = make_mock_transport({"http://api.test.com": {"json": expected_data}})
        client = httpx.Client(transport=transport)

        data, error = api.get_mixcloud_API_data(url="http://api.test.com", client=client)

        assert data == expected_data
        assert error == ""

    def test_get_mixcloud_API_data_network_error(self):
        """Test API data retrieval with network error."""

        def raise_network_error(request: httpx.Request) -> httpx.Response:
            raise httpx.RequestError("Connection failed")

        transport = httpx.MockTransport(raise_network_error)
        client = httpx.Client(transport=transport)

        data, error = api.get_mixcloud_API_data(url="http://api.test.com", client=client)

        assert data is None
        assert error == ERROR_API_REQUEST_FAILED

    def test_get_mixcloud_API_data_api_error_response(self):
        """Test API data retrieval with API error in response."""
        error_response = {"error": {"type": "NotFound", "message": "User not found"}}
        transport = make_mock_transport({"http://api.test.com": {"json": error_response}})
        client = httpx.Client(transport=transport)

        data, error = api.get_mixcloud_API_data(url="http://api.test.com", client=client)

        assert data == error_response
        assert error == "NotFound: User not found"

    def test_get_mixcloud_API_data_http_status_error(self):
        """Test API data retrieval with HTTP status error."""

        def raise_http_error(request: httpx.Request) -> httpx.Response:
            raise httpx.HTTPStatusError(
                "404 Not Found",
                request=request,
                response=httpx.Response(status_code=404),
            )

        transport = httpx.MockTransport(raise_http_error)
        client = httpx.Client(transport=transport)

        data, error = api.get_mixcloud_API_data(url="http://api.test.com", client=client)

        assert data is None
        assert error == ERROR_API_REQUEST_FAILED

    def test_get_mixcloud_API_data_timeout_error(self):
        """Test API data retrieval with timeout error."""

        def raise_timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Request timed out")

        transport = httpx.MockTransport(raise_timeout)
        client = httpx.Client(transport=transport)

        data, error = api.get_mixcloud_API_data(url="http://api.test.com", client=client)

        assert data is None
        assert error == ERROR_API_REQUEST_FAILED

    def test_get_mixcloud_API_data_empty_response(self):
        """Test API data retrieval with empty response."""
        transport = make_mock_transport({"http://api.test.com": {"json": {}}})
        client = httpx.Client(transport=transport)

        data, error = api.get_mixcloud_API_data(url="http://api.test.com", client=client)

        assert data == {}
        assert error == ""

    def test_get_mixcloud_API_data_malformed_error_response(self):
        """Test API data retrieval with malformed error response."""
        error_response = {
            "error": {
                "type": "BadRequest"
                # Missing "message" field
            }
        }
        transport = make_mock_transport({"http://api.test.com": {"json": error_response}})
        client = httpx.Client(transport=transport)

        with pytest.raises(KeyError):
            api.get_mixcloud_API_data(url="http://api.test.com", client=client)


class TestAPIIntegration:
    """Test integration scenarios combining API functions."""

    def test_full_workflow_simulation(self):
        """Test a complete API workflow from search to user cloudcasts."""
        api_response = {
            "data": [{"key": "/testuser/", "username": "testuser", "cloudcasts": ["mix1", "mix2"]}]
        }
        transport = make_mock_transport({MIXCLOUD_API_URL: {"json": api_response}})
        client = httpx.Client(transport=transport)

        search_url = api.search_user_API_url("test")
        data, error = api.get_mixcloud_API_data(url=search_url, client=client)

        assert error == ""
        assert len(data["data"]) == 1

        user_url = api.user_cloudcasts_API_url("testuser")
        cloudcasts_data, cloudcasts_error = api.get_mixcloud_API_data(url=user_url, client=client)

        assert cloudcasts_error == ""

    def test_error_handling_consistency(self):
        """Test that error handling is consistent across functions."""
        assert api.search_user_API_url("") == f"{MIXCLOUD_API_URL}/search/?q=&type=user"
        assert api.user_cloudcasts_API_url("") == f"{MIXCLOUD_API_URL}//cloudcasts/"

        def raise_network_error(request: httpx.Request) -> httpx.Response:
            raise httpx.RequestError("Network error")

        transport = httpx.MockTransport(raise_network_error)
        client = httpx.Client(transport=transport)

        data, error = api.get_mixcloud_API_data(url="http://test.com", client=client)
        assert data is None
        assert error == ERROR_API_REQUEST_FAILED
