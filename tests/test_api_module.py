"""Tests for app/api.py module functions."""

import pytest
from unittest.mock import patch, MagicMock

import httpx

from app import api
from app.consts.api import MIXCLOUD_API_URL, ERROR_API_REQUEST_FAILED


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

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_success(self, mock_get):
        """Test successful API data retrieval."""
        expected_data = {"data": [{"name": "Test"}]}
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_get.return_value = mock_response
        
        data, error = api.get_mixcloud_API_data("http://api.test.com")
        
        assert data == expected_data
        assert error == ""
        mock_get.assert_called_once_with(url="http://api.test.com")

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_network_error(self, mock_get):
        """Test API data retrieval with network error."""
        mock_get.side_effect = httpx.RequestError("Connection failed")
        
        data, error = api.get_mixcloud_API_data("http://api.test.com")
        
        assert data is None
        assert error == ERROR_API_REQUEST_FAILED

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_api_error_response(self, mock_get):
        """Test API data retrieval with API error in response."""
        error_response = {
            "error": {
                "type": "NotFound",
                "message": "User not found"
            }
        }
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_get.return_value = mock_response
        
        data, error = api.get_mixcloud_API_data("http://api.test.com")
        
        assert data == error_response
        assert error == "NotFound: User not found"

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_invalid_json(self, mock_get):
        """Test API data retrieval with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError):
            api.get_mixcloud_API_data("http://api.test.com")

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_http_status_error(self, mock_get):
        """Test API data retrieval with HTTP status error."""
        mock_get.side_effect = httpx.HTTPStatusError(
            "404 Not Found", 
            request=MagicMock(), 
            response=MagicMock()
        )
        
        data, error = api.get_mixcloud_API_data("http://api.test.com")
        
        assert data is None
        assert error == ERROR_API_REQUEST_FAILED

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_timeout_error(self, mock_get):
        """Test API data retrieval with timeout error."""
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        
        data, error = api.get_mixcloud_API_data("http://api.test.com")
        
        assert data is None
        assert error == ERROR_API_REQUEST_FAILED

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_empty_response(self, mock_get):
        """Test API data retrieval with empty response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        data, error = api.get_mixcloud_API_data("http://api.test.com")
        
        assert data == {}
        assert error == ""

    @patch('app.api.httpx.get')
    def test_get_mixcloud_API_data_malformed_error_response(self, mock_get):
        """Test API data retrieval with malformed error response."""
        # Error response missing required fields
        error_response = {
            "error": {
                "type": "BadRequest"
                # Missing "message" field
            }
        }
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_get.return_value = mock_response
        
        # Should handle gracefully even with malformed error
        with pytest.raises(KeyError):
            api.get_mixcloud_API_data("http://api.test.com")


class TestAPIIntegration:
    """Test integration scenarios combining API functions."""

    @patch('app.api.httpx.get')
    def test_full_workflow_simulation(self, mock_get):
        """Test a complete API workflow from search to user cloudcasts."""
        # Mock successful API response
        api_response = {
            "data": [{
                "key": "/testuser/",
                "username": "testuser",
                "cloudcasts": ["mix1", "mix2"]
            }]
        }
        mock_response = MagicMock()
        mock_response.json.return_value = api_response
        mock_get.return_value = mock_response
        
        # Simulate API workflow
        search_url = api.search_user_API_url("test")
        data, error = api.get_mixcloud_API_data(search_url)
        
        assert error == ""
        assert len(data["data"]) == 1
        
        # Get user cloudcasts
        user_url = api.user_cloudcasts_API_url("testuser") 
        cloudcasts_data, cloudcasts_error = api.get_mixcloud_API_data(user_url)
        
        assert cloudcasts_error == ""

    def test_error_handling_consistency(self):
        """Test that error handling is consistent across functions."""
        # URL generation functions should never raise exceptions
        assert api.search_user_API_url("") == f"{MIXCLOUD_API_URL}/search/?q=&type=user"
        assert api.user_cloudcasts_API_url("") == f"{MIXCLOUD_API_URL}//cloudcasts/"
        
        # API function should return errors, not raise them (for network issues)
        with patch('app.api.httpx.get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Network error")
            
            data, error = api.get_mixcloud_API_data("http://test.com")
            assert data is None
            assert error == ERROR_API_REQUEST_FAILED