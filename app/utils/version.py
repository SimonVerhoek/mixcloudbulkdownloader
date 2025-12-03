"""Version parsing and comparison utilities."""

import tomllib
from pathlib import Path

from packaging.version import parse as version_parse
from PySide6.QtCore import QCoreApplication

from app.consts.settings import DEVELOPMENT


def set_current_version() -> str:
    """Initialize application version in QCoreApplication."""

    if DEVELOPMENT:
        # Use existing pyproject.toml reading logic
        project_root = Path(__file__).parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            version = data["tool"]["poetry"]["version"]
    else:
        from app._version import __version__

        version = __version__

    QCoreApplication.setApplicationVersion(version)

    return version


def normalize_version_tag(tag: str) -> str:
    """Remove 'v' prefix from version tags.

    Args:
        tag: Version tag (e.g., "v2.1.0" or "2.1.0")

    Returns:
        Normalized version without 'v' prefix
    """
    return tag.lstrip("v")


def is_prerelease_version(tag: str) -> bool:
    """Check if version tag indicates a pre-release (alpha, beta, rc, dev, or Poetry pre-release).

    This function detects various pre-release patterns including:
    - Alpha versions: alpha, a
    - Beta versions: beta, b
    - Release candidates: rc, release-candidate
    - Development versions: dev, devel
    - Poetry pre-release patterns: premajor, preminor, prerelease
    - Semantic versioning pre-release identifiers (using packaging.version)

    Args:
        tag: Version tag to check (e.g., "v2.1.0-alpha.1", "1.0.0-beta", "premajor")

    Returns:
        True if tag indicates a pre-release version
    """
    # Normalize tag for consistent checking
    normalized_tag = normalize_version_tag(tag.lower().strip())

    # First, try using packaging.version for semantic versioning pre-release detection
    # This handles most cases correctly and avoids false positives
    try:
        parsed_version = version_parse(normalized_tag)
        if parsed_version.is_prerelease:
            return True
    except Exception:
        # If parsing fails, fall back to pattern matching
        pass

    # Check for Poetry pre-release patterns that aren't valid semantic versions
    poetry_patterns = ["premajor", "preminor", "prerelease"]
    for pattern in poetry_patterns:
        if pattern == normalized_tag:  # Exact match for Poetry patterns
            return True
        # Also check if Poetry pattern appears after version (e.g., "v2.0.0-premajor")
        if "-" in normalized_tag and normalized_tag.endswith("-" + pattern):
            return True

    # Check for explicit pre-release patterns in the pre-release part only
    # Split on dash to separate version from pre-release identifier
    if "-" in normalized_tag:
        version_part, prerelease_part = normalized_tag.split("-", 1)
        # Remove build metadata (everything after +)
        prerelease_part = prerelease_part.split("+")[0]

        prerelease_patterns = [
            "alpha",
            "a",  # Alpha releases
            "beta",
            "b",  # Beta releases
            "rc",
            "release-candidate",  # Release candidates
            "dev",
            "devel",  # Development releases
        ]

        # Check if pre-release part starts with any pattern
        for pattern in prerelease_patterns:
            if prerelease_part.startswith(pattern):
                return True

        # Handle numeric prefix patterns like "0.beta"
        if "." in prerelease_part:
            parts = prerelease_part.split(".")
            for part in parts:
                for pattern in prerelease_patterns:
                    if part == pattern or part.startswith(pattern):
                        return True

        # If we have a dash and couldn't parse it with packaging.version,
        # and it's not a known pattern, treat it as a pre-release for safety
        # This handles complex/invalid pre-release identifiers
        if prerelease_part.strip():  # Non-empty pre-release part means it's a pre-release
            return True

    return False


def compare_versions(current: str, latest: str) -> bool:
    """Compare semantic versions, return True if latest > current.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        True if latest version is newer than current version

    Raises:
        ValueError: If version strings are not valid semantic versions
    """
    # Normalize versions by removing 'v' prefix if present
    current_normalized = normalize_version_tag(current)
    latest_normalized = normalize_version_tag(latest)

    # Use packaging library for robust semantic version comparison
    return version_parse(latest_normalized) > version_parse(current_normalized)
