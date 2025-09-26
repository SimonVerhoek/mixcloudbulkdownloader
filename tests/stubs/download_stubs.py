"""Download service test stubs."""

from pathlib import Path
from typing import Any, Callable
from unittest.mock import Mock

from app.services.download_service import DownloadService
from .ytdlp_stubs import StubYoutubeDL
from .ffmpeg_stubs import StubFFmpegService


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
        
    def download_cloudcasts(self, urls: list[str], directory: str | None = None, parent_widget=None) -> None:
        """Simulate cloudcast downloads.
        
        Args:
            urls: List of URLs to download
            directory: Target directory for downloads. If None, uses Pro default or shows picker.
            parent_widget: Parent widget for dialogs (unused in stub)
            
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
        
    def download_cloudcasts(self, urls: list[str], directory: str | None = None, parent_widget=None) -> None:
        """Override to use stub yt-dlp while keeping real service logic.
        
        Args:
            urls: List of cloudcast URLs to download
            directory: Target directory for downloads. If None, uses Pro default or shows picker.
            parent_widget: Parent widget for dialogs (unused in stub)
            
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


class FFmpegAwareDownloadService(DownloadService):
    """Download service stub with FFmpeg integration testing capabilities.
    
    This stub allows comprehensive testing of audio conversion functionality
    including FFmpeg path detection, availability checking, and conversion.
    """
    
    def __init__(
        self,
        progress_callback: Callable[[str, str], None] = None,
        error_callback: Callable[[str], None] = None
    ) -> None:
        """Initialize FFmpeg-aware download service stub.
        
        Args:
            progress_callback: Progress update callback
            error_callback: Error reporting callback
        """
        super().__init__(progress_callback, error_callback)
        
        # FFmpeg stub for testing
        self.ffmpeg_stub = StubFFmpegService()
        
        # Track method calls for verification
        self.ffmpeg_path_calls: list[str] = []
        self.availability_checks: list[dict[str, Any]] = []
        self.conversions: list[dict[str, Any]] = []
        
        # Configuration for testing scenarios
        self.mock_platform = None  # Override platform detection
        
    def _get_ffmpeg_path(self) -> Path:
        """Get FFmpeg path using stub for testing.
        
        Returns:
            Path to FFmpeg executable
            
        Raises:
            RuntimeError: If platform is unsupported
        """
        platform = self.mock_platform or None
        self.ffmpeg_path_calls.append(platform or "default")
        return self.ffmpeg_stub.get_ffmpeg_path(platform)
        
    def verify_ffmpeg_availability(self) -> bool:
        """Verify FFmpeg availability using stub.
        
        Returns:
            True if FFmpeg is available
        """
        platform = self.mock_platform or None
        result = self.ffmpeg_stub.verify_ffmpeg_availability(platform)
        
        self.availability_checks.append({
            "platform": platform or "default",
            "available": result
        })
        
        return result
        
    def convert_audio(
        self,
        input_path: str,
        output_path: str,
        target_format: str,
        bitrate_k: int = 192
    ) -> None:
        """Convert audio using FFmpeg stub.
        
        Args:
            input_path: Source file path
            output_path: Target file path
            target_format: Target audio format
            bitrate_k: Bitrate in kbps for lossy formats
            
        Raises:
            RuntimeError: If conversion fails
        """
        conversion_info = {
            "input_path": input_path,
            "output_path": output_path,
            "target_format": target_format,
            "bitrate_k": bitrate_k
        }
        self.conversions.append(conversion_info)
        
        # Use FFmpeg stub for conversion
        self.ffmpeg_stub.convert_audio(
            input_path,
            output_path,
            target_format,
            bitrate_k,
            self.progress_callback
        )
        
    # Test configuration methods
        
    def set_platform(self, platform: str) -> None:
        """Set platform for testing platform-specific behavior.
        
        Args:
            platform: Platform name (windows, darwin, linux)
        """
        self.mock_platform = platform
        
    def set_ffmpeg_availability(self, available: bool) -> None:
        """Configure FFmpeg availability for testing.
        
        Args:
            available: Whether FFmpeg should be available
        """
        self.ffmpeg_stub.set_availability(available)
        
    def set_ffmpeg_path_exists(self, exists: bool) -> None:
        """Configure whether FFmpeg executable exists.
        
        Args:
            exists: Whether FFmpeg executable should exist
        """
        self.ffmpeg_stub.set_path_exists(exists)
        
    def set_conversion_failure(self, should_fail: bool, error_message: str = None) -> None:
        """Configure audio conversion to fail for testing.
        
        Args:
            should_fail: Whether conversion should fail
            error_message: Custom error message
        """
        self.ffmpeg_stub.set_conversion_failure(should_fail, error_message)
        
    def get_ffmpeg_stub(self) -> StubFFmpegService:
        """Get the FFmpeg stub for advanced configuration.
        
        Returns:
            FFmpeg service stub instance
        """
        return self.ffmpeg_stub
        
    # Verification methods for tests
        
    def get_ffmpeg_path_calls(self) -> list[str]:
        """Get list of platforms used in FFmpeg path calls.
        
        Returns:
            List of platform names used in path resolution
        """
        return self.ffmpeg_path_calls.copy()
        
    def get_availability_checks(self) -> list[dict[str, Any]]:
        """Get history of FFmpeg availability checks.
        
        Returns:
            List of availability check records
        """
        return self.availability_checks.copy()
        
    def get_conversions(self) -> list[dict[str, Any]]:
        """Get history of audio conversions.
        
        Returns:
            List of conversion records
        """
        return self.conversions.copy()
        
    def get_conversion_progress_calls(self) -> list[tuple[str, str]]:
        """Get progress callbacks made during conversions.
        
        Returns:
            List of (item_name, progress_message) tuples
        """
        return self.ffmpeg_stub.progress_calls.copy()
        
    def reset(self) -> None:
        """Reset stub state for new test."""
        self.ffmpeg_path_calls.clear()
        self.availability_checks.clear()
        self.conversions.clear()
        self.mock_platform = None
        self.ffmpeg_stub.reset()
        self._is_cancelled = False