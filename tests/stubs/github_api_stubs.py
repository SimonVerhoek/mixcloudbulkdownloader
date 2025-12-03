"""GitHub API-related test stubs for update service testing."""

import sys
from typing import Any

from app.data_classes import GitHubAsset, GitHubRelease
from app.services.update_service import UpdateService


class FakeGitHubHTTPClient:
    """Fake HTTP client that returns predefined GitHub API responses."""

    def __init__(self) -> None:
        """Initialize fake GitHub client with response mapping."""
        self.responses: dict[str, dict[str, Any]] = {
            # Latest release response - update available scenario
            "release_update_available": {
                "tag_name": "v2.2.0",
                "name": "MBD 2.2.0 - Enhanced Downloads",
                "body": "## What's New\n- Improved download speed\n- Better error handling\n- Bug fixes",
                "published_at": "2024-12-01T10:00:00Z",
                "assets": [
                    {
                        "name": "MixcloudBulkDownloader-2.2.0.dmg",
                        "browser_download_url": "https://github.com/SimonVerhoek/mixcloudbulkdownloader/releases/download/v2.2.0/MixcloudBulkDownloader-2.2.0.dmg",
                        "size": 15678900,
                        "content_type": "application/octet-stream",
                    },
                    {
                        "name": "MixcloudBulkDownloader-2.2.0.zip",
                        "browser_download_url": "https://github.com/SimonVerhoek/mixcloudbulkdownloader/releases/download/v2.2.0/MixcloudBulkDownloader-2.2.0.zip",
                        "size": 12345678,
                        "content_type": "application/zip",
                    },
                ],
            },
            # Latest release response - no update available (same version)
            "release_no_update": {
                "tag_name": "v2.1.0",  # Assume current version
                "name": "MBD 2.1.0 - Current Release",
                "body": "## Current Release\n- This is the current version",
                "published_at": "2024-11-15T10:00:00Z",
                "assets": [
                    {
                        "name": "MixcloudBulkDownloader-2.1.0.dmg",
                        "browser_download_url": "https://github.com/SimonVerhoek/mixcloudbulkdownloader/releases/download/v2.1.0/MixcloudBulkDownloader-2.1.0.dmg",
                        "size": 15123456,
                        "content_type": "application/octet-stream",
                    },
                    {
                        "name": "MixcloudBulkDownloader-2.1.0.zip",
                        "browser_download_url": "https://github.com/SimonVerhoek/mixcloudbulkdownloader/releases/download/v2.1.0/MixcloudBulkDownloader-2.1.0.zip",
                        "size": 11987654,
                        "content_type": "application/zip",
                    },
                ],
            },
            # Beta release - should be filtered out
            "release_beta": {
                "tag_name": "v2.3.0-beta.1",
                "name": "MBD 2.3.0 Beta 1",
                "body": "## Beta Release\n- Testing new features",
                "published_at": "2024-12-10T10:00:00Z",
                "assets": [
                    {
                        "name": "MixcloudBulkDownloader-2.3.0-beta.1.dmg",
                        "browser_download_url": "https://github.com/SimonVerhoek/mixcloudbulkdownloader/releases/download/v2.3.0-beta.1/MixcloudBulkDownloader-2.3.0-beta.1.dmg",
                        "size": 16000000,
                        "content_type": "application/octet-stream",
                    }
                ],
            },
            # Release without platform-specific assets
            "release_no_platform_assets": {
                "tag_name": "v2.4.0",
                "name": "MBD 2.4.0 - Source Only",
                "body": "## Source Release\n- Source code only",
                "published_at": "2024-12-15T10:00:00Z",
                "assets": [
                    {
                        "name": "source-code.tar.gz",
                        "browser_download_url": "https://github.com/SimonVerhoek/mixcloudbulkdownloader/releases/download/v2.4.0/source-code.tar.gz",
                        "size": 987654,
                        "content_type": "application/gzip",
                    }
                ],
            },
        }

        # Control response behavior
        self.current_response = "release_update_available"
        self.should_raise_network_error = False
        self.should_raise_http_error = False
        self.should_raise_rate_limit = False
        self.request_count = 0

    def get(self, url: str, **kwargs) -> dict[str, Any]:
        """Mock GET request to GitHub API.

        Args:
            url: The URL being requested
            **kwargs: Additional request parameters

        Returns:
            Mocked response data

        Raises:
            Exception: If configured to simulate errors
        """
        self.request_count += 1

        if self.should_raise_network_error:
            raise ConnectionError("Simulated network error")

        if self.should_raise_rate_limit:
            from datetime import datetime, timezone

            import httpx

            # Create a mock response with rate limit headers
            class MockResponse:
                status_code = 403
                headers = {
                    "x-ratelimit-limit": "60",
                    "x-ratelimit-reset": str(
                        int((datetime.now(tz=timezone.utc).timestamp()) + 3600)
                    ),  # 1 hour from now
                    "x-ratelimit-remaining": "0",
                }

            mock_response = MockResponse()

            # Simulate GitHub rate limit error (403 with rate limit message)
            error = httpx.HTTPStatusError(
                "Client error '403 rate limit exceeded' for url 'https://api.github.com/repos/SimonVerhoek/mixcloudbulkdownloader/releases/latest'",
                request=None,
                response=mock_response,
            )
            raise error

        if self.should_raise_http_error:
            import httpx

            raise httpx.HTTPStatusError("404 Not Found", request=None, response=None)

        # Handle GitHub releases endpoint
        if "/repos/SimonVerhoek/mixcloudbulkdownloader/releases/latest" in url:
            return self.responses[self.current_response]

        # Unknown endpoint
        raise ValueError(f"Unknown GitHub API endpoint: {url}")

    def stream(self, method: str, url: str, **kwargs):
        """Mock streaming request for file downloads.

        Args:
            method: HTTP method
            url: The URL being requested
            **kwargs: Additional request parameters

        Returns:
            Mock response object with streaming capabilities
        """

        # This would be used for actual file downloads
        # For now, just return a basic mock
        class MockResponse:
            def __init__(self):
                self.headers = {"content-length": "1000000"}

            def raise_for_status(self):
                pass

            def iter_bytes(self, chunk_size=8192):
                # Return some fake chunks
                for i in range(10):
                    yield b"x" * min(chunk_size, 100000)

        return MockResponse()


class StubGitHubUpdateService(UpdateService):
    """Stub GitHub update service that uses fake HTTP client."""

    def __init__(self, fake_client: FakeGitHubHTTPClient = None, settings_manager=None):
        """Initialize stub update service.

        Args:
            fake_client: Fake HTTP client instance
            settings_manager: Mock settings manager
        """
        # Call parent init to get proper HTTPClientBase setup
        from app.consts.settings import GITHUB_API_BASE_URL
        from app.services.settings_manager import settings

        super().__init__(settings_manager or settings)

        # Create a custom httpx client that delegates to our fake client
        self.fake_client = fake_client or FakeGitHubHTTPClient()

        # Replace the httpx client with our custom one
        self._client = self._create_mock_httpx_client()

    def _create_mock_httpx_client(self):
        """Create a mock httpx client that delegates to our fake client."""

        class MockHttpxClient:
            def __init__(self, fake_client):
                self.fake_client = fake_client

            def request(self, method, url, **kwargs):
                # Create a mock response that behaves like httpx Response
                class MockHttpxResponse:
                    def __init__(self, data, fake_client):
                        self._data = data
                        self.fake_client = fake_client

                    def raise_for_status(self):
                        # Delegate to fake client to check for errors
                        try:
                            self.fake_client.get(url)  # This will raise if needed
                        except Exception as e:
                            import httpx

                            if isinstance(e, httpx.HTTPStatusError):
                                raise
                            # Convert to HTTPStatusError for other exceptions
                            raise httpx.HTTPStatusError(str(e), request=None, response=self) from e

                    def json(self):
                        return self._data

                # Get the actual data from fake client (but handle exceptions in raise_for_status)
                try:
                    data = self.fake_client.get(url)
                    return MockHttpxResponse(data, self.fake_client)
                except Exception:
                    # Return a response that will fail in raise_for_status
                    return MockHttpxResponse(None, self.fake_client)

            def stream(self, method, url, **kwargs):
                return self.fake_client.stream(method, url, **kwargs)

            def close(self):
                pass

        return MockHttpxClient(self.fake_client)


# Test scenarios helper
class GitHubAPITestScenarios:
    """Helper class to configure different test scenarios."""

    @staticmethod
    def configure_no_update_available(fake_client: FakeGitHubHTTPClient):
        """Configure scenario where no update is available."""
        fake_client.current_response = "release_no_update"
        fake_client.should_raise_network_error = False
        fake_client.should_raise_http_error = False

    @staticmethod
    def configure_update_available(fake_client: FakeGitHubHTTPClient):
        """Configure scenario where an update is available."""
        fake_client.current_response = "release_update_available"
        fake_client.should_raise_network_error = False
        fake_client.should_raise_http_error = False

    @staticmethod
    def configure_beta_release(fake_client: FakeGitHubHTTPClient):
        """Configure scenario with beta release (should be filtered out)."""
        fake_client.current_response = "release_beta"
        fake_client.should_raise_network_error = False
        fake_client.should_raise_http_error = False

    @staticmethod
    def configure_no_platform_assets(fake_client: FakeGitHubHTTPClient):
        """Configure scenario with no platform-specific assets."""
        fake_client.current_response = "release_no_platform_assets"
        fake_client.should_raise_network_error = False
        fake_client.should_raise_http_error = False

    @staticmethod
    def configure_network_error(fake_client: FakeGitHubHTTPClient):
        """Configure scenario with network error."""
        fake_client.should_raise_network_error = True
        fake_client.should_raise_http_error = False

    @staticmethod
    def configure_http_error(fake_client: FakeGitHubHTTPClient):
        """Configure scenario with HTTP error."""
        fake_client.should_raise_network_error = False
        fake_client.should_raise_http_error = True

    @staticmethod
    def configure_rate_limit_error(fake_client: FakeGitHubHTTPClient):
        """Configure scenario with GitHub rate limit error."""
        fake_client.should_raise_network_error = False
        fake_client.should_raise_http_error = False
        fake_client.should_raise_rate_limit = True
