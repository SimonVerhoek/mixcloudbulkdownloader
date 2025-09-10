"""API service for Mixcloud operations with dependency injection."""

import httpx

from app.consts import ERROR_API_REQUEST_FAILED, MIXCLOUD_API_URL
from app.data_classes import Cloudcast, MixcloudUser


class MixcloudAPIService:
    """Service for Mixcloud API operations with injectable HTTP client for testing."""

    def __init__(self, http_client: httpx.Client = httpx.Client()) -> None:
        """Initialize API service with optional HTTP client injection.

        Args:
            http_client: HTTP client for making requests. If None, creates default client.
        """
        self.client = http_client

    def search_users(self, phrase: str) -> tuple[list[MixcloudUser], str]:
        """Search for Mixcloud users by phrase.

        Args:
            phrase: Search term to look for users

        Returns:
            Tuple of (users_list, error_message). If successful, error_message is empty.
        """
        url = f"{MIXCLOUD_API_URL}/search/?q={phrase}&type=user"
        response_data, error = self._make_api_request(url)

        if error:
            return [], error

        users = []
        if response_data and "data" in response_data:
            for user_data in response_data["data"]:
                try:
                    user = MixcloudUser(**user_data)
                    users.append(user)
                except (TypeError, KeyError) as e:
                    # Skip malformed user data
                    continue

        return users, ""

    def get_user_cloudcasts(self, username: str, url: str = "") -> tuple[list[Cloudcast], str, str]:
        """Get cloudcasts for a specific user.

        Args:
            username: Mixcloud username
            url: Optional API URL for pagination (if empty, generates from username)

        Returns:
            Tuple of (cloudcasts_list, error_message, next_page_url).
            next_page_url is empty if no more pages.
        """
        if not url:
            url = f"{MIXCLOUD_API_URL}/{username}/cloudcasts/"

        response_data, error = self._make_api_request(url)

        if error:
            return [], error, ""

        cloudcasts = []
        next_page = ""

        if response_data and "data" in response_data:
            # Create a user object for the cloudcasts
            user = MixcloudUser(
                key=f"/{username}/",
                name=username,  # We'll use username as display name for now
                pictures={},
                url=f"https://www.mixcloud.com/{username}/",
                username=username,
            )

            for cloudcast_data in response_data["data"]:
                try:
                    cloudcast = Cloudcast(
                        name=cloudcast_data["name"], url=cloudcast_data["url"], user=user
                    )
                    cloudcasts.append(cloudcast)
                except (TypeError, KeyError):
                    # Skip malformed cloudcast data
                    continue

            # Check for next page
            if response_data.get("paging") and response_data["paging"].get("next"):
                next_page = response_data["paging"]["next"]

        return cloudcasts, "", next_page

    def get_next_cloudcasts_page(self, next_url: str) -> tuple[list[Cloudcast], str, str]:
        """Get the next page of cloudcasts from pagination URL.

        Args:
            next_url: Full URL for the next page

        Returns:
            Tuple of (cloudcasts_list, error_message, next_page_url).
            next_page_url is empty if no more pages.
        """
        response_data, error = self._make_api_request(next_url)

        if error:
            return [], error, ""

        cloudcasts = []
        next_page = ""

        if response_data:
            if "data" in response_data:
                # Extract username from the URL for user object
                username = self._extract_username_from_url(next_url)
                user = MixcloudUser(
                    key=f"/{username}/",
                    name=username,
                    pictures={},
                    url=f"https://www.mixcloud.com/{username}/",
                    username=username,
                )

                for cloudcast_data in response_data["data"]:
                    try:
                        cloudcast = Cloudcast(
                            name=cloudcast_data["name"], url=cloudcast_data["url"], user=user
                        )
                        cloudcasts.append(cloudcast)
                    except (TypeError, KeyError):
                        continue

            # Check for next page
            if response_data.get("paging") and response_data["paging"].get("next"):
                next_page = response_data["paging"]["next"]

        return cloudcasts, "", next_page

    def _make_api_request(self, url: str) -> tuple[dict | None, str]:
        """Make HTTP request to Mixcloud API.

        Args:
            url: API endpoint URL

        Returns:
            Tuple of (response_data, error_message). If successful, error_message is empty.
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            # Check for API-level errors in response
            if isinstance(data, dict) and "error" in data:
                error_type = data["error"].get("type", "Unknown")
                error_msg = data["error"].get("message", "Unknown error")
                return None, f"{error_type}: {error_msg}"

            return data, ""

        except httpx.RequestError:
            return None, ERROR_API_REQUEST_FAILED
        except httpx.HTTPStatusError as e:
            return None, f"HTTP {e.response.status_code}: {ERROR_API_REQUEST_FAILED}"
        except (ValueError, KeyError):
            return None, "Invalid response format from API"

    def _extract_username_from_url(self, url: str) -> str:
        """Extract username from a Mixcloud API URL.

        Args:
            url: API URL containing username

        Returns:
            Extracted username or empty string if not found
        """
        try:
            # URL format: https://api.mixcloud.com/username/cloudcasts/...
            parts = url.split("/")
            api_index = next((i for i, part in enumerate(parts) if "api.mixcloud.com" in part), -1)
            if api_index != -1 and api_index + 1 < len(parts):
                return parts[api_index + 1]
        except (ValueError, IndexError):
            pass
        return ""

    def close(self) -> None:
        """Close the HTTP client connection."""
        if hasattr(self.client, "close"):
            self.client.close()


# Create module-level singleton instance
api_service = MixcloudAPIService()
