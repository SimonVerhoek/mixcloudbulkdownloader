"""yt-dlp test stubs and mock exceptions."""

from typing import Any, Callable
import time


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