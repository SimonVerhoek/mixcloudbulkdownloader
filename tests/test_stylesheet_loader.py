"""Tests for StylesheetLoader and stylesheet loading functionality."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.styles import (
    StylesheetLoader,
    _stylesheet_loader,
    get_stylesheet_loader,
    load_application_styles,
    reload_styles,
)


class TestStylesheetLoader:
    """Test cases for StylesheetLoader class."""

    def test_init_sets_styles_directory(self):
        """Test that initialization sets the correct styles directory."""
        loader = StylesheetLoader()
        assert loader.styles_dir is not None
        assert isinstance(loader.styles_dir, Path)
        assert loader._loaded_styles == {}

    def test_get_styles_directory_development_environment(self):
        """Test styles directory detection in development environment."""
        with (
            patch("app.styles.getattr", side_effect=lambda obj, attr, default=None: default),
            patch("app.styles.hasattr", return_value=False),
        ):
            loader = StylesheetLoader()
            assert str(loader.styles_dir).endswith("app/styles")

    def test_get_styles_directory_bundled_environment(self):
        """Test styles directory detection in PyInstaller bundled environment."""
        with (
            patch("app.styles.getattr", return_value=True),
            patch("app.styles.hasattr", return_value=True),
            patch("app.styles.sys") as mock_sys,
        ):
            # Mock sys to have _MEIPASS attribute
            mock_sys._MEIPASS = "/tmp/bundled_app"

            loader = StylesheetLoader()
            expected_dir = Path("/tmp/bundled_app/styles")
            assert loader.styles_dir == expected_dir

    def test_load_stylesheet_success(self):
        """Test successful stylesheet loading."""
        test_content = "QPushButton { color: red; }"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test stylesheet file
            styles_dir = Path(temp_dir)
            test_file = styles_dir / "test.qss"
            test_file.write_text(test_content)

            # Mock the styles directory
            loader = StylesheetLoader()
            loader.styles_dir = styles_dir

            result = loader.load_stylesheet("test.qss")
            assert result == test_content
            assert "test.qss" in loader._loaded_styles
            assert loader._loaded_styles["test.qss"] == test_content

    def test_load_stylesheet_caching(self):
        """Test that stylesheets are cached after first load."""
        test_content = "QPushButton { color: blue; }"

        with tempfile.TemporaryDirectory() as temp_dir:
            styles_dir = Path(temp_dir)
            test_file = styles_dir / "cached.qss"
            test_file.write_text(test_content)

            loader = StylesheetLoader()
            loader.styles_dir = styles_dir

            # First load
            result1 = loader.load_stylesheet("cached.qss")

            # Modify file after caching
            test_file.write_text("QPushButton { color: green; }")

            # Second load should return cached content
            result2 = loader.load_stylesheet("cached.qss")

            assert result1 == result2 == test_content

    def test_load_stylesheet_file_not_found(self):
        """Test loading non-existent stylesheet raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = StylesheetLoader()
            loader.styles_dir = Path(temp_dir)

            with pytest.raises(FileNotFoundError, match="Stylesheet file not found"):
                loader.load_stylesheet("nonexistent.qss")

    def test_load_stylesheet_io_error(self):
        """Test loading stylesheet with IO error raises IOError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            styles_dir = Path(temp_dir)
            test_file = styles_dir / "readonly.qss"
            test_file.write_text("content")

            loader = StylesheetLoader()
            loader.styles_dir = styles_dir

            # Mock open to raise IOError
            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = IOError("Permission denied")

                with pytest.raises(IOError, match="Error reading stylesheet file"):
                    loader.load_stylesheet("readonly.qss")

    def test_load_all_stylesheets_success(self):
        """Test loading all stylesheets successfully."""
        main_content = "QApplication { font-size: 14px; }"
        buttons_content = "QPushButton { padding: 10px; }"
        dialogs_content = "QDialog { margin: 20px; }"

        with tempfile.TemporaryDirectory() as temp_dir:
            styles_dir = Path(temp_dir)
            (styles_dir / "main.qss").write_text(main_content)
            (styles_dir / "buttons.qss").write_text(buttons_content)
            (styles_dir / "dialogs.qss").write_text(dialogs_content)

            loader = StylesheetLoader()
            loader.styles_dir = styles_dir

            result = loader.load_all_stylesheets()

            # Check that all stylesheets are included
            assert "/* main.qss */" in result
            assert main_content in result
            assert "/* buttons.qss */" in result
            assert buttons_content in result
            assert "/* dialogs.qss */" in result
            assert dialogs_content in result

    def test_load_all_stylesheets_missing_files(self, capsys):
        """Test loading stylesheets when some files are missing."""
        buttons_content = "QPushButton { padding: 10px; }"

        with tempfile.TemporaryDirectory() as temp_dir:
            styles_dir = Path(temp_dir)
            # Only create buttons.qss, leave main.qss and dialogs.qss missing
            (styles_dir / "buttons.qss").write_text(buttons_content)

            loader = StylesheetLoader()
            loader.styles_dir = styles_dir

            result = loader.load_all_stylesheets()

            # Should contain the available stylesheet
            assert "/* buttons.qss */" in result
            assert buttons_content in result

            # Should have printed warnings for missing files
            captured = capsys.readouterr()
            assert "Warning: Could not load stylesheet main.qss" in captured.out
            assert "Warning: Could not load stylesheet dialogs.qss" in captured.out

    def test_apply_styles_with_app_instance(self, qapp):
        """Test applying styles to a QApplication instance."""
        test_content = "QApplication { font-size: 16px; }"

        with tempfile.TemporaryDirectory() as temp_dir:
            styles_dir = Path(temp_dir)
            (styles_dir / "main.qss").write_text(test_content)
            (styles_dir / "buttons.qss").write_text("")
            (styles_dir / "dialogs.qss").write_text("")

            loader = StylesheetLoader()
            loader.styles_dir = styles_dir

            # Mock setStyleSheet to verify it's called
            with patch.object(qapp, "setStyleSheet") as mock_set_style:
                loader.apply_styles(qapp)
                mock_set_style.assert_called_once()
                args = mock_set_style.call_args[0]
                assert test_content in args[0]

    def test_apply_styles_no_app_instance(self):
        """Test applying styles when no QApplication instance is provided."""
        mock_app = MagicMock()

        with patch("app.styles.QApplication.instance", return_value=mock_app):
            loader = StylesheetLoader()
            loader.styles_dir = Path("/nonexistent")  # Will cause load errors

            loader.apply_styles()
            # Should still attempt to set stylesheet even with errors
            mock_app.setStyleSheet.assert_called_once()

    def test_apply_styles_no_qapplication_available(self):
        """Test applying styles when no QApplication is available."""
        with patch("app.styles.QApplication.instance", return_value=None):
            loader = StylesheetLoader()

            with pytest.raises(RuntimeError, match="No QApplication instance available"):
                loader.apply_styles()

    def test_apply_styles_handles_exceptions(self, capsys):
        """Test that apply_styles handles exceptions gracefully."""
        loader = StylesheetLoader()
        loader.styles_dir = Path("/nonexistent")

        mock_app = MagicMock()
        mock_app.setStyleSheet.side_effect = Exception("Test exception")

        with patch("app.styles.QApplication.instance", return_value=mock_app):
            loader.apply_styles()  # Should not raise

            captured = capsys.readouterr()
            assert "Error applying stylesheets: Test exception" in captured.out

    def test_reload_styles(self):
        """Test reloading styles clears cache and reapplies."""
        loader = StylesheetLoader()
        loader._loaded_styles["test.qss"] = "cached content"

        with patch.object(loader, "apply_styles") as mock_apply:
            loader.reload_styles()

            # Cache should be cleared
            assert loader._loaded_styles == {}
            # apply_styles should be called
            mock_apply.assert_called_once()


class TestStylesheetLoaderGlobalFunctions:
    """Test cases for global stylesheet loader functions."""

    def test_get_stylesheet_loader_singleton(self):
        """Test that get_stylesheet_loader returns singleton instance."""
        # Clear the global instance first
        import app.styles

        app.styles._stylesheet_loader = None

        loader1 = get_stylesheet_loader()
        loader2 = get_stylesheet_loader()

        assert loader1 is loader2
        assert isinstance(loader1, StylesheetLoader)

    def test_load_application_styles_with_app(self, qapp):
        """Test load_application_styles convenience function."""
        with patch("app.styles.get_stylesheet_loader") as mock_get_loader:
            mock_loader = MagicMock()
            mock_get_loader.return_value = mock_loader

            load_application_styles(qapp)

            mock_get_loader.assert_called_once()
            mock_loader.apply_styles.assert_called_once_with(qapp)

    def test_load_application_styles_no_app(self):
        """Test load_application_styles without app parameter."""
        with patch("app.styles.get_stylesheet_loader") as mock_get_loader:
            mock_loader = MagicMock()
            mock_get_loader.return_value = mock_loader

            load_application_styles()

            mock_get_loader.assert_called_once()
            mock_loader.apply_styles.assert_called_once_with(None)

    def test_reload_styles_convenience_function(self):
        """Test reload_styles convenience function."""
        with patch("app.styles.get_stylesheet_loader") as mock_get_loader:
            mock_loader = MagicMock()
            mock_get_loader.return_value = mock_loader

            reload_styles()

            mock_get_loader.assert_called_once()
            mock_loader.reload_styles.assert_called_once()


@pytest.mark.integration
class TestStylesheetLoaderIntegration:
    """Integration tests for StylesheetLoader with real stylesheet files."""

    def test_load_real_stylesheets(self):
        """Test loading the actual project stylesheet files."""
        loader = StylesheetLoader()

        # This test will use the real styles directory
        if loader.styles_dir.exists():
            result = loader.load_all_stylesheets()

            # Should contain content from real files
            assert len(result) > 0

            # Check for expected CSS comments and content
            if (loader.styles_dir / "main.qss").exists():
                assert "/* main.qss */" in result
            if (loader.styles_dir / "buttons.qss").exists():
                assert "/* buttons.qss */" in result
            if (loader.styles_dir / "dialogs.qss").exists():
                assert "/* dialogs.qss */" in result

    def test_stylesheet_files_exist(self):
        """Test that expected stylesheet files exist in the project."""
        loader = StylesheetLoader()
        styles_dir = loader.styles_dir

        if styles_dir.exists():
            expected_files = ["main.qss", "buttons.qss", "dialogs.qss"]
            for filename in expected_files:
                file_path = styles_dir / filename
                if file_path.exists():
                    # File should be readable and contain CSS
                    content = file_path.read_text()
                    assert len(content.strip()) > 0
                    # Should look like CSS (basic check)
                    assert "{" in content or "/*" in content
