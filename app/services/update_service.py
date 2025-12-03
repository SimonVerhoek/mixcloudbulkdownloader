"""Update service for GitHub release checking and version management."""

import sys
from typing import Any

from app.consts.settings import (
    DEFAULT_CHECK_UPDATES_ON_STARTUP,
    ERROR_NO_SUITABLE_DOWNLOAD,
    ERROR_UPDATE_CHECK_FAILED,
    GITHUB_API_BASE_URL,
    GITHUB_RELEASES_ENDPOINT,
    PLATFORM_FILE_EXTENSIONS,
    SETTING_CHECK_UPDATES_ON_STARTUP,
)
from app.data_classes import GitHubAsset, GitHubRelease
from app.interfaces.http_client import HTTPClientBase, RateLimitError
from app.qt_logger import log_error_with_traceback
from app.services.settings_manager import SettingsManager, settings
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

    def get_platform_asset(self, assets: list[GitHubAsset]) -> str:
        """Get platform-appropriate download asset URL.

        Args:
            assets: List of GitHub release assets

        Returns:
            Download URL for platform-specific asset, empty string if not found
        """
        # Simple platform detection (corrected for .zip on Windows)
        if sys.platform == "darwin":
            ext = ".dmg"
        elif sys.platform.startswith("win"):
            ext = ".zip"  # Windows gets .zip files, no .exe provided
        else:
            return ""  # unsupported platform

        for asset in assets:
            if asset.name.endswith(ext):
                return asset.browser_download_url
        return ""

    def is_release_suitable(self, release: GitHubRelease) -> bool:
        """Check if release is suitable for download (excludes pre-releases).

        Filters out pre-release versions including:
        - Alpha versions (alpha, a)
        - Beta versions (beta, b)
        - Release candidates (rc)
        - Development versions (dev)
        - Poetry pre-release patterns (premajor, preminor, prerelease)

        Args:
            release: GitHub release to check

        Returns:
            True if release is a stable version, False if it's a pre-release
        """
        return not is_prerelease_version(release.tag_name)

    def check_for_updates(self) -> tuple[GitHubRelease | None, str]:
        """Check for application updates.

        Returns:
            Tuple of (release, error_message). If successful, error_message is empty.
            Special case: Returns (None, "RATE_LIMITED") for GitHub rate limit errors.
        """
        try:
            release = self.get_latest_release()
            if not release:
                return None, ERROR_UPDATE_CHECK_FAILED

            # Filter out pre-release versions
            if not self.is_release_suitable(release):
                return None, ""  # No error, just no suitable release

            # Check if platform-specific asset is available
            download_url = self.get_platform_asset(release.assets)
            if not download_url:
                return None, ERROR_NO_SUITABLE_DOWNLOAD

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
