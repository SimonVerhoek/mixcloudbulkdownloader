"""Platform-specific OS directory resolution.

These helpers centralise the idiomatic inline lookups for OS-standard path
environment variables (APPDATA, XDG_DATA_HOME, XDG_CONFIG_HOME) so that each
lookup is defined exactly once and reused throughout the codebase.

Per the CLAUDE.md exception clause these variables are OS-defined path vars,
not app config, so they are read via ``os.getenv`` rather than ``environs``.
"""

import os
from pathlib import Path


def get_appdata_dir() -> Path:
    """Return the Windows APPDATA base directory.

    Returns:
        Path to the APPDATA roaming directory, falling back to
        ``~/AppData/Roaming`` when the environment variable is not set.
    """
    return Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))


def get_xdg_data_home() -> Path:
    """Return the XDG_DATA_HOME directory.

    Returns:
        Path to the XDG data home directory, falling back to
        ``~/.local/share`` when the environment variable is not set.
    """
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))


def get_xdg_config_home() -> Path:
    """Return the XDG_CONFIG_HOME directory.

    Returns:
        Path to the XDG config home directory, falling back to
        ``~/.config`` when the environment variable is not set.
    """
    return Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config")))


def get_current_user() -> str:
    """Return the current OS username.

    Tries the Unix ``USER`` variable first, then the Windows ``USERNAME``
    variable, falling back to ``"default"`` if neither is set.

    Returns:
        Current username string.
    """
    return os.getenv("USER") or os.getenv("USERNAME") or "default"
