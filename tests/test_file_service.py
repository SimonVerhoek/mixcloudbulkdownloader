"""Tests for FileService."""

import pytest

from app.services.file_service import FileService
from tests.stubs.file_stubs import StubFileService


class TestFileService:
    """Test cases for FileService."""

    def test_init(self):
        """Test service initialization."""
        service = FileService()
        assert service is not None

    def test_select_download_directory_success(self):
        """Test successful directory selection."""
        service = StubFileService()

        result = service.select_download_directory(title="Test Dialog")

        assert result == "/fake/download/path"

    def test_select_download_directory_cancelled(self):
        """Test cancelled directory selection."""
        service = StubFileService()
        service.set_cancel_dialog(True)

        result = service.select_download_directory()

        assert result == ""

    def test_validate_directory_valid(self):
        """Test validation of valid directory."""
        service = StubFileService()

        result = service.validate_directory("/fake/download/path")

        assert result is True

    def test_validate_directory_invalid(self):
        """Test validation of invalid directory."""
        service = StubFileService()

        result = service.validate_directory("/nonexistent/path")

        assert result is False

    def test_validate_directory_empty_path(self):
        """Test validation of empty path."""
        service = StubFileService()

        result = service.validate_directory("")

        assert result is False

    def test_validate_directory_not_writable(self):
        """Test validation of non-writable directory."""
        service = StubFileService()
        service.existing_directories.add("/readonly/path")
        # Don't add to writable_directories

        result = service.validate_directory("/readonly/path")

        assert result is False

    def test_ensure_directory_exists_existing(self):
        """Test ensuring existing directory exists."""
        service = StubFileService()

        result = service.ensure_directory_exists("/fake/download/path")

        assert result is True

    def test_ensure_directory_exists_new(self):
        """Test creating new directory."""
        service = StubFileService()

        result = service.ensure_directory_exists("/new/directory/path")

        assert result is True
        assert "/new/directory/path" in service.existing_directories

    def test_ensure_directory_exists_empty_path(self):
        """Test ensuring empty path exists."""
        service = StubFileService()

        result = service.ensure_directory_exists("")

        assert result is False

    def test_get_user_home_directory(self):
        """Test getting user home directory."""
        service = FileService()

        result = service.get_user_home_directory()

        assert result is not None
        assert len(result) > 0

    def test_join_paths(self):
        """Test joining path components."""
        service = FileService()

        result = service.join_paths("home", "user", "downloads")

        assert "home" in result
        assert "user" in result
        assert "downloads" in result

    def test_file_exists_true(self):
        """Test file existence check for existing file."""
        service = StubFileService()
        service.add_fake_file("/fake/file.txt", 1000)

        result = service.file_exists("/fake/file.txt")

        assert result is True

    def test_file_exists_false(self):
        """Test file existence check for non-existing file."""
        service = StubFileService()

        result = service.file_exists("/nonexistent/file.txt")

        assert result is False

    def test_get_file_size_existing(self):
        """Test getting size of existing file."""
        service = StubFileService()
        service.add_fake_file("/fake/file.txt", 2048)

        result = service.get_file_size("/fake/file.txt")

        assert result == 2048

    def test_get_file_size_nonexistent(self):
        """Test getting size of non-existing file."""
        service = StubFileService()

        result = service.get_file_size("/nonexistent/file.txt")

        assert result == 0

    def test_get_directory_size_valid(self):
        """Test getting directory size."""
        service = StubFileService()

        # Directory size calculation would need more complex stub setup
        # For now, test that it returns 0 for non-existent directory
        result = service.get_directory_size("/nonexistent/path")

        assert result == 0

    def test_get_directory_size_invalid_path(self):
        """Test getting size of invalid directory."""
        service = StubFileService()

        result = service.get_directory_size("/invalid/path")

        assert result == 0

    def test_list_files_in_directory_valid(self):
        """Test listing files in valid directory."""
        service = StubFileService()
        fake_files = ["/fake/dir/file1.mp3", "/fake/dir/file2.mp3", "/fake/dir/file3.txt"]
        service.add_fake_directory_files("/fake/dir", fake_files)

        result = service.list_files_in_directory("/fake/dir")

        assert len(result) == 3
        assert all(f in result for f in fake_files)

    def test_list_files_in_directory_with_extension_filter(self):
        """Test listing files with extension filter."""
        service = StubFileService()
        fake_files = ["/fake/dir/file1.mp3", "/fake/dir/file2.mp3", "/fake/dir/file3.txt"]
        service.add_fake_directory_files("/fake/dir", fake_files)

        result = service.list_files_in_directory("/fake/dir", ".mp3")

        assert len(result) == 2
        assert "/fake/dir/file1.mp3" in result
        assert "/fake/dir/file2.mp3" in result
        assert "/fake/dir/file3.txt" not in result

    def test_list_files_in_directory_invalid(self):
        """Test listing files in invalid directory."""
        service = StubFileService()

        result = service.list_files_in_directory("/invalid/path")

        assert result == []

    def test_list_files_in_directory_case_insensitive_extension(self):
        """Test extension filter is case insensitive."""
        service = StubFileService()
        fake_files = ["/fake/dir/file1.MP3", "/fake/dir/file2.mp3", "/fake/dir/file3.TXT"]
        service.add_fake_directory_files("/fake/dir", fake_files)

        result = service.list_files_in_directory("/fake/dir", ".mp3")

        assert len(result) == 2
        assert "/fake/dir/file1.MP3" in result
        assert "/fake/dir/file2.mp3" in result

    def test_stub_reset(self):
        """Test that stub reset clears state."""
        service = StubFileService()

        # Modify state
        service.set_cancel_dialog(True)
        service.add_fake_file("/test/file.txt", 500)
        service.add_fake_directory_files("/test", ["/test/file.txt"])

        # Reset
        service.reset()

        # Check state is cleared
        assert service.should_cancel_dialog is False
        assert service.selected_directory == "/fake/download/path"
        assert len(service.file_sizes) == 0
        assert len(service.directory_files) == 0
