"""Tests for MixcloudAPIService."""

import pytest

from app.services.api_service import MixcloudAPIService
from app.data_classes import MixcloudUser, Cloudcast
from tests.stubs import StubMixcloudAPIService


class TestMixcloudAPIService:
    """Test cases for MixcloudAPIService."""

    def test_init_with_default_client(self):
        """Test initialization with default HTTP client."""
        service = MixcloudAPIService()
        assert service.client is not None

    def test_search_users_success(self):
        """Test successful user search."""
        service = StubMixcloudAPIService()
        users, error = service.search_users("test")
        
        assert error == ""
        assert len(users) == 2
        assert isinstance(users[0], MixcloudUser)
        assert users[0].username == "testuser"
        assert users[0].name == "Test User"
        assert users[1].username == "anotheruser"
        assert service.request_count == 1

    def test_search_users_empty_phrase(self):
        """Test user search with empty search phrase.""" 
        service = StubMixcloudAPIService()
        users, error = service.search_users("")
        
        # Should still make request but return empty results
        assert error == ""
        assert len(users) == 0

    def test_search_users_api_error(self):
        """Test user search with API error response."""
        service = StubMixcloudAPIService()
        users, error = service.search_users("nonexistent")
        
        assert users == []
        assert "NotFound: User not found" in error

    def test_search_users_network_error(self):
        """Test user search with network error."""
        service = StubMixcloudAPIService()
        service.set_network_error(True)
        
        users, error = service.search_users("test")
        
        assert users == []
        assert "Failed to query Mixcloud API" in error

    def test_search_users_http_error(self):
        """Test user search with HTTP error."""
        service = StubMixcloudAPIService()
        service.set_http_error(True, 500)
        
        users, error = service.search_users("test")
        
        assert users == []
        assert "HTTP 500" in error

    def test_get_user_cloudcasts_success(self):
        """Test successful cloudcast retrieval."""
        service = StubMixcloudAPIService()
        cloudcasts, error, next_page = service.get_user_cloudcasts("testuser")
        
        assert error == ""
        assert len(cloudcasts) == 2
        assert isinstance(cloudcasts[0], Cloudcast)
        assert cloudcasts[0].name == "Test Mix 1"
        assert cloudcasts[1].name == "Test Mix 2"
        assert next_page == "https://api.mixcloud.com/testuser/cloudcasts/?offset=20"

    def test_get_user_cloudcasts_pagination(self):
        """Test cloudcast retrieval with pagination."""
        service = StubMixcloudAPIService()
        
        # First page
        cloudcasts1, error1, next_page = service.get_user_cloudcasts("testuser")
        assert error1 == ""
        assert len(cloudcasts1) == 2
        assert next_page != ""
        
        # Second page
        cloudcasts2, error2, next_page2 = service.get_next_cloudcasts_page(next_page)
        assert error2 == ""
        assert len(cloudcasts2) == 1
        assert cloudcasts2[0].name == "Test Mix 3"
        assert next_page2 == ""  # No more pages

    def test_get_user_cloudcasts_network_error(self):
        """Test cloudcast retrieval with network error."""
        service = StubMixcloudAPIService()
        service.set_network_error(True)
        
        cloudcasts, error, next_page = service.get_user_cloudcasts("testuser")
        
        assert cloudcasts == []
        assert "Failed to query Mixcloud API" in error
        assert next_page == ""

    def test_extract_username_from_url(self):
        """Test username extraction from API URL."""
        service = MixcloudAPIService()
        
        test_cases = [
            ("https://api.mixcloud.com/user1/cloudcasts/", "user1"),
            ("https://api.mixcloud.com/test-user/cloudcasts/?offset=20", "test-user"),
            ("invalid-url", ""),
            ("https://other-site.com/user1/", "")
        ]
        
        for url, expected in test_cases:
            result = service._extract_username_from_url(url)
            assert result == expected

    def test_close_client(self):
        """Test HTTP client closure."""
        service = StubMixcloudAPIService()
        
        # Should not raise an exception
        service.close()

    def test_malformed_user_data_handling(self):
        """Test handling of malformed user data from API."""
        service = StubMixcloudAPIService()
        
        # Mock response with malformed data
        service.fake_client.responses["search_user_success"] = {
            "data": [
                {
                    "key": "/testuser/",
                    "name": "Test User",
                    "username": "testuser"
                    # Missing required fields like 'url' and 'pictures'
                },
                {
                    "invalid": "data"  # Completely invalid structure
                }
            ]
        }
        
        users, error = service.search_users("test")
        
        # Should skip malformed entries and continue
        assert error == ""
        assert len(users) == 0  # Both entries are malformed

    def test_malformed_cloudcast_data_handling(self):
        """Test handling of malformed cloudcast data from API."""
        service = StubMixcloudAPIService()
        
        # Mock response with malformed data
        service.fake_client.responses["cloudcasts_page1"] = {
            "data": [
                {
                    "name": "Valid Mix",
                    "url": "https://www.mixcloud.com/testuser/valid-mix/"
                },
                {
                    "invalid": "data"  # Missing required fields
                }
            ]
        }
        
        cloudcasts, error, next_page = service.get_user_cloudcasts("testuser")
        
        # Should skip malformed entries and continue
        assert error == ""
        assert len(cloudcasts) == 1
        assert cloudcasts[0].name == "Valid Mix"