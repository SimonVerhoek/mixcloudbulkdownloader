"""Unit tests for app.utils.platform_paths."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils.platform_paths import (
    get_appdata_dir,
    get_current_user,
    get_xdg_config_home,
    get_xdg_data_home,
)


class TestGetAppdataDir:
    """Tests for get_appdata_dir()."""

    def test_uses_env_var(self):
        """Returns Path wrapping the APPDATA env var when set."""
        with patch("app.utils.platform_paths.os.getenv", return_value="C:/custom/appdata"):
            assert get_appdata_dir() == Path("C:/custom/appdata")

    def test_fallback_when_not_set(self):
        """Falls back to ~/AppData/Roaming when APPDATA is not set."""
        with patch(
            "app.utils.platform_paths.os.getenv", side_effect=lambda key, default=None: default
        ):
            assert get_appdata_dir() == Path.home() / "AppData" / "Roaming"


class TestGetXdgDataHome:
    """Tests for get_xdg_data_home()."""

    def test_uses_env_var(self):
        """Returns Path wrapping XDG_DATA_HOME when set."""
        with patch("app.utils.platform_paths.os.getenv", return_value="/custom/data"):
            assert get_xdg_data_home() == Path("/custom/data")

    def test_fallback_when_not_set(self):
        """Falls back to ~/.local/share when XDG_DATA_HOME is not set."""
        with patch(
            "app.utils.platform_paths.os.getenv", side_effect=lambda key, default=None: default
        ):
            assert get_xdg_data_home() == Path.home() / ".local" / "share"


class TestGetXdgConfigHome:
    """Tests for get_xdg_config_home()."""

    def test_uses_env_var(self):
        """Returns Path wrapping XDG_CONFIG_HOME when set."""
        with patch("app.utils.platform_paths.os.getenv", return_value="/custom/config"):
            assert get_xdg_config_home() == Path("/custom/config")

    def test_fallback_when_not_set(self):
        """Falls back to ~/.config when XDG_CONFIG_HOME is not set."""
        with patch(
            "app.utils.platform_paths.os.getenv", side_effect=lambda key, default=None: default
        ):
            assert get_xdg_config_home() == Path.home() / ".config"


class TestGetCurrentUser:
    """Tests for get_current_user()."""

    def test_uses_user_env_var(self):
        """Returns the USER env var value when set."""
        with patch(
            "app.utils.platform_paths.os.getenv",
            side_effect=lambda k, d=None: "alice" if k == "USER" else d,
        ):
            assert get_current_user() == "alice"

    def test_falls_back_to_username(self):
        """Falls back to USERNAME when USER is not set."""
        with patch(
            "app.utils.platform_paths.os.getenv",
            side_effect=lambda k, d=None: "bob" if k == "USERNAME" else None,
        ):
            assert get_current_user() == "bob"

    def test_fallback_to_default(self):
        """Returns 'default' when neither USER nor USERNAME is set."""
        with patch("app.utils.platform_paths.os.getenv", return_value=None):
            assert get_current_user() == "default"
