"""File service for file system operations with dependency injection."""

import os
from os.path import expanduser

from PySide6.QtWidgets import QFileDialog, QWidget


class FileService:
    """Service for file system operations that can be easily mocked for testing."""

    def __init__(self) -> None:
        """Initialize file service."""
        pass

    def select_download_directory(
        self, parent: QWidget | None = None, title: str = "Select download location"
    ) -> str:
        """Show directory selection dialog.

        Args:
            parent: Parent widget for the dialog
            title: Dialog title text

        Returns:
            Selected directory path, or empty string if cancelled
        """
        dialog = QFileDialog()
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setOption(QFileDialog.DontResolveSymlinks)

        directory = dialog.getExistingDirectory(parent, title, expanduser("~"))

        return directory if directory else ""

    def validate_directory(self, path: str) -> bool:
        """Validate that a directory path exists and is writable.

        Args:
            path: Directory path to validate

        Returns:
            True if directory is valid and writable
        """
        if not path:
            return False

        try:
            # Check if path exists and is a directory
            if not os.path.exists(path):
                return False

            if not os.path.isdir(path):
                return False

            # Check if directory is writable
            return os.access(path, os.W_OK)

        except (OSError, TypeError):
            return False

    def ensure_directory_exists(self, path: str) -> bool:
        """Ensure directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure exists

        Returns:
            True if directory exists or was created successfully
        """
        if not path:
            return False

        try:
            if os.path.exists(path):
                return os.path.isdir(path)

            # Create directory and any necessary parent directories
            os.makedirs(path, exist_ok=True)
            return True

        except (OSError, TypeError):
            return False

    def get_user_home_directory(self) -> str:
        """Get the user's home directory path.

        Returns:
            User's home directory path
        """
        return expanduser("~")

    def join_paths(self, *paths: str) -> str:
        """Join multiple path components safely.

        Args:
            *paths: Path components to join

        Returns:
            Joined path string
        """
        return os.path.join(*paths)

    def get_directory_size(self, path: str) -> int:
        """Get the total size of all files in a directory.

        Args:
            path: Directory path

        Returns:
            Total size in bytes, or 0 if directory doesn't exist
        """
        if not self.validate_directory(path):
            return 0

        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, TypeError):
            pass

        return total_size

    def list_files_in_directory(self, path: str, extension: str | None = None) -> list[str]:
        """List files in a directory, optionally filtered by extension.

        Args:
            path: Directory path to list
            extension: Optional file extension filter (e.g., ".mp3")

        Returns:
            List of file paths
        """
        if not self.validate_directory(path):
            return []

        try:
            files = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path):
                    if extension is None or item.lower().endswith(extension.lower()):
                        files.append(item_path)
            return sorted(files)
        except (OSError, TypeError):
            return []

    def file_exists(self, path: str) -> bool:
        """Check if a file exists.

        Args:
            path: File path to check

        Returns:
            True if file exists
        """
        try:
            return os.path.isfile(path)
        except TypeError:
            return False

    def get_file_size(self, path: str) -> int:
        """Get the size of a file.

        Args:
            path: File path

        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        try:
            if self.file_exists(path):
                return os.path.getsize(path)
        except (OSError, TypeError):
            pass
        return 0
