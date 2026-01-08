"""File service for file system operations with dependency injection."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager


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

        directory = dialog.getExistingDirectory(parent, title, str(Path.home()))

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
            path_obj = Path(path)
            if not path_obj.exists():
                return False

            if not path_obj.is_dir():
                return False

            # Check if directory is writable using pathlib method
            try:
                # Test write access by attempting to create a temporary file
                test_file = path_obj / ".write_test"
                test_file.touch()
                test_file.unlink()
                return True
            except (OSError, PermissionError):
                return False

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
            path_obj = Path(path)
            if path_obj.exists():
                return path_obj.is_dir()

            # Create directory and any necessary parent directories
            path_obj.mkdir(parents=True, exist_ok=True)
            return True

        except (OSError, TypeError):
            return False

    def get_user_home_directory(self) -> str:
        """Get the user's home directory path.

        Returns:
            User's home directory path
        """
        return str(Path.home())

    def join_paths(self, *paths: str) -> str:
        """Join multiple path components safely.

        Args:
            *paths: Path components to join

        Returns:
            Joined path string
        """
        if not paths:
            return ""
        path_obj = Path(paths[0])
        for part in paths[1:]:
            path_obj = path_obj / part
        return str(path_obj)

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
            path_obj = Path(path)
            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
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
            path_obj = Path(path)
            for item in path_obj.iterdir():
                if item.is_file():
                    if extension is None or item.name.lower().endswith(extension.lower()):
                        files.append(str(item))
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
            return Path(path).is_file()
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
                return Path(path).stat().st_size
        except (OSError, TypeError):
            pass
        return 0

    def get_pro_download_directory(
        self,
        license_manager: LicenseManager,
        settings_manager: SettingsManager,
        parent: QWidget = None,
    ) -> str | None:
        """Pro-aware directory selection with default directory support.

        Args:
            license_manager: License manager for Pro user detection
            settings_manager: Settings manager for default directory storage
            parent: Parent widget for dialogs

        Returns:
            Selected directory path, or None if cancelled
        """
        if license_manager.is_pro:
            # Check for saved default
            default_dir = settings_manager.default_download_directory
            if default_dir and Path(default_dir).exists():
                return default_dir

            # No default - prompt and offer to save
            chosen_dir = self.select_download_directory(parent, "Select Download Directory")
            if chosen_dir:
                self._prompt_save_as_default(chosen_dir, parent, settings_manager)
                return chosen_dir
            return None

        # Free users get basic picker
        directory = self.select_download_directory(parent, "Select Download Directory")
        return directory if directory else None

    def _prompt_save_as_default(
        self, directory: str, parent: QWidget, settings_manager: SettingsManager
    ) -> None:
        """Ask user if they want to save directory as default.

        Args:
            directory: Directory path to potentially save as default
            parent: Parent widget for dialog
            settings_manager: Settings manager for saving preference
        """
        reply = QMessageBox.question(
            parent,
            "Save as Default",
            f"Would you like to save this location as your default download folder?\n\n{directory}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            settings_manager.set("default_download_directory", directory)


# Create module-level singleton instance
file_service = FileService()
