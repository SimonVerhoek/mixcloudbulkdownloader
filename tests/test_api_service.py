"""Tests for MixcloudAPIService."""

import pytest

from app.data_classes import Cloudcast, MixcloudUser
from app.services.api_service import MixcloudAPIService
from tests.stubs.api_stubs import StubMixcloudAPIService


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
            ("https://other-site.com/user1/", ""),
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
                    "username": "testuser",
                    # Missing required fields like 'url' and 'pictures'
                },
                {"invalid": "data"},  # Completely invalid structure
            ]
        }

        users, error = service.search_users("test")

        # Should skip malformed entries and continue
        assert error == ""
        assert len(users) == 0  # Both entries are malformed

    def test_search_cloudcasts_success(self):
        """Test successful cloudcast search returns populated Cloudcast list."""
        service = StubMixcloudAPIService()
        cloudcasts, error = service.search_cloudcasts(phrase="test")

        assert error == ""
        assert len(cloudcasts) == 2
        assert all(isinstance(c, Cloudcast) for c in cloudcasts)
        assert cloudcasts[0].name == "Test Mix A"
        assert cloudcasts[0].user is not None
        assert cloudcasts[0].user.username == "djtest"
        assert cloudcasts[1].name == "Test Mix B"

    def test_search_cloudcasts_network_error(self):
        """Test cloudcast search returns empty list and error on network failure."""
        service = StubMixcloudAPIService()
        service.set_network_error(should_error=True)

        cloudcasts, error = service.search_cloudcasts(phrase="test")

        assert cloudcasts == []
        assert error != ""

    def test_search_cloudcasts_http_error(self):
        """Test cloudcast search returns empty list and HTTP status in error on HTTP failure."""
        service = StubMixcloudAPIService()
        service.set_http_error(should_error=True, status_code=500)

        cloudcasts, error = service.search_cloudcasts(phrase="test")

        assert cloudcasts == []
        assert "HTTP 500" in error

    def test_search_cloudcasts_url_has_correct_params(self):
        """Test cloudcast search URL contains type=cloudcast and limit=5."""
        service = StubMixcloudAPIService()
        service.search_cloudcasts(phrase="test")

        assert "type=cloudcast" in service.last_url
        assert "limit=5" in service.last_url

    def test_search_cloudcasts_malformed_data(self):
        """Test cloudcast search skips malformed entries and returns valid ones."""
        service = StubMixcloudAPIService()
        service.fake_client.responses["search_cloudcast_success"] = {
            "data": [
                {
                    "name": "Valid Mix",
                    "url": "https://www.mixcloud.com/djtest/valid-mix/",
                    "user": {
                        "key": "/djtest/",
                        "name": "DJ Test",
                        "pictures": {},
                        "url": "https://www.mixcloud.com/djtest/",
                        "username": "djtest",
                    },
                },
                {"invalid": "data"},  # Missing name, url, user
            ]
        }

        cloudcasts, error = service.search_cloudcasts(phrase="test")

        assert error == ""
        assert len(cloudcasts) == 1
        assert cloudcasts[0].name == "Valid Mix"

    def test_malformed_cloudcast_data_handling(self):
        """Test handling of malformed cloudcast data from API."""
        service = StubMixcloudAPIService()

        # Mock response with malformed data
        service.fake_client.responses["cloudcasts_page1"] = {
            "data": [
                {"name": "Valid Mix", "url": "https://www.mixcloud.com/testuser/valid-mix/"},
                {"invalid": "data"},  # Missing required fields
            ]
        }

        cloudcasts, error, next_page = service.get_user_cloudcasts("testuser")

        # Should skip malformed entries and continue
        assert error == ""
        assert len(cloudcasts) == 1
        assert cloudcasts[0].name == "Valid Mix"


class TestGetUser:
    """Test cases for MixcloudAPIService.get_user()."""

    def test_get_user_success(self):
        """Test successful single user fetch returns a populated MixcloudUser."""
        service = StubMixcloudAPIService()
        user, error = service.get_user(username="testuser")

        assert error == ""
        assert isinstance(user, MixcloudUser)
        assert user.username == "testuser"
        assert user.name == "Test User"
        assert user.key == "/testuser/"

    def test_get_user_network_error(self):
        """Test get_user returns (None, error_msg) on network failure."""
        service = StubMixcloudAPIService()
        service.set_network_error(should_error=True)

        user, error = service.get_user(username="testuser")

        assert user is None
        assert "Failed to query Mixcloud API" in error

    def test_get_user_http_error(self):
        """Test get_user returns (None, error_msg) with HTTP status on HTTP failure."""
        service = StubMixcloudAPIService()
        service.set_http_error(should_error=True, status_code=404)

        user, error = service.get_user(username="testuser")

        assert user is None
        assert "HTTP 404" in error


class TestGetCloudcast:
    """Test cases for MixcloudAPIService.get_cloudcast()."""

    def test_get_cloudcast_success(self):
        """Test successful single cloudcast fetch returns populated Cloudcast and nested user."""
        service = StubMixcloudAPIService()
        cloudcast, error = service.get_cloudcast(username="djtest", slug="test-mix-a")

        assert error == ""
        assert isinstance(cloudcast, Cloudcast)
        assert cloudcast.name == "Test Mix A"
        assert cloudcast.url == "https://www.mixcloud.com/djtest/test-mix-a/"
        assert isinstance(cloudcast.user, MixcloudUser)
        assert cloudcast.user.username == "djtest"
        assert cloudcast.user.name == "DJ Test"

    def test_get_cloudcast_network_error(self):
        """Test get_cloudcast returns (None, error_msg) on network failure."""
        service = StubMixcloudAPIService()
        service.set_network_error(should_error=True)

        cloudcast, error = service.get_cloudcast(username="djtest", slug="test-mix-a")

        assert cloudcast is None
        assert error != ""

    def test_get_cloudcast_http_error(self):
        """Test get_cloudcast returns (None, error_msg) with HTTP status on HTTP failure."""
        service = StubMixcloudAPIService()
        service.set_http_error(should_error=True, status_code=404)

        cloudcast, error = service.get_cloudcast(username="djtest", slug="test-mix-a")

        assert cloudcast is None
        assert "HTTP 404" in error
