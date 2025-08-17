"""Test stubs for dependency injection in tests."""

from typing import Any, Callable
import httpx
import time
from unittest.mock import MagicMock

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


# yt-dlp Exception Classes (mimicking real yt-dlp exceptions)
class YTDLError(Exception):
    """Base exception for yt-dlp errors."""
    pass


class DownloadError(YTDLError):
    """Exception for download failures."""
    pass


class ExtractorError(YTDLError):
    """Exception for extraction failures."""
    pass


class UnsupportedError(YTDLError):
    """Exception for unsupported URLs or features."""
    pass


class StubYoutubeDL:
    """Comprehensive stub for yt_dlp.YoutubeDL that simulates real download behavior."""
    
    def __init__(self, params: dict[str, Any]) -> None:
        """Initialize stub YoutubeDL with parameters.
        
        Args:
            params: yt-dlp configuration parameters
        """
        self.params = params
        self.downloaded_urls: list[str] = []
        self.should_raise_error = False
        self.error_type = "network"  # network, format, permission, extraction, unsupported
        self.error_message = "Simulated download error"
        self.progress_hooks: list[Callable] = params.get("progress_hooks", [])
        self.simulate_slow_download = False
        self.download_delay = 0.0  # Seconds to delay between progress updates
        self.simulate_partial_failure = False  # Fail on some URLs but not others
        self.failed_urls: list[str] = []  # URLs that should fail when partial failure is enabled
        
        # Progress simulation settings
        self.file_sizes = {"default": 10_000_000}  # 10MB default
        self.download_speeds = {"default": 500_000}  # 500KB/s default
        
    def download(self, urls: list[str]) -> None:
        """Simulate downloading URLs with realistic progress and error scenarios.
        
        Args:
            urls: List of URLs to download
            
        Raises:
            DownloadError: For general download failures
            ExtractorError: For extraction/parsing failures  
            UnsupportedError: For unsupported URLs
            PermissionError: For file system permission issues
        """
        if self.should_raise_error and self.error_type == "permission":
            raise PermissionError(f"Permission denied: {self.error_message}")
            
        for i, url in enumerate(urls):
            # Check if this specific URL should fail (for partial failure testing)
            if self.simulate_partial_failure and url in self.failed_urls:
                self._raise_configured_error()
                
            # Check for global error - immediate failure unless partial failure mode
            if self.should_raise_error and not self.simulate_partial_failure:
                self._raise_configured_error()
                
            # For partial failure mode, allow first URL to succeed then fail
            if self.should_raise_error and self.simulate_partial_failure and i > 0:
                self._raise_configured_error()
                
            self._simulate_single_download(url)
            self.downloaded_urls.append(url)
            
    def _raise_configured_error(self) -> None:
        """Raise the appropriate error type based on configuration."""
        if self.error_type == "network":
            raise DownloadError(f"Network error: {self.error_message}")
        elif self.error_type == "extraction":
            raise ExtractorError(f"Extraction failed: {self.error_message}")
        elif self.error_type == "unsupported":
            raise UnsupportedError(f"Unsupported URL: {self.error_message}")
        elif self.error_type == "format":
            raise DownloadError(f"Format not available: {self.error_message}")
        else:
            raise DownloadError(self.error_message)
            
    def _simulate_single_download(self, url: str) -> None:
        """Simulate downloading a single URL with progress callbacks.
        
        Args:
            url: URL being downloaded
        """
        if not self.progress_hooks:
            return
            
        # Extract filename from URL for realistic simulation
        # URL format: https://www.mixcloud.com/username/track-name/
        parts = url.rstrip("/").split("/")
        if len(parts) >= 2:
            username = parts[-2] 
            track_name = parts[-1].replace("-", " ").title()
            filename = f"{username} - {track_name}.webm"
        else:
            filename = "unknown_track.webm"
            
        # Get configured file size and speed for this URL
        file_size = self.file_sizes.get(url, self.file_sizes["default"])
        speed = self.download_speeds.get(url, self.download_speeds["default"])
        
        # Simulate output template processing
        outtmpl = self.params.get("outtmpl", "%(title)s.%(ext)s")
        if "%(uploader_id)s" in outtmpl and "%(title)s" in outtmpl:
            final_filename = outtmpl.replace("%(uploader_id)s", parts[-2] if len(parts) >= 2 else "unknown")
            final_filename = final_filename.replace("%(title)s", track_name if len(parts) >= 2 else "unknown")
            final_filename = final_filename.replace("%(ext)s", "m4a")
        else:
            final_filename = filename
            
        # Simulate download progress stages
        chunk_size = file_size // 4  # Download in 4 chunks
        downloaded = 0
        
        for chunk in range(4):
            downloaded += chunk_size
            if downloaded > file_size:
                downloaded = file_size
                
            progress_data = {
                "status": "downloading",
                "filename": final_filename,
                "tmpfilename": f"{final_filename}.part",
                "downloaded_bytes": downloaded,
                "total_bytes": file_size,
                "speed": speed,
                "eta": (file_size - downloaded) / speed if speed > 0 else None,
                "_percent_str": f"{(downloaded/file_size)*100:.1f}%",
                "_speed_str": f"{speed//1000}KB/s" if speed < 1_000_000 else f"{speed//1_000_000:.1f}MB/s"
            }
            
            for hook in self.progress_hooks:
                hook(progress_data)
                
            if self.download_delay > 0:
                time.sleep(self.download_delay)
                
        # Final completion status
        final_progress = {
            "status": "finished",
            "filename": final_filename,
            "downloaded_bytes": file_size,
            "total_bytes": file_size,
            "_percent_str": "100%"
        }
        
        for hook in self.progress_hooks:
            hook(final_progress)
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
        
    # Test configuration methods
    def set_error(self, error_type: str = "network", message: str = "Simulated error") -> None:
        """Configure the stub to raise errors.
        
        Args:
            error_type: Type of error - network, extraction, unsupported, format, permission
            message: Error message to use
        """
        self.should_raise_error = True
        self.error_type = error_type
        self.error_message = message
        
    def set_file_size(self, url_or_default: str, size: int) -> None:
        """Set simulated file size for a URL or default.
        
        Args:
            url_or_default: Specific URL or "default" for default size
            size: File size in bytes
        """
        self.file_sizes[url_or_default] = size
        
    def set_download_speed(self, url_or_default: str, speed: int) -> None:
        """Set simulated download speed for a URL or default.
        
        Args:
            url_or_default: Specific URL or "default" for default speed  
            speed: Download speed in bytes per second
        """
        self.download_speeds[url_or_default] = speed
        
    def enable_partial_failure(self, failed_urls: list[str]) -> None:
        """Enable partial failure mode where only specific URLs fail.
        
        Args:
            failed_urls: List of URLs that should fail during download
        """
        self.simulate_partial_failure = True
        self.failed_urls = failed_urls
        
    def reset(self) -> None:
        """Reset stub state for new test."""
        self.downloaded_urls.clear()
        self.should_raise_error = False
        self.simulate_partial_failure = False
        self.failed_urls.clear()
        self.file_sizes = {"default": 10_000_000}
        self.download_speeds = {"default": 500_000}


class EnhancedStubDownloadService(DownloadService):
    """Enhanced stub download service that uses real DownloadService with mocked yt-dlp.
    
    This allows testing the actual DownloadService logic while controlling yt-dlp behavior.
    """
    
    def __init__(
        self, 
        progress_callback: Callable[[str, str], None] | None = None,
        error_callback: Callable[[str], None] | None = None
    ) -> None:
        """Initialize enhanced stub with real service logic.
        
        Args:
            progress_callback: Progress callback function
            error_callback: Error callback function
        """
        super().__init__(progress_callback, error_callback)
        self.stub_yt_dlp: StubYoutubeDL | None = None
        self.downloaded_urls: list[str] = []
        
    def _create_stub_yt_dlp(self, ydl_opts: dict[str, Any]) -> StubYoutubeDL:
        """Create and configure stub yt-dlp instance.
        
        Args:
            ydl_opts: yt-dlp options from real service
            
        Returns:
            Configured StubYoutubeDL instance
        """
        if self.stub_yt_dlp is None:
            stub = StubYoutubeDL(ydl_opts)
            self.stub_yt_dlp = stub
        else:
            # Reuse existing stub but update options
            self.stub_yt_dlp.params = ydl_opts
        
        return self.stub_yt_dlp
        
    def download_cloudcasts(self, urls: list[str], directory: str) -> None:
        """Override to use stub yt-dlp while keeping real service logic.
        
        Args:
            urls: List of cloudcast URLs to download
            directory: Target directory for downloads
            
        Raises:
            ValueError: If directory is not provided
        """
        if not directory:
            error_msg = "no download directory provided"
            if self.error_callback:
                self.error_callback(error_msg)
            raise ValueError(error_msg)

        self._is_cancelled = False

        ydl_opts = {
            "outtmpl": f"{directory}/%(uploader_id)s - %(title)s.%(ext)s",
            "progress_hooks": [self._track_progress],
            "verbose": False,
        }

        # Use stub instead of real yt-dlp
        try:
            with self._create_stub_yt_dlp(ydl_opts) as ydl:
                ydl.download(urls)
                self.downloaded_urls.extend(ydl.downloaded_urls)
        except Exception as e:
            if self.error_callback and not self._is_cancelled:
                self.error_callback(f"Download failed: {str(e)}")
            raise
            
    # Test configuration methods
    def set_yt_dlp_error(self, error_type: str = "network", message: str = "Download failed") -> None:
        """Configure yt-dlp stub to raise errors.
        
        Args:
            error_type: Type of error to simulate
            message: Error message
        """
        if self.stub_yt_dlp:
            self.stub_yt_dlp.set_error(error_type, message)
            
    def set_file_size(self, url_or_default: str, size: int) -> None:
        """Set simulated file size for downloads.
        
        Args:
            url_or_default: URL or "default" for default size
            size: File size in bytes
        """
        if self.stub_yt_dlp:
            self.stub_yt_dlp.set_file_size(url_or_default, size)
            
    def enable_partial_failure(self, failed_urls: list[str]) -> None:
        """Enable partial failure mode.
        
        Args:
            failed_urls: URLs that should fail
        """
        if self.stub_yt_dlp:
            self.stub_yt_dlp.enable_partial_failure(failed_urls)
            
    def get_stub_yt_dlp(self) -> StubYoutubeDL | None:
        """Get the stub yt-dlp instance for advanced configuration.
        
        Returns:
            StubYoutubeDL instance or None if not created yet
        """
        return self.stub_yt_dlp
        
    def reset(self) -> None:
        """Reset stub state for new test."""
        self.downloaded_urls.clear()
        self._is_cancelled = False
        if self.stub_yt_dlp:
            self.stub_yt_dlp.reset()