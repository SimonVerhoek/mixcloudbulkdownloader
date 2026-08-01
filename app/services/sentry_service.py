"""Sentry event scrubbing and consent gating for error reporting."""

import re
from pathlib import Path

from app.services.settings_manager import settings


_HOME = str(Path.home())
_HOME_POSIX = Path.home().as_posix()

# On Windows _HOME uses backslashes; build a pattern that matches both slash styles
# and applies case-insensitive matching (Windows FS is case-insensitive).
_HOME_PATTERN = re.compile(
    re.escape(_HOME).replace(r"\\", r"[/\\]"),
    flags=re.IGNORECASE if _HOME != _HOME_POSIX else 0,
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
