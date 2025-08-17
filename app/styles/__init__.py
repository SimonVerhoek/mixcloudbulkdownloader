"""Stylesheet loading system for Mixcloud Bulk Downloader."""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication


class StylesheetLoader:
    """Handles loading and applying QSS stylesheets to the application."""

    def __init__(self) -> None:
        """Initialize the stylesheet loader."""
        self.styles_dir = self._get_styles_directory()
        self._loaded_styles: dict[str, str] = {}

    def _get_styles_directory(self) -> Path:
        """Get the styles directory, handling both development and bundled environments.

        Returns:
            Path to the styles directory
        """
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            # PyInstaller bundled environment
            # Files are in sys._MEIPASS/styles/
            return Path(sys._MEIPASS) / "styles"
        else:
            # Development environment
            return Path(__file__).parent

    def load_stylesheet(self, filename: str) -> str:
        """Load a QSS stylesheet file.

        Args:
            filename: Name of the QSS file to load

        Returns:
            Content of the stylesheet file

        Raises:
            FileNotFoundError: If the stylesheet file doesn't exist
            IOError: If there's an error reading the file
        """
        if filename in self._loaded_styles:
            return self._loaded_styles[filename]

        filepath = self.styles_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Stylesheet file not found: {filepath}")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self._loaded_styles[filename] = content
            return content
        except IOError as e:
            raise IOError(f"Error reading stylesheet file {filepath}: {e}") from e

    def load_all_stylesheets(self) -> str:
        """Load and combine all QSS stylesheets.

        Returns:
            Combined stylesheet content
        """
        stylesheet_files = ["main.qss", "buttons.qss", "dialogs.qss"]
        combined_styles = []

        for filename in stylesheet_files:
            try:
                content = self.load_stylesheet(filename)
                combined_styles.append(f"/* {filename} */")
                combined_styles.append(content)
                combined_styles.append("")  # Add spacing between files
            except (FileNotFoundError, IOError) as e:
                # Use print() instead of logging to ensure visibility in bundled environments
                # where the Qt logging system may not be fully initialized yet
                print(f"Warning: Could not load stylesheet {filename}: {e}")

        return "\n".join(combined_styles)

    def apply_styles(self, app: Optional[QApplication] = None) -> None:
        """Apply all stylesheets to the application.

        Args:
            app: QApplication instance. If None, uses QApplication.instance()
        """
        if app is None:
            app = QApplication.instance()

        if app is None:
            raise RuntimeError("No QApplication instance available")

        try:
            combined_styles = self.load_all_stylesheets()
            app.setStyleSheet(combined_styles)
        except Exception as e:
            print(f"Error applying stylesheets: {e}")

    def reload_styles(self) -> None:
        """Clear cached styles and reload them.

        Useful for development when styles are being modified.
        """
        self._loaded_styles.clear()
        self.apply_styles()


# Global stylesheet loader instance
_stylesheet_loader: Optional[StylesheetLoader] = None


def get_stylesheet_loader() -> StylesheetLoader:
    """Get the global stylesheet loader instance."""
    global _stylesheet_loader
    if _stylesheet_loader is None:
        _stylesheet_loader = StylesheetLoader()
    return _stylesheet_loader


def load_application_styles(app: Optional[QApplication] = None) -> None:
    """Convenience function to load and apply all application styles.

    Args:
        app: QApplication instance. If None, uses QApplication.instance()
    """
    loader = get_stylesheet_loader()
    loader.apply_styles(app)


def reload_styles() -> None:
    """Convenience function to reload all styles.

    Useful for development when styles are being modified.
    """
    loader = get_stylesheet_loader()
    loader.reload_styles()
