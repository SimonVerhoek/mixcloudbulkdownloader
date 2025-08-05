"""Test stubs for dependency injection in tests."""

from typing import Any
import httpx

from app.services.api_service import MixcloudAPIService
from app.services.download_service import DownloadService
from app.services.file_service import FileService


class FakeHTTPClient:
    """Fake HTTP client that returns predefined responses."""
    
    def __init__(self) -> None:
        """Initialize fake client with response mapping."""
        self.responses: dict[str, dict[str, Any]] = {
            # User search responses
            "search_user_success": {
                "data": [
                    {
                        "key": "/testuser/",
                        "name": "Test User",
                        "pictures": {"large": "https://example.com/large.jpg"},
                        "url": "https://www.mixcloud.com/testuser/",
                        "username": "testuser"
                    },
                    {
                        "key": "/anotheruser/",
                        "name": "Another User",
                        "pictures": {},
                        "url": "https://www.mixcloud.com/anotheruser/",
                        "username": "anotheruser"
                    }
                ]
            },
            
            # Cloudcast responses
            "cloudcasts_page1": {
                "data": [
                    {
                        "name": "Test Mix 1",
                        "url": "https://www.mixcloud.com/testuser/test-mix-1/"
                    },
                    {
                        "name": "Test Mix 2", 
                        "url": "https://www.mixcloud.com/testuser/test-mix-2/"
                    }
                ],
                "paging": {
                    "next": "https://api.mixcloud.com/testuser/cloudcasts/?offset=20"
                }
            },
            
            "cloudcasts_page2": {
                "data": [
                    {
                        "name": "Test Mix 3",
                        "url": "https://www.mixcloud.com/testuser/test-mix-3/"
                    }
                ]
            },
            
            # Error responses
            "user_not_found": {
                "error": {
                    "type": "NotFound",
                    "message": "User not found"
                }
            },
            
            "api_error": {
                "error": {
                    "type": "InvalidRequest",
                    "message": "Invalid search query"
                }
            }
        }
        
        self.request_count = 0
        self.last_url = ""
        self.should_raise_network_error = False
        self.should_raise_http_error = False
        self.http_status_code = 404
        
    def get(self, url: str) -> 'FakeHTTPResponse':
        """Simulate HTTP GET request.
        
        Args:
            url: Request URL
            
        Returns:
            Fake HTTP response
            
        Raises:
            httpx.RequestError: When should_raise_network_error is True
            httpx.HTTPStatusError: When should_raise_http_error is True
        """
        self.request_count += 1
        self.last_url = url
        
        if self.should_raise_network_error:
            raise httpx.RequestError("Simulated network error")
            
        if self.should_raise_http_error:
            response = FakeHTTPResponse({}, status_code=self.http_status_code)
            raise httpx.HTTPStatusError(
                "HTTP Error", 
                request=None, 
                response=response
            )
        
        # Determine response based on URL patterns
        if "search" in url and "type=user" in url:
            if "q=" in url and "q=&" in url:  # Empty search phrase
                return FakeHTTPResponse({"data": []})
            elif "nonexistent" in url:
                return FakeHTTPResponse(self.responses["user_not_found"])
            elif "error" in url:
                return FakeHTTPResponse(self.responses["user_not_found"])
            else:
                return FakeHTTPResponse(self.responses["search_user_success"])
                
        elif "cloudcasts" in url:
            if "offset=20" in url:
                return FakeHTTPResponse(self.responses["cloudcasts_page2"])
            else:
                return FakeHTTPResponse(self.responses["cloudcasts_page1"])
                
        # Default empty response
        return FakeHTTPResponse({"data": []})
        
    def close(self) -> None:
        """Simulate client closure."""
        pass


class FakeHTTPResponse:
    """Fake HTTP response object."""
    
    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        """Initialize fake response.
        
        Args:
            json_data: JSON data to return
            status_code: HTTP status code
        """
        self._json_data = json_data
        self.status_code = status_code
        
    def json(self) -> dict[str, Any]:
        """Return JSON data."""
        return self._json_data
        
    def raise_for_status(self) -> None:
        """Raise exception for HTTP errors."""
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=None,
                response=self
            )


class StubMixcloudAPIService(MixcloudAPIService):
    """Stub API service for testing."""
    
    def __init__(self) -> None:
        """Initialize stub with fake HTTP client."""
        fake_client = FakeHTTPClient()
        super().__init__(http_client=fake_client)
        self.fake_client = fake_client
        
    def set_network_error(self, should_error: bool = True) -> None:
        """Configure stub to simulate network errors."""
        self.fake_client.should_raise_network_error = should_error
        
    def set_http_error(self, should_error: bool = True, status_code: int = 404) -> None:
        """Configure stub to simulate HTTP errors."""
        self.fake_client.should_raise_http_error = should_error
        self.fake_client.http_status_code = status_code
        
    @property 
    def request_count(self) -> int:
        """Get number of requests made."""
        return self.fake_client.request_count
        
    @property
    def last_url(self) -> str:
        """Get last requested URL."""
        return self.fake_client.last_url


class StubDownloadService(DownloadService):
    """Stub download service for testing."""
    
    def __init__(self) -> None:
        """Initialize stub download service."""
        super().__init__()
        self.downloaded_urls: list[str] = []
        self.download_directory = ""
        self.should_raise_error = False
        self.error_message = "Simulated download error"
        self.simulate_progress = True
        
    def download_cloudcasts(self, urls: list[str], directory: str) -> None:
        """Simulate cloudcast downloads.
        
        Args:
            urls: List of URLs to download
            directory: Target directory
            
        Raises:
            ValueError: If directory not provided
            Exception: If should_raise_error is True
        """
        if not directory:
            error_msg = "No download directory provided"
            if self.error_callback:
                self.error_callback(error_msg)
            raise ValueError(error_msg)
            
        if self.should_raise_error:
            if self.error_callback:
                self.error_callback(self.error_message)
            raise Exception(self.error_message)
        
        self.downloaded_urls.extend(urls)
        self.download_directory = directory
        
        # Simulate progress updates
        if self.simulate_progress and self.progress_callback:
            for i, url in enumerate(urls):
                if self._is_cancelled:
                    break
                    
                # Extract filename from URL and make it more realistic
                # URL format: https://www.mixcloud.com/username/track-name/
                parts = url.rstrip("/").split("/")
                if len(parts) >= 2:
                    username = parts[-2]
                    track_name = parts[-1].replace("-", " ")
                    # Simulate yt-dlp filename format: "username - track name"
                    filename = f"{username.lower()} - {track_name}"
                else:
                    filename = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
                
                # Simulate download progress
                self.progress_callback(filename, "25% of 10MB at 500KB/s")
                self.progress_callback(filename, "50% of 10MB at 500KB/s") 
                self.progress_callback(filename, "100% of 10MB at 500KB/s")
                self.progress_callback(filename, "Done")
                
    def set_download_error(self, should_error: bool = True, message: str = "Download failed") -> None:
        """Configure stub to simulate download errors."""
        self.should_raise_error = should_error
        self.error_message = message
        
    def reset(self) -> None:
        """Reset stub state for new test."""
        self.downloaded_urls.clear()
        self.download_directory = ""
        self.should_raise_error = False
        self._is_cancelled = False


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