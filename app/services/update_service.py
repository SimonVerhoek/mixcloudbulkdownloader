"""Update service for GitHub release checking and version management."""

import sys
from typing import Any

from app.consts.settings import (
    AUTO_UPDATE_SHOW_PRERELEASE,
    DEFAULT_CHECK_UPDATES_ON_STARTUP,
    ERROR_NO_SUITABLE_DOWNLOAD,
    ERROR_UPDATE_CHECK_FAILED,
    GITHUB_API_BASE_URL,
    GITHUB_RELEASES_ALL_ENDPOINT,
    GITHUB_RELEASES_ENDPOINT,
    PLATFORM_FILE_EXTENSIONS,
    SETTING_CHECK_UPDATES_ON_STARTUP,
)
from app.data_classes import GitHubAsset, GitHubRelease
from app.interfaces.http_client import HTTPClientBase, RateLimitError
from app.qt_logger import log_error_with_traceback
from app.services.settings_manager import SettingsManager, settings
from app.utils.ffmpeg import _get_macos_architecture
from app.utils.version import is_prerelease_version


class UpdateService(HTTPClientBase):
    """Service for GitHub release checking with HTTPClientBase inheritance.

    Provides functionality to check for application updates from GitHub releases,
    handle platform-specific asset selection, and manage update preferences.
    """

    def __init__(self, settings_manager: SettingsManager = settings) -> None:
        """Initialize UpdateService with GitHub API base URL.

        Args:
            settings_manager: Settings manager for configuration access
        """
        super().__init__(base_url=GITHUB_API_BASE_URL)
        self.settings_manager = settings_manager

    def should_check_on_startup(self) -> bool:
        """Check if updates should be checked on startup.

        Returns:
            True if startup checking is enabled in settings
        """
        return self.settings_manager.get(
            SETTING_CHECK_UPDATES_ON_STARTUP, DEFAULT_CHECK_UPDATES_ON_STARTUP
        )

    def get_latest_release(self) -> GitHubRelease | None:
        """Get latest release from GitHub API with proper asset parsing.

        Returns:
            GitHubRelease object if successful, None if failed

        Raises:
            Exception: If API request fails or response is invalid
        """
        try:
            response_data = self._get(GITHUB_RELEASES_ENDPOINT)
            if not response_data:
                return None

            # Simple parsing as specified - error handling to be added later
            assets = [
                GitHubAsset(
                    name=asset_data["name"],
                    browser_download_url=asset_data["browser_download_url"],
                    size=asset_data["size"],
                    content_type=asset_data["content_type"],
                )
                for asset_data in response_data["assets"]
            ]

            return GitHubRelease(
                tag_name=response_data["tag_name"],
                name=response_data["name"],
                body=response_data["body"],
                assets=assets,
                published_at=response_data["published_at"],
            )
        except RateLimitError as e:
            # Rate limit error already logged by HTTPClientBase with header details
            # Re-raise with special marker for check_for_updates to catch
            raise ValueError("RATE_LIMITED") from e
        except Exception as e:
            log_error_with_traceback(f"Failed to get latest release: {e}")
            raise

    def get_latest_release_including_prereleases(self) -> GitHubRelease | None:
        """Get latest release including prereleases from GitHub API.

        Uses the /releases endpoint to fetch all releases and returns the first one
        (assuming GitHub's default sort returns the most recent first).

        Returns:
            GitHubRelease object if successful, None if failed

        Raises:
            Exception: If API request fails or response is invalid
        """
        try:
            response_data = self._get(GITHUB_RELEASES_ALL_ENDPOINT)
            if not response_data or len(response_data) == 0:
                return None

            # Get the first release from the list (assumed to be most recent)
            first_release = response_data[0]

            # Parse assets using same logic as get_latest_release()
            assets = [
                GitHubAsset(
                    name=asset_data["name"],
                    browser_download_url=asset_data["browser_download_url"],
                    size=asset_data["size"],
                    content_type=asset_data["content_type"],
                )
                for asset_data in first_release["assets"]
            ]

            return GitHubRelease(
                tag_name=first_release["tag_name"],
                name=first_release["name"],
                body=first_release["body"],
                assets=assets,
                published_at=first_release["published_at"],
            )
        except RateLimitError as e:
            # Rate limit error already logged by HTTPClientBase with header details
            # Re-raise with special marker for check_for_updates to catch
            raise ValueError("RATE_LIMITED") from e
        except Exception as e:
            log_error_with_traceback(f"Failed to get latest release (including prereleases): {e}")
            raise

    def get_platform_asset(self, assets: list[GitHubAsset]) -> str:
        """Get platform-appropriate download asset URL.

        Args:
            assets: List of GitHub release assets

        Returns:
            Download URL for platform-specific asset, empty string if not found
        """
        if sys.platform == "darwin":
            # Get macOS architecture and find architecture-specific DMG
            try:
                arch = _get_macos_architecture()
                for asset in assets:
                    if asset.name.endswith(".dmg") and arch in asset.name:
                        return asset.browser_download_url

                return ""  # No architecture-specific DMG found
            except RuntimeError:
                return ""  # Architecture detection failed
        elif sys.platform.startswith("win"):
            # Windows gets .zip files
            for asset in assets:
                if asset.name.endswith(".zip"):
                    return asset.browser_download_url
            return ""
        else:
            return ""  # unsupported platform

    def is_release_suitable(self, release: GitHubRelease) -> bool:
        """Check if release is suitable for download.

        By default, filters out pre-release versions including:
        - Alpha versions (alpha, a)
        - Beta versions (beta, b)
        - Release candidates (rc)
        - Development versions (dev)
        - Poetry pre-release patterns (premajor, preminor, prerelease)

        When AUTO_UPDATE_SHOW_PRERELEASE environment variable is True,
        all releases (including pre-releases) are considered suitable.

        Args:
            release: GitHub release to check

        Returns:
            True if release is suitable for download
        """
        if AUTO_UPDATE_SHOW_PRERELEASE:
            return True  # Accept all releases including pre-releases
        return not is_prerelease_version(release.tag_name)

    def check_for_updates(self) -> tuple[GitHubRelease | None, str]:
        """Check for application updates.

        Returns:
            Tuple of (release, error_message). If successful, error_message is empty.
            Special case: Returns (None, "RATE_LIMITED") for GitHub rate limit errors.
        """
        try:
            # Use different endpoint based on prerelease preference
            if AUTO_UPDATE_SHOW_PRERELEASE:
                release = self.get_latest_release_including_prereleases()
            else:
                release = self.get_latest_release()

            if not release:
                return None, ERROR_UPDATE_CHECK_FAILED

            # Filter out pre-release versions (only applies when AUTO_UPDATE_SHOW_PRERELEASE=False)
            if not self.is_release_suitable(release):
                return None, ""  # No error, just no suitable release

            return release, ""
        except Exception as e:
            # Check if this is a special rate limit marker from get_latest_release
            if str(e) == "RATE_LIMITED":
                return None, "RATE_LIMITED"

            error_msg = f"Update check failed: {e}"
            log_error_with_traceback(error_msg)
            return None, ERROR_UPDATE_CHECK_FAILED


# Create module-level singleton instance
update_service = UpdateService()
