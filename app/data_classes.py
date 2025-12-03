"""Data classes for Mixcloud API entities."""

from dataclasses import dataclass


@dataclass
class MixcloudUser:
    """Represents a Mixcloud user profile.

    Attributes:
        key: Unique identifier for the user
        name: Display name of the user
        pictures: Dictionary mapping picture sizes to URLs
        url: Full URL to the user's Mixcloud profile
        username: Username (handle) of the user
    """

    key: str
    name: str
    pictures: dict[str, str]
    url: str
    username: str


@dataclass
class Cloudcast:
    """Represents a Mixcloud cloudcast (mix/show).

    Attributes:
        name: Title of the cloudcast
        url: Full URL to the cloudcast
        user: The MixcloudUser who uploaded this cloudcast
    """

    name: str
    url: str
    user: MixcloudUser


@dataclass
class GitHubAsset:
    """Represents a GitHub release asset.

    Attributes:
        name: Asset filename (e.g., "app-2.2.0.dmg")
        browser_download_url: Direct download URL
        size: File size in bytes
        content_type: MIME type of the asset
    """

    name: str
    browser_download_url: str
    size: int
    content_type: str


@dataclass
class GitHubRelease:
    """Represents a GitHub release with download assets.

    Attributes:
        tag_name: Version tag (e.g., "2.2.0")
        name: Release title
        body: Release notes/changelog
        assets: List of downloadable assets
        published_at: Release publication date
    """

    tag_name: str
    name: str
    body: str
    assets: list[GitHubAsset]
    published_at: str
