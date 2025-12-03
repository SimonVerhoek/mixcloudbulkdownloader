"""File service test stubs."""

from app.services.file_service import FileService


class StubFileService(FileService):
    """Stub file service for testing."""

    def __init__(self) -> None:
        """Initialize stub file service."""
        super().__init__()
        self.selected_directory = "/fake/download/path"
        self.should_cancel_dialog = False
        self.existing_directories: set[str] = {"/fake/download/path", "/home/user"}
        self.writable_directories: set[str] = {"/fake/download/path", "/home/user"}
        self.file_sizes: dict[str, int] = {}
        self.directory_files: dict[str, list[str]] = {}

    def select_download_directory(self, parent=None, title: str = "Select directory") -> str:
        """Simulate directory selection dialog.

        Args:
            parent: Parent widget (ignored in stub)
            title: Dialog title (ignored in stub)

        Returns:
            Selected directory path or empty string if cancelled
        """
        return "" if self.should_cancel_dialog else self.selected_directory

    def validate_directory(self, path: str) -> bool:
        """Simulate directory validation.

        Args:
            path: Directory path to validate

        Returns:
            True if directory is valid and writable
        """
        if not path:
            return False
        return path in self.existing_directories and path in self.writable_directories

    def ensure_directory_exists(self, path: str) -> bool:
        """Simulate directory creation.

        Args:
            path: Directory path to create

        Returns:
            True if directory exists or was created
        """
        if not path:
            return False
        self.existing_directories.add(path)
        self.writable_directories.add(path)
        return True

    def file_exists(self, path: str) -> bool:
        """Simulate file existence check.

        Args:
            path: File path to check

        Returns:
            True if file exists
        """
        return path in self.file_sizes

    def get_file_size(self, path: str) -> int:
        """Simulate getting file size.

        Args:
            path: File path

        Returns:
            File size in bytes
        """
        return self.file_sizes.get(path, 0)

    def list_files_in_directory(self, path: str, extension: str | None = None) -> list[str]:
        """Simulate listing files in directory.

        Args:
            path: Directory path
            extension: Optional file extension filter

        Returns:
            List of file paths
        """
        if path not in self.directory_files:
            return []

        files = self.directory_files[path]
        if extension:
            files = [f for f in files if f.lower().endswith(extension.lower())]
        return sorted(files)

    def set_cancel_dialog(self, should_cancel: bool = True) -> None:
        """Configure dialog cancellation behavior."""
        self.should_cancel_dialog = should_cancel

    def add_fake_file(self, path: str, size: int = 1000) -> None:
        """Add a fake file for testing."""
        self.file_sizes[path] = size

    def add_fake_directory_files(self, directory: str, files: list[str]) -> None:
        """Add fake files to a directory for testing."""
        self.directory_files[directory] = files

    def reset(self) -> None:
        """Reset stub state for new test."""
        self.should_cancel_dialog = False
        self.selected_directory = "/fake/download/path"
        self.file_sizes.clear()
        self.directory_files.clear()
        self.existing_directories = {"/fake/download/path", "/home/user"}
        self.writable_directories = {"/fake/download/path", "/home/user"}
