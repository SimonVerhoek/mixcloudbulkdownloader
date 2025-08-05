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
