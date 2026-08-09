"""Sentry event scrubbing and consent gating for error reporting."""

import re
from collections.abc import Callable
from pathlib import Path

from app.services.settings_manager import SettingsManager, settings


_HOME = str(Path.home())
_HOME_POSIX = Path.home().as_posix()

# On Windows _HOME uses backslashes; build a pattern that matches both slash styles
# and applies case-insensitive matching (Windows FS is case-insensitive).
_HOME_PATTERN = re.compile(
    re.escape(_HOME).replace(r"\\", r"[/\\]"),
    flags=re.IGNORECASE if _HOME != _HOME_POSIX else 0,
)


def _build_home_pattern(home_dir: Path) -> re.Pattern:
    """Build a regex pattern that matches the given home directory path.

    Args:
        home_dir: The home directory path to match against.

    Returns:
        Compiled regex pattern that matches the home directory in both slash styles.
    """
    home_str = str(home_dir)
    home_posix = home_dir.as_posix()
    return re.compile(
        re.escape(home_str).replace(r"\\", r"[/\\]"),
        flags=re.IGNORECASE if home_str != home_posix else 0,
    )


def scrub_str(value: str) -> str:
    """Replace the home directory prefix with <username> in a string."""
    return _HOME_PATTERN.sub("<username>", value)


def scrub_obj(obj: object) -> object:
    """Recursively scrub home directory paths from a Sentry event object."""
    if isinstance(obj, str):
        return scrub_str(obj)
    if isinstance(obj, dict):
        return {k: scrub_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_obj(item) for item in obj]
    return obj


def _scrub_obj_with_pattern(obj: object, pattern: re.Pattern) -> object:
    """Recursively scrub home directory paths using the given pattern.

    Args:
        obj: The object to scrub (string, dict, list, or other).
        pattern: The compiled regex pattern to use for replacement.

    Returns:
        The scrubbed object with home directory paths replaced.
    """
    if isinstance(obj, str):
        return pattern.sub("<username>", obj)
    if isinstance(obj, dict):
        return {k: _scrub_obj_with_pattern(v, pattern) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_obj_with_pattern(item, pattern) for item in obj]
    return obj


def make_before_send(settings: SettingsManager, home_dir: Path = Path.home()) -> Callable:
    """Create a before_send hook with the given settings and home directory.

    Args:
        settings: The settings manager to read error_reporting_enabled from.
        home_dir: The home directory to scrub from events. Defaults to Path.home().

    Returns:
        A before_send callable suitable for use as a Sentry hook.
    """
    pattern = _build_home_pattern(home_dir)

    def before_send_fn(event: dict, hint: dict) -> dict | None:
        if not settings.error_reporting_enabled:
            return None
        return _scrub_obj_with_pattern(event, pattern)

    return before_send_fn


def before_breadcrumb(crumb: dict, hint: dict) -> dict:
    """Scrub home directory paths from breadcrumb messages (defence-in-depth)."""
    if msg := crumb.get("message"):
        crumb["message"] = scrub_str(msg)
    return crumb


def before_send(event: dict, hint: dict) -> dict | None:
    """Gate Sentry events on consent and scrub home directory paths.

    Dynamically reads the setting on every event so that toggling in Settings
    takes effect immediately without a restart. Strips the home directory from
    all strings in the event (breadcrumbs, stack frame locals, messages) before
    forwarding to Sentry.
    """
    if not settings.error_reporting_enabled:
        return None
    return scrub_obj(event)
