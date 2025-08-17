"""Enhanced tests for DownloadService with comprehensive yt-dlp mocking."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.download_service import DownloadService
from tests.stubs import (
    StubYoutubeDL, 
    EnhancedStubDownloadService,
    DownloadError,
    ExtractorError,
    UnsupportedError
)


class TestDownloadServiceErrorPaths:
    """Test download service error handling and edge cases."""

    def test_download_cloudcasts_no_directory_raises_value_error(self):
        """Test that empty directory raises ValueError."""
        service = DownloadService()
        
        with pytest.raises(ValueError, match="no download directory provided"):
            service.download_cloudcasts(["http://example.com"], "")
            
    def test_download_cloudcasts_no_directory_calls_error_callback(self):
        """Test that empty directory calls error callback before raising."""
        error_callback = MagicMock()
        service = DownloadService(error_callback=error_callback)
        
        with pytest.raises(ValueError):
            service.download_cloudcasts(["http://example.com"], "")
            
        error_callback.assert_called_once_with("no download directory provided")

    def test_download_single_cloudcast_delegates_to_download_cloudcasts(self):
        """Test that single download delegates to batch download."""
        service = EnhancedStubDownloadService()
        
        service.download_single_cloudcast("http://example.com", "/downloads")
        
        assert service.downloaded_urls == ["http://example.com"]

    def test_cancel_downloads_sets_cancelled_flag(self):
        """Test that cancel sets the cancelled flag."""
        service = DownloadService()
        
        service.cancel_downloads()
        
        assert service._is_cancelled is True

    def test_set_progress_callback(self):
        """Test setting progress callback."""
        callback = MagicMock()
        service = DownloadService()
        
        service.set_progress_callback(callback)
        
        assert service.progress_callback is callback

    def test_set_error_callback(self):
        """Test setting error callback."""  
        callback = MagicMock()
        service = DownloadService()
        
        service.set_error_callback(callback)
        
        assert service.error_callback is callback


class TestDownloadServiceWithYTDLPStub:
    """Test download service with comprehensive yt-dlp stubbing."""

    def test_successful_download_with_progress_tracking(self):
        """Test successful download with progress callbacks."""
        progress_callback = MagicMock()
        service = EnhancedStubDownloadService(progress_callback=progress_callback)
        
        urls = ["https://www.mixcloud.com/testuser/test-mix/"]
        service.download_cloudcasts(urls, "/downloads")
        
        # Verify download completed
        assert service.downloaded_urls == urls
        
        # Verify progress callbacks were called
        assert progress_callback.call_count > 0
        
        # Check that progress data looks realistic
        calls = progress_callback.call_args_list
        assert any("test mix" in call[0][0].lower() for call in calls)  # Filename
        assert any("%" in call[0][1] for call in calls)  # Progress info

    def test_yt_dlp_network_error_handling(self):
        """Test handling of yt-dlp network errors."""
        # Test with direct stub usage
        stub_yt_dlp = StubYoutubeDL({})
        stub_yt_dlp.set_error("network", "Connection timeout")
        
        with pytest.raises(DownloadError, match="Network error"):
            stub_yt_dlp.download(["http://example.com"])

    def test_yt_dlp_extraction_error_handling(self):
        """Test handling of yt-dlp extraction errors."""
        stub_yt_dlp = StubYoutubeDL({})
        stub_yt_dlp.set_error("extraction", "Failed to extract audio URL")
        
        with pytest.raises(ExtractorError, match="Extraction failed"):
            stub_yt_dlp.download(["http://example.com"])

    def test_yt_dlp_unsupported_url_error(self):
        """Test handling of unsupported URL errors."""
        stub_yt_dlp = StubYoutubeDL({})
        stub_yt_dlp.set_error("unsupported", "URL format not supported")
        
        with pytest.raises(UnsupportedError, match="Unsupported URL"):
            stub_yt_dlp.download(["http://example.com"])

    def test_yt_dlp_permission_error_handling(self):
        """Test handling of file system permission errors."""
        stub_yt_dlp = StubYoutubeDL({})
        stub_yt_dlp.set_error("permission", "Permission denied writing to directory")
        
        with pytest.raises(PermissionError, match="Permission denied"):
            stub_yt_dlp.download(["http://example.com"])

    def test_partial_download_failure(self):
        """Test scenario where some downloads fail but others succeed."""
        urls = [
            "https://www.mixcloud.com/user1/working-mix/",
            "https://www.mixcloud.com/user2/failing-mix/", 
            "https://www.mixcloud.com/user3/another-working-mix/"
        ]
        
        stub_yt_dlp = StubYoutubeDL({})
        stub_yt_dlp.enable_partial_failure([urls[1]])  # Only second URL fails
        stub_yt_dlp.set_error("network", "Connection lost")
        
        with pytest.raises(DownloadError):
            stub_yt_dlp.download(urls)
            
        # First URL should have been processed before failure
        assert urls[0] in stub_yt_dlp.downloaded_urls

    def test_cancel_during_download_stops_progress(self):
        """Test that cancellation stops progress updates."""
        progress_callback = MagicMock()
        service = DownloadService(progress_callback=progress_callback)
        
        # Set cancelled flag before calling _track_progress
        service._is_cancelled = True
        
        # Simulate progress callback during cancelled state
        progress_data = {
            "status": "downloading",
            "filename": "test.m4a",
            "downloaded_bytes": 1000,
            "total_bytes": 10000
        }
        
        service._track_progress(progress_data)
        
        # Progress callback should not be called when cancelled
        progress_callback.assert_not_called()

    def test_download_service_error_callback_integration(self):
        """Test that download service error handling integrates with stub."""
        error_callback = MagicMock()
        service = EnhancedStubDownloadService(error_callback=error_callback)
        
        # First do a successful download to create the stub
        service.download_cloudcasts(["http://example.com"], "/downloads")
        
        # Then configure error and test
        stub = service.get_stub_yt_dlp()
        stub.set_error("network", "Connection failed")
        
        with pytest.raises(DownloadError):
            service.download_cloudcasts(["http://example2.com"], "/downloads")
        
        # Error callback should be called with formatted message
        error_callback.assert_called_once()
        assert "Download failed" in error_callback.call_args[0][0]


class TestProgressTracking:
    """Test progress tracking functionality in detail."""

    def test_track_progress_with_valid_filename(self):
        """Test progress tracking with properly formatted filename."""
        progress_callback = MagicMock()
        service = DownloadService(progress_callback=progress_callback)
        
        progress_data = {
            "filename": "/downloads/testuser - Test Mix.m4a",
            "status": "downloading",
            "_percent_str": "50%",
            "_total_bytes_estimate_str": "10MB", 
            "_speed_str": "500KB/s"
        }
        
        service._track_progress(progress_data)
        
        progress_callback.assert_called_once()
        call_args = progress_callback.call_args[0]
        assert "testuser - Test Mix" in call_args[0]  # Cleaned filename
        assert "50%" in call_args[1]  # Should have progress info
        assert "unknown" not in call_args[1]  # Should not be unknown

    def test_track_progress_with_no_filename(self):
        """Test progress tracking when filename is missing."""
        progress_callback = MagicMock()
        service = DownloadService(progress_callback=progress_callback)
        
        progress_data = {"downloaded_bytes": 1000}  # No filename
        
        service._track_progress(progress_data)
        
        # Should not call callback without filename
        progress_callback.assert_not_called()

    def test_track_progress_without_callback(self):
        """Test progress tracking when no callback is set."""
        service = DownloadService()  # No progress callback
        
        progress_data = {
            "filename": "test.m4a",
            "downloaded_bytes": 1000,
            "total_bytes": 2000
        }
        
        # Should not raise exception
        service._track_progress(progress_data)

    def test_track_progress_cleans_filename_properly(self):
        """Test that filename cleaning works correctly."""
        progress_callback = MagicMock()
        service = DownloadService(progress_callback=progress_callback)
        
        progress_data = {
            "filename": "/downloads/Artist Name - Song Title.webm",
            "tmpfilename": "/downloads/Artist Name - Song Title.webm.part"
        }
        
        service._track_progress(progress_data)
        
        call_args = progress_callback.call_args[0]
        item_name = call_args[0]
        assert item_name == "Artist Name - Song Title"
        assert ".webm" not in item_name
        assert ".part" not in item_name

    def test_yt_dlp_options_configuration(self):
        """Test that yt-dlp options are configured correctly."""
        service = EnhancedStubDownloadService()
        
        service.download_cloudcasts(["http://example.com"], "/test/downloads")
        
        stub = service.get_stub_yt_dlp()
        assert stub is not None
        
        # Check output template includes directory and format
        outtmpl = stub.params["outtmpl"]
        assert "/test/downloads/" in outtmpl
        assert "%(uploader_id)s - %(title)s.%(ext)s" in outtmpl
        
        # Check progress hooks are registered
        assert len(stub.params["progress_hooks"]) == 1
        assert stub.params["verbose"] is False


class TestDownloadServiceConfiguration:
    """Test various configuration scenarios."""

    def test_initialization_with_callbacks(self):
        """Test initialization with both callbacks."""
        progress_cb = MagicMock()
        error_cb = MagicMock()
        
        service = DownloadService(progress_cb, error_cb)
        
        assert service.progress_callback is progress_cb
        assert service.error_callback is error_cb
        assert service._is_cancelled is False

    def test_initialization_without_callbacks(self):
        """Test initialization without callbacks."""
        service = DownloadService()
        
        assert service.progress_callback is None
        assert service.error_callback is None
        assert service._is_cancelled is False

    def test_enhanced_stub_reset_functionality(self):
        """Test that enhanced stub reset works properly."""
        service = EnhancedStubDownloadService()
        
        # Simulate some state
        service.downloaded_urls = ["http://example.com"]
        service._is_cancelled = True
        
        service.reset()
        
        assert service.downloaded_urls == []
        assert service._is_cancelled is False