"""Platform-specific OS directory resolution.

These helpers centralise the idiomatic inline lookups for OS-standard path
environment variables (APPDATA, XDG_DATA_HOME, XDG_CONFIG_HOME) so that each
lookup is defined exactly once and reused throughout the codebase.

Per the CLAUDE.md exception clause these variables are OS-defined path vars,
not app config, so they are read via ``os.getenv`` rather than ``environs``.
"""

import os
from collections.abc import Callable
from pathlib import Path


def get_appdata_dir(getenv_fn: Callable[[str, str | None], str | None] | None = None) -> Path:
    """Return the Windows APPDATA base directory.

    Args:
        getenv_fn: Optional callable with the same signature as ``os.getenv``.
            Defaults to ``os.getenv``. Allows injection for testing without patching.

    Returns:
        Path to the APPDATA roaming directory, falling back to
        ``~/AppData/Roaming`` when the environment variable is not set.
    """
    _getenv = getenv_fn if getenv_fn is not None else os.getenv
    return Path(_getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))


def get_xdg_data_home(getenv_fn: Callable[[str, str | None], str | None] | None = None) -> Path:
    """Return the XDG_DATA_HOME directory.

    Args:
        getenv_fn: Optional callable with the same signature as ``os.getenv``.
            Defaults to ``os.getenv``. Allows injection for testing without patching.

    Returns:
        Path to the XDG data home directory, falling back to
        ``~/.local/share`` when the environment variable is not set.
    """
    _getenv = getenv_fn if getenv_fn is not None else os.getenv
    return Path(_getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))


def get_xdg_config_home(getenv_fn: Callable[[str, str | None], str | None] | None = None) -> Path:
    """Return the XDG_CONFIG_HOME directory.

    Args:
        getenv_fn: Optional callable with the same signature as ``os.getenv``.
            Defaults to ``os.getenv``. Allows injection for testing without patching.

    Returns:
        Path to the XDG config home directory, falling back to
        ``~/.config`` when the environment variable is not set.
    """
    _getenv = getenv_fn if getenv_fn is not None else os.getenv
    return Path(_getenv("XDG_CONFIG_HOME", str(Path.home() / ".config")))


def get_current_user(getenv_fn: Callable[[str, str | None], str | None] | None = None) -> str:
    """Return the current OS username.

    Tries the Unix ``USER`` variable first, then the Windows ``USERNAME``
    variable, falling back to ``"default"`` if neither is set.

    Args:
        getenv_fn: Optional callable with the same signature as ``os.getenv``.
            Defaults to ``os.getenv``. Allows injection for testing without patching.

    Returns:
        Current username string.
    """
    _getenv = getenv_fn if getenv_fn is not None else os.getenv
    return _getenv("USER", None) or _getenv("USERNAME", None) or "default"
