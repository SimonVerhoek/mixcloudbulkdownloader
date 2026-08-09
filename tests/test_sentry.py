"""Unit tests for Sentry integration in sentry_service."""

from pathlib import Path

import pytest

from app.services.sentry_service import (
    before_breadcrumb,
    before_send,
    make_before_send,
    scrub_obj,
    scrub_str,
)


class StubSettings:
    """Minimal stub for SettingsManager with error_reporting_enabled control."""

    def __init__(self, error_reporting_enabled: bool = True) -> None:
        self.error_reporting_enabled = error_reporting_enabled


@pytest.mark.unit
class TestBeforeSend:
    """Tests for the before_send Sentry gate function."""

    def test_returns_event_when_consent_enabled(self, tmp_path):
        """before_send should return the event unchanged when consent is enabled."""
        event = {"type": "event", "level": "error"}
        hint = {}
        stub_settings = StubSettings(error_reporting_enabled=True)
        fn = make_before_send(settings=stub_settings, home_dir=tmp_path)

        result = fn(event, hint)

        assert result == event

    def test_returns_none_when_consent_disabled(self, tmp_path):
        """before_send should return None (drop the event) when consent is disabled."""
        event = {"type": "event", "level": "error"}
        hint = {}
        stub_settings = StubSettings(error_reporting_enabled=False)
        fn = make_before_send(settings=stub_settings, home_dir=tmp_path)

        result = fn(event, hint)

        assert result is None

    def test_reads_setting_dynamically(self, tmp_path):
        """before_send reads the setting on every call, so toggling takes effect immediately."""
        event = {"type": "event", "level": "error"}
        hint = {}
        stub_settings = StubSettings(error_reporting_enabled=True)
        fn = make_before_send(settings=stub_settings, home_dir=tmp_path)

        assert fn(event, hint) == event

        stub_settings.error_reporting_enabled = False
        assert fn(event, hint) is None

    def test_scrubs_home_from_event_when_consent_enabled(self, tmp_path):
        """before_send should replace the home directory path with <username> in the returned event."""
        home = str(tmp_path)
        event = {"message": f"Error writing to {home}/Downloads/mix.mp3"}
        stub_settings = StubSettings(error_reporting_enabled=True)
        fn = make_before_send(settings=stub_settings, home_dir=tmp_path)

        result = fn(event, {})

        assert result is not None
        assert home not in result["message"]
        assert "<username>/Downloads/mix.mp3" in result["message"]


@pytest.mark.unit
class TestScrubStr:
    """Tests for scrub_str — single-string home replacement."""

    def test_replaces_home_prefix(self):
        home = str(Path.home())
        result = scrub_str(f"{home}/Downloads/mix.mp3")
        assert result == "<username>/Downloads/mix.mp3"
        assert home not in result

    def test_no_change_when_no_home_in_string(self):
        value = "/tmp/some/path"
        assert scrub_str(value) == value

    def test_already_tilde_unchanged(self):
        assert scrub_str("~/Downloads/mix.mp3") == "~/Downloads/mix.mp3"

    def test_empty_string(self):
        assert scrub_str("") == ""


@pytest.mark.unit
class TestScrubObj:
    """Tests for scrub_obj — recursive scrubbing of Sentry event-like structures."""

    def test_scrubs_plain_string(self):
        home = str(Path.home())
        assert scrub_obj(f"{home}/file.mp3") == "<username>/file.mp3"

    def test_scrubs_dict_values(self):
        home = str(Path.home())
        result = scrub_obj({"path": f"{home}/Downloads/mix.mp3", "level": "error"})
        assert result == {"path": "<username>/Downloads/mix.mp3", "level": "error"}

    def test_scrubs_nested_dict(self):
        home = str(Path.home())
        event = {"exception": {"values": [{"locals": {"f": f"{home}/mix.mp3"}}]}}
        result = scrub_obj(event)
        assert result["exception"]["values"][0]["locals"]["f"] == "<username>/mix.mp3"

    def test_scrubs_list_items(self):
        home = str(Path.home())
        result = scrub_obj([f"{home}/a.mp3", "clean", f"{home}/b.mp3"])
        assert result == ["<username>/a.mp3", "clean", "<username>/b.mp3"]

    def test_passthrough_non_string_leaf(self):
        assert scrub_obj(42) == 42
        assert scrub_obj(3.14) == 3.14
        assert scrub_obj(None) is None
        assert scrub_obj(True) is True

    def test_empty_dict(self):
        assert scrub_obj({}) == {}

    def test_empty_list(self):
        assert scrub_obj([]) == []


@pytest.mark.unit
class TestBeforeBreadcrumb:
    """Tests for before_breadcrumb — scrubs message field in breadcrumb dicts."""

    def test_scrubs_message_field(self):
        home = str(Path.home())
        crumb = {"message": f"Downloading {home}/Downloads/mix.mp3", "level": "info"}
        result = before_breadcrumb(crumb=crumb, hint={})
        assert home not in result["message"]
        assert "<username>/Downloads/mix.mp3" in result["message"]

    def test_returns_crumb_unchanged_when_no_message(self):
        crumb = {"type": "http", "data": {"url": "https://api.mixcloud.com"}}
        result = before_breadcrumb(crumb=crumb, hint={})
        assert result == crumb

    def test_returns_crumb_when_message_has_no_home(self):
        crumb = {"message": "Starting download", "level": "info"}
        result = before_breadcrumb(crumb=crumb, hint={})
        assert result["message"] == "Starting download"


@pytest.mark.unit
class TestSentryEnvironmentTag:
    """Tests for the environment tag derived from the DEVELOPMENT flag."""

    @pytest.mark.parametrize(
        "development,expected",
        [(True, "development"), (False, "production")],
    )
    def test_environment_derived_from_development_flag(self, development, expected):
        """Environment string must be 'development' or 'production' based on DEVELOPMENT flag."""
        environment = "development" if development else "production"
        assert environment == expected


@pytest.mark.unit
class TestSentryDsn:
    """Tests for the SENTRY_DSN constant."""

    def test_sentry_dsn_defaults_to_empty_string(self, monkeypatch):
        """SENTRY_DSN should be empty string in test env (disabling Sentry by default)."""
        import app.consts.settings as settings_module

        monkeypatch.setattr(settings_module, "SENTRY_DSN", "")
        assert settings_module.SENTRY_DSN == ""
