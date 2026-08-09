"""Unit tests for app.utils.platform_paths."""

from pathlib import Path

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

        def stub_getenv(key, default=None):
            return "C:/custom/appdata"

        assert get_appdata_dir(getenv_fn=stub_getenv) == Path("C:/custom/appdata")

    def test_fallback_when_not_set(self):
        """Falls back to ~/AppData/Roaming when APPDATA is not set."""

        def stub_getenv_fallback(key, default=None):
            return default

        assert (
            get_appdata_dir(getenv_fn=stub_getenv_fallback) == Path.home() / "AppData" / "Roaming"
        )


class TestGetXdgDataHome:
    """Tests for get_xdg_data_home()."""

    def test_uses_env_var(self):
        """Returns Path wrapping XDG_DATA_HOME when set."""

        def stub_getenv(key, default=None):
            return "/custom/data"

        assert get_xdg_data_home(getenv_fn=stub_getenv) == Path("/custom/data")

    def test_fallback_when_not_set(self):
        """Falls back to ~/.local/share when XDG_DATA_HOME is not set."""

        def stub_getenv_fallback(key, default=None):
            return default

        assert get_xdg_data_home(getenv_fn=stub_getenv_fallback) == Path.home() / ".local" / "share"


class TestGetXdgConfigHome:
    """Tests for get_xdg_config_home()."""

    def test_uses_env_var(self):
        """Returns Path wrapping XDG_CONFIG_HOME when set."""

        def stub_getenv(key, default=None):
            return "/custom/config"

        assert get_xdg_config_home(getenv_fn=stub_getenv) == Path("/custom/config")

    def test_fallback_when_not_set(self):
        """Falls back to ~/.config when XDG_CONFIG_HOME is not set."""

        def stub_getenv_fallback(key, default=None):
            return default

        assert get_xdg_config_home(getenv_fn=stub_getenv_fallback) == Path.home() / ".config"


class TestGetCurrentUser:
    """Tests for get_current_user()."""

    def test_uses_user_env_var(self):
        """Returns the USER env var value when set."""

        def stub_getenv_user(key, default=None):
            return "alice" if key == "USER" else default

        assert get_current_user(getenv_fn=stub_getenv_user) == "alice"

    def test_falls_back_to_username(self):
        """Falls back to USERNAME when USER is not set."""

        def stub_getenv_username(key, default=None):
            return "bob" if key == "USERNAME" else None

        assert get_current_user(getenv_fn=stub_getenv_username) == "bob"

    def test_fallback_to_default(self):
        """Returns 'default' when neither USER nor USERNAME is set."""

        def stub_getenv_none(key, default=None):
            return None

        assert get_current_user(getenv_fn=stub_getenv_none) == "default"
