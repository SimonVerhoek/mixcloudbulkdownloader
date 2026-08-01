"""Tests for app.logger — the Qt-free logging module."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from app.logger import (
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    configure,
    get_log_directory,
    log_api,
    log_download,
    log_error,
    log_error_with_traceback,
    log_thread,
    log_ui,
)


# ---------------------------------------------------------------------------
# Format constants
# ---------------------------------------------------------------------------


class TestFormatConstants:
    """Verify LOG_FORMAT and LOG_DATE_FORMAT match expected patterns."""

    def test_log_format_contains_name(self):
        assert "%(name)s" in LOG_FORMAT

    def test_log_format_does_not_contain_func_name(self):
        assert "%(funcName)s" not in LOG_FORMAT

    def test_log_format_contains_lineno(self):
        assert "%(lineno)d" in LOG_FORMAT

    def test_log_format_contains_asctime(self):
        assert "%(asctime)s" in LOG_FORMAT

    def test_log_format_contains_levelname(self):
        assert "%(levelname)s" in LOG_FORMAT

    def test_log_format_contains_message(self):
        assert "%(message)s" in LOG_FORMAT

    def test_log_date_format(self):
        assert LOG_DATE_FORMAT == "%Y-%m-%dT%H:%M:%SZ"


# ---------------------------------------------------------------------------
# configure() behaviour
# ---------------------------------------------------------------------------


class TestConfigure:
    """Verify configure() sets up the root logger correctly."""

    def _remove_rotating_handlers(self) -> None:
        """Strip any RotatingFileHandlers from root logger before each test."""
        root = logging.getLogger()
        for handler in [h for h in root.handlers if isinstance(h, RotatingFileHandler)]:
            handler.close()
            root.removeHandler(handler)

    def test_attaches_rotating_file_handler(self, tmp_path: Path):
        self._remove_rotating_handlers()
        log_file = tmp_path / "test.log"
        configure(log_file=log_file)
        handlers = [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]
        assert len(handlers) == 1

    def test_idempotent_double_call(self, tmp_path: Path):
        self._remove_rotating_handlers()
        log_file = tmp_path / "test.log"
        configure(log_file=log_file)
        configure(log_file=log_file)
        handlers = [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]
        assert len(handlers) == 1

    def test_handler_max_bytes(self, tmp_path: Path):
        self._remove_rotating_handlers()
        log_file = tmp_path / "test.log"
        configure(log_file=log_file)
        handler = next(
            h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)
        )
        assert handler.maxBytes == 5 * 1024 * 1024

    def test_handler_backup_count(self, tmp_path: Path):
        self._remove_rotating_handlers()
        log_file = tmp_path / "test.log"
        configure(log_file=log_file)
        handler = next(
            h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)
        )
        assert handler.backupCount == 5

    def test_formatter_uses_log_format(self, tmp_path: Path):
        self._remove_rotating_handlers()
        log_file = tmp_path / "test.log"
        configure(log_file=log_file)
        handler = next(
            h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)
        )
        assert handler.formatter._fmt == LOG_FORMAT

    def test_formatter_uses_log_date_format(self, tmp_path: Path):
        self._remove_rotating_handlers()
        log_file = tmp_path / "test.log"
        configure(log_file=log_file)
        handler = next(
            h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)
        )
        assert handler.formatter.datefmt == LOG_DATE_FORMAT


# ---------------------------------------------------------------------------
# Named logger identity
# ---------------------------------------------------------------------------


class TestNamedLoggers:
    """Verify each convenience function routes to the correct named logger."""

    def test_log_ui_uses_app_ui(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.ui"):
            log_ui("hello ui")
        assert any(r.name == "app.ui" for r in caplog.records)

    def test_log_api_uses_app_api(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.api"):
            log_api("hello api")
        assert any(r.name == "app.api" for r in caplog.records)

    def test_log_download_uses_app_download(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.download"):
            log_download("hello download")
        assert any(r.name == "app.download" for r in caplog.records)

    def test_log_thread_uses_app_thread(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.thread"):
            log_thread("hello thread")
        assert any(r.name == "app.thread" for r in caplog.records)

    def test_log_error_uses_app_error(self, caplog):
        with caplog.at_level(logging.ERROR, logger="app.error"):
            log_error("hello error")
        assert any(r.name == "app.error" for r in caplog.records)

    def test_log_error_with_traceback_uses_app_error(self, caplog):
        with caplog.at_level(logging.ERROR, logger="app.error"):
            try:
                raise ValueError("boom")
            except ValueError:
                log_error_with_traceback("traceback error")
        assert any(r.name == "app.error" for r in caplog.records)


# ---------------------------------------------------------------------------
# Level mapping
# ---------------------------------------------------------------------------


class TestLevelMapping:
    """Verify that level strings produce the correct logging integer constants."""

    @pytest.mark.parametrize(
        "level_str,expected_int",
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ],
    )
    def test_level_string_maps_to_correct_int(self, level_str: str, expected_int: int, caplog):
        with caplog.at_level(logging.DEBUG, logger="app.ui"):
            log_ui(message="level check", level=level_str)
        record = next(r for r in caplog.records if r.name == "app.ui")
        assert record.levelno == expected_int


# ---------------------------------------------------------------------------
# get_log_directory()
# ---------------------------------------------------------------------------


class TestGetLogDirectory:
    """Verify get_log_directory() returns a valid, existing Path."""

    def test_returns_path_object(self):
        result = get_log_directory()
        assert isinstance(result, Path)

    def test_directory_exists_after_call(self):
        result = get_log_directory()
        assert result.exists()

    def test_is_a_directory(self):
        result = get_log_directory()
        assert result.is_dir()
